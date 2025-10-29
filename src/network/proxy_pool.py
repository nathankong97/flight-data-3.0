"""HTTP proxy utilities: fetching, validation, and request-time rotation.

This module supports an optional proxy workflow:

1) Fetch a public list of HTTP proxies (``ip:port`` per line).
2) Stage 1 validation against a generic HTTPS endpoint (reachability + latency).
3) Stage 2 validation using a caller-provided probe (e.g., FlightRadar24 test call).
4) Build a ``ProxyPool`` for round-robin/randomized rotation during the job.

Notes:
- Only use proxies for public, non-sensitive outbound requests. Never proxy secrets.
- Public proxies are volatile; always keep a direct-IP fallback path in callers.
"""

import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProxyEndpoint:
    """Represents an HTTP proxy endpoint.

    Args:
        host: Proxy host or IP.
        port: Proxy TCP port.
    """

    host: str
    port: int

    def as_url(self) -> str:
        """Return a URL form suitable for Requests ``proxies`` mapping."""
        return f"http://{self.host}:{self.port}"


@dataclass
class ProxyProbe:
    """Result of validating a proxy against a target.

    Attributes:
        proxy: The proxy endpoint.
        ok: Whether the probe succeeded with acceptable status/latency.
        status_code: Optional HTTP status observed.
        latency_ms: Observed latency in milliseconds (float("inf") when failed).
        error: Optional error string if failed.
        stage: Label for the probe stage (e.g., "generic" or "custom").
    """

    proxy: ProxyEndpoint
    ok: bool
    status_code: Optional[int]
    latency_ms: float
    error: Optional[str]
    stage: str


def _parse_proxy_line(line: str) -> Optional[ProxyEndpoint]:
    """Parse a single ``ip:port`` line into a ``ProxyEndpoint``.

    Returns None for invalid lines.
    """
    raw_line = (line or "").strip()
    if not raw_line or ":" not in raw_line:
        return None
    host, port_text = raw_line.split(":", 1)
    host = host.strip()
    try:
        port = int(port_text.strip())
    except ValueError:
        return None
    if not host or port <= 0:
        return None
    return ProxyEndpoint(host=host, port=port)


def fetch_proxy_list(
    source_url: str,
    *,
    timeout_seconds: float = 8.0,
    limit: Optional[int] = 300,
) -> List[ProxyEndpoint]:
    """Fetch and parse a public proxy list.

    Args:
        source_url: URL returning a text list of ``ip:port`` per line.
        timeout_seconds: Request timeout in seconds.
        limit: Optional cap on number of proxies to keep (after shuffle/dedupe).

    Returns:
        A deduplicated list of ``ProxyEndpoint`` values.
    """
    resp = requests.get(source_url, timeout=timeout_seconds)
    resp.raise_for_status()
    lines = resp.text.splitlines()

    proxies: List[ProxyEndpoint] = []
    seen: set[Tuple[str, int]] = set()
    for text_line in lines:
        endpoint = _parse_proxy_line(text_line)
        if not endpoint:
            continue
        key = (endpoint.host, endpoint.port)
        if key in seen:
            continue
        seen.add(key)
        proxies.append(endpoint)

    random.shuffle(proxies)
    if limit and limit > 0:
        proxies = proxies[:limit]

    LOGGER.info(
        "Fetched %d proxies from %s (limit=%s)",
        len(proxies),
        source_url,
        str(limit),
    )
    return proxies


def _proxies_mapping(proxy: ProxyEndpoint) -> Dict[str, str]:
    url = proxy.as_url()
    return {"http": url, "https": url}


def validate_proxy_generic(
    proxy: ProxyEndpoint,
    *,
    url: str,
    connect_timeout: float = 2.0,
    read_timeout: float = 4.0,
    accept_status: Sequence[int] = (200,),
) -> ProxyProbe:
    """Validate a proxy by issuing a small HTTPS GET to a generic endpoint.

    Args:
        proxy: Proxy endpoint to test.
        url: Target URL (e.g., https://httpbin.org/ip).
        connect_timeout: Socket connect timeout in seconds.
        read_timeout: Read timeout in seconds.
        accept_status: Acceptable HTTP status codes.

    Returns:
        A ``ProxyProbe`` with success flag and timing.
    """
    start_ns = time.perf_counter_ns()
    try:
        resp = requests.get(
            url,
            timeout=(connect_timeout, read_timeout),
            proxies=_proxies_mapping(proxy),
            headers={"User-Agent": "flight-data/1.0"},
        )
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        ok = resp.status_code in accept_status
        return ProxyProbe(
            proxy=proxy,
            ok=ok,
            status_code=resp.status_code,
            latency_ms=elapsed_ms,
            error=None,
            stage="generic",
        )
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        return ProxyProbe(
            proxy=proxy,
            ok=False,
            status_code=None,
            latency_ms=elapsed_ms,
            error=str(exc),
            stage="generic",
        )


def validate_proxy_custom(
    proxy: ProxyEndpoint,
    *,
    probe: Callable[[Dict[str, str]], Tuple[bool, Optional[int], Optional[str]]],
) -> ProxyProbe:
    """Validate a proxy via a caller-provided probe function.

    The probe receives a ``requests``-style ``proxies`` mapping (http/https) and must
    return a tuple: ``(ok, status_code, error)``.
    """
    start_ns = time.perf_counter_ns()
    try:
        ok, status_code, error_text = probe(_proxies_mapping(proxy))
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        return ProxyProbe(
            proxy=proxy,
            ok=ok,
            status_code=status_code,
            latency_ms=elapsed_ms,
            error=error_text,
            stage="custom",
        )
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        return ProxyProbe(
            proxy=proxy,
            ok=False,
            status_code=None,
            latency_ms=elapsed_ms,
            error=str(exc),
            stage="custom",
        )


class ProxyPool:
    """A simple rotating pool of validated proxies with failure eviction.

    Use ``get_proxies_for_request`` to obtain a mapping suitable for ``requests``.
    Call ``report_failure`` when a proxy fails; it will be evicted after the
    configured number of failures.
    """

    def __init__(
        self,
        proxies: Iterable[ProxyEndpoint],
        *,
        max_failures: int = 2,
        strategy: str = "round_robin",
    ) -> None:
        self._proxies: List[ProxyEndpoint] = list(proxies)
        self._failures: Dict[Tuple[str, int], int] = {}
        self._idx: int = 0
        self._max_failures = max(1, int(max_failures))
        self._strategy = strategy

    def is_empty(self) -> bool:
        """Return True if the pool has no proxies left."""
        return not self._proxies

    def get_proxies_for_request(self) -> Optional[Dict[str, str]]:
        """Return a proxies mapping for the next request, or None if empty."""
        if not self._proxies:
            return None
        if self._strategy == "random":
            proxy = random.choice(self._proxies)
        else:
            proxy = self._proxies[self._idx % len(self._proxies)]
            self._idx += 1
        return _proxies_mapping(proxy)

    def report_failure(self, proxies_mapping: Dict[str, str]) -> None:
        """Record a failure for the given mapping and evict if threshold reached.

        Args:
            proxies_mapping: The mapping previously returned by ``get_proxies_for_request``.
        """
        url = proxies_mapping.get("http") or proxies_mapping.get("https")
        if not url or not url.startswith("http://"):
            return
        host_port = url[len("http://") :]
        if ":" not in host_port:
            return
        host, port_s = host_port.split(":", 1)
        try:
            port = int(port_s)
        except ValueError:
            return
        key = (host, port)
        count = self._failures.get(key, 0) + 1
        self._failures[key] = count
        if count >= self._max_failures:
            # Evict from pool
            self._proxies = [p for p in self._proxies if not (p.host == host and p.port == port)]
            LOGGER.info("Evicted proxy %s:%s after %d failures", host, port, count)

    @staticmethod
    def _run_stage(
        proxies: Sequence[ProxyEndpoint],
        worker: Callable[[ProxyEndpoint], ProxyProbe],
        max_workers: int,
    ) -> List[ProxyProbe]:
        results: List[ProxyProbe] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(worker, proxy): proxy for proxy in proxies}
            for fut in as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception as exc:  # noqa: BLE001
                    proxy = futures[fut]
                    results.append(
                        ProxyProbe(
                            proxy=proxy,
                            ok=False,
                            status_code=None,
                            latency_ms=float("inf"),
                            error=str(exc),
                            stage="worker",
                        )
                    )
        return results

    @classmethod
    def build(
        cls,
        *,
        source_url: str,
        stage1_url: str,
        stage2_probe: Callable[
            [Dict[str, str]], Tuple[bool, Optional[int], Optional[str]]
        ],
        fetch_limit: int = 300,
        survivors_max: int = 50,
        connect_timeout: float = 2.0,
        read_timeout: float = 4.0,
        max_workers: int = 32,
        latency_threshold_ms: Optional[float] = 1500.0,
        strategy: str = "round_robin",
    ) -> Tuple["ProxyPool", List[ProxyEndpoint], Dict[str, int]]:
        """Fetch, validate, and assemble a proxy pool.

        Returns the pool, the survivor list (endpoints), and stage counts.
        """
        all_proxies = fetch_proxy_list(
            source_url, timeout_seconds=8.0, limit=fetch_limit
        )
        if not all_proxies:
            LOGGER.warning("No proxies fetched from %s", source_url)
            return (
                cls([], strategy=strategy),
                [],
                {"fetched": 0, "stage1": 0, "stage2": 0},
            )

        def stage1_worker(p: ProxyEndpoint) -> ProxyProbe:
            return validate_proxy_generic(
                p,
                url=stage1_url,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                accept_status=(200, 204),
            )

        stage1_results = cls._run_stage(all_proxies, stage1_worker, max_workers)
        s1_ok = [
            r
            for r in stage1_results
            if r.ok and (
                latency_threshold_ms is None or r.latency_ms <= latency_threshold_ms
            )
        ]

        def stage2_worker(p: ProxyEndpoint) -> ProxyProbe:
            return validate_proxy_custom(p, probe=stage2_probe)

        stage2_results = cls._run_stage(
            [r.proxy for r in s1_ok], stage2_worker, max_workers
        )
        s2_ok = [r for r in stage2_results if r.ok]

        # Sort by latency and cap survivors
        s2_ok.sort(key=lambda r: r.latency_ms)
        survivors = [r.proxy for r in s2_ok[: max(1, survivors_max)]]

        counts = {
            "fetched": len(all_proxies),
            "stage1": len(s1_ok),
            "stage2": len(survivors),
        }
        LOGGER.info(
            "Proxy selection: fetched=%d stage1_pass=%d stage2_pass=%d (kept=%d)",
            counts["fetched"],
            counts["stage1"],
            len(s2_ok),
            len(survivors),
        )

        pool = cls(survivors, strategy=strategy)
        return pool, survivors, counts
