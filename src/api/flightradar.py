"""Client for the FlightRadar24 airport schedule endpoint."""

from typing import Any, Dict, Optional

import requests

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

    def __init__(self, session: Optional[requests.Session] = None, timeout: float = 10.0) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout

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

    def fetch_departures(
        self,
        airport_code: str,
        *,
        page: int = 1,
        limit: int = 100,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch the scheduled departures for a specific airport/page."""

        if not airport_code:
            raise ValueError("airport_code must be provided")
        if page < 1:
            raise ValueError("page must be >= 1")
        if limit <= 0:
            raise ValueError("limit must be positive")

        params = self._build_params(airport_code, page, limit, timestamp)
        response = self._session.get(
            BASE_URL,
            headers=HEADERS,
            params=params,
            timeout=self._timeout,
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
