"""Helpers for retrieving airport coordinate reference data."""

import logging
from typing import Dict

from src.db import DatabaseClient
from src.logging_utils import perf

LOGGER = logging.getLogger(__name__)

COORDINATE_QUERY = """
    SELECT iata, latitude, longitude
    FROM airports
    WHERE iata IS NOT NULL
"""


@perf("reference.load_coordinates", tags={"component": "reference"})
def load_coordinates(db_client: DatabaseClient) -> Dict[str, Dict[str, float]]:
    """Return a mapping of IATA code to latitude/longitude."""

    try:
        rows = db_client.fetch_all(COORDINATE_QUERY)
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.warning("Failed to load airport coordinates: %s", exc)
        return {}

    mapping: Dict[str, Dict[str, float]] = {}
    for row in rows:
        iata = (row.get("iata") or "").upper()
        lat = row.get("latitude")
        lng = row.get("longitude")
        if not iata or lat is None or lng is None:
            continue
        mapping[iata] = {"lat": float(lat), "lng": float(lng)}

    LOGGER.info("Loaded %s airport coordinate entries", len(mapping))
    return mapping


__all__ = ["load_coordinates"]
