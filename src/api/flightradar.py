"""Client for the FlightRadar24 airport schedule endpoint.

Adds optional request-route logging (proxy vs direct) and supports forcing
direct calls for guarded fallback scenarios.
"""

from typing import Any, Callable, Dict, Optional

import requests
import logging
from src.logging_utils import perf

BASE_URL = "https://api.flightradar24.com/common/v1/airport.json"
HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/84.0.4147.105 Safari/537.36"
    )
}


class FlightRadarClient:
    """Simple wrapper around the FlightRadar airport schedule API."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
        get_proxies: Optional[Callable[[], Optional[Dict[str, str]]]] = None,
        report_proxy_failure: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> None:
        """Initialize the API client.

        Args:
            session: Optional pre-configured Requests session.
            timeout: Per-request timeout in seconds.
            get_proxies: Optional callable returning a Requests ``proxies`` mapping
                to route traffic via a proxy. If None, requests use direct network.
            report_proxy_failure: Optional callback invoked when a request fails
                while using a given proxies mapping.
        """
        self._session = session or requests.Session()
        self._timeout = timeout
        self._get_proxies = get_proxies
        self._report_proxy_failure = report_proxy_failure

    def _build_params(
        self,
        airport_code: str,
        page: int,
        limit: int,
        timestamp: Optional[int],
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "code": airport_code,
            "page": page,
            "limit": limit,
            "plugin[]": "schedule",
            "plugin-setting[schedule][mode]": "departures",
        }
        if timestamp is not None:
            params["plugin-setting[schedule][timestamp]"] = timestamp
        return params

    @perf("api.fetch_departures", tags={"component": "api"})
    def fetch_departures(
        self,
        airport_code: str,
        *,
        page: int = 1,
        limit: int = 100,
        timestamp: Optional[int] = None,
        force_proxies: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Fetch the scheduled departures for a specific airport/page."""

        if not airport_code:
            raise ValueError("airport_code must be provided")
        if page == 0:
            raise ValueError("page must be != 0")
        if limit <= 0:
            raise ValueError("limit must be positive")

        params = self._build_params(airport_code, page, limit, timestamp)
        proxies: Optional[Dict[str, str]] = None
        # Determine routing: proxy vs direct
        if force_proxies is False:
            proxies = None
        elif self._get_proxies is not None:
            try:
                proxies = self._get_proxies()
            except Exception:  # pragma: no cover - defensive
                proxies = None

        # Log the route used at DEBUG level for diagnostics
        route = "proxy" if proxies else "direct"
        if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
            px = proxies.get("http") if proxies else None
            masked = None
            if px:
                try:
                    # mask host (keep first octet only)
                    host_port = px.split("//", 1)[-1]
                    host = host_port.split(":", 1)[0]
                    parts = host.split(".")
                    masked = (parts[0] + ".x.x.x") if len(parts) == 4 else host
                except Exception:  # pragma: no cover - defensive
                    masked = "unknown"
            logging.getLogger(__name__).debug(
                "api.fetch_departures via=%s airport=%s page=%s proxy=%s",
                route,
                airport_code,
                page,
                masked,
            )

        # Perform request; only treat transport-level failures as proxy failures
        try:
            response = self._session.get(
                BASE_URL,
                headers=HEADERS,
                params=params,
                timeout=self._timeout,
                proxies=proxies,
            )
        except Exception:
            # Notify pool of failure for this proxies mapping if provided
            if proxies and self._report_proxy_failure is not None:
                try:
                    self._report_proxy_failure(proxies)
                except Exception:  # pragma: no cover - defensive
                    pass
            raise

        # Log 429 Retry-After if present (do not mark proxy as failed here)
        if response.status_code == 429:
            ra = response.headers.get("Retry-After")
            logging.getLogger(__name__).debug(
                "api.fetch_departures got 429 airport=%s page=%s retry_after=%s",
                airport_code,
                page,
                ra,
            )

        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "FlightRadarClient":
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self.close()


__all__ = ["FlightRadarClient", "BASE_URL", "HEADERS"]
