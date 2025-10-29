import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest

import src.network.proxy_pool as proxy_mod


class DummyResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if not (200 <= self.status_code < 400):
            raise RuntimeError(f"HTTP {self.status_code}")


def test_parse_proxy_line_valid_and_invalid() -> None:
    assert proxy_mod._parse_proxy_line("1.2.3.4:8080") == proxy_mod.ProxyEndpoint(
        host="1.2.3.4", port=8080
    )
    assert proxy_mod._parse_proxy_line("bad") is None
    assert proxy_mod._parse_proxy_line("1.2.3.4:abc") is None


def test_fetch_proxy_list_dedup_and_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = "\n".join([
        "1.1.1.1:80",
        "2.2.2.2:8080",
        "1.1.1.1:80",  # dup
        "badline",
    ])

    def fake_get(url, timeout):  # type: ignore[no-redef]
        assert "http" in url
        return DummyResponse(200, text=lines)

    monkeypatch.setattr(proxy_mod.requests, "get", fake_get)
    # Avoid randomness in tests
    monkeypatch.setattr(proxy_mod.random, "shuffle", lambda x: None)

    proxies = proxy_mod.fetch_proxy_list("http://example/proxies.txt", limit=2)
    assert len(proxies) == 2
    assert proxies[0].host == "1.1.1.1"
    assert proxies[1].port == 8080


def test_validate_proxy_generic_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url, timeout, proxies, headers):  # type: ignore[no-redef]
        return DummyResponse(200)

    monkeypatch.setattr(proxy_mod.requests, "get", fake_get)
    endpoint = proxy_mod.ProxyEndpoint("8.8.8.8", 3128)
    probe = proxy_mod.validate_proxy_generic(endpoint, url="https://httpbin.org/ip")
    assert probe.ok is True
    assert probe.status_code == 200
    assert probe.stage == "generic"


def test_validate_proxy_generic_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url, timeout, proxies, headers):  # type: ignore[no-redef]
        raise TimeoutError("timeout")

    monkeypatch.setattr(proxy_mod.requests, "get", fake_get)
    endpoint = proxy_mod.ProxyEndpoint("8.8.4.4", 8080)
    probe = proxy_mod.validate_proxy_generic(endpoint, url="https://httpbin.org/ip")
    assert probe.ok is False
    assert probe.error is not None


def test_proxy_pool_rotation_and_eviction() -> None:
    pool = proxy_mod.ProxyPool(
        [proxy_mod.ProxyEndpoint("1.1.1.1", 80), proxy_mod.ProxyEndpoint("2.2.2.2", 8080)],
        max_failures=2,
        strategy="round_robin",
    )

    p1 = pool.get_proxies_for_request()
    p2 = pool.get_proxies_for_request()
    assert p1 != p2

    # Trigger failures for first proxy until eviction
    assert p1 is not None
    pool.report_failure(p1)
    pool.report_failure(p1)

    # Consume until only the second remains
    next_map = pool.get_proxies_for_request()
    assert next_map == p2

    # Evict the second as well
    assert next_map is not None
    pool.report_failure(next_map)
    pool.report_failure(next_map)
    assert pool.is_empty()


def test_build_uses_stage_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    # Provide three endpoints
    monkeypatch.setattr(
        proxy_mod, "fetch_proxy_list", lambda *a, **k: [
            proxy_mod.ProxyEndpoint("1.1.1.1", 80),
            proxy_mod.ProxyEndpoint("2.2.2.2", 8080),
            proxy_mod.ProxyEndpoint("3.3.3.3", 3128),
        ]
    )

    # Stage 1 generic validates all
    monkeypatch.setattr(
        proxy_mod.requests,
        "get",
        lambda *a, **k: DummyResponse(200),
    )

    # Stage 2 probe fails only the last
    def stage2_probe(proxies: Dict[str, str]) -> Tuple[bool, Optional[int], Optional[str]]:
        http_url = proxies.get("http", "")
        ok = not http_url.endswith(":3128")
        return ok, 200 if ok else 502, None if ok else "bad"

    pool, survivors, counts = proxy_mod.ProxyPool.build(
        source_url="http://example/list.txt",
        stage1_url="https://httpbin.org/ip",
        stage2_probe=stage2_probe,
        fetch_limit=10,
        survivors_max=5,
        max_workers=4,
    )

    assert counts["fetched"] == 3
    assert counts["stage1"] == 3
    assert counts["stage2"] == 2
    assert len(survivors) == 2
    # Ensure pool returns a proxies mapping for requests
    mapping = pool.get_proxies_for_request()
    assert mapping and "http" in mapping

