"""Job runner orchestrating API fetch, transform, and persistence."""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

from src.airport_codes import load_airport_codes
from src.api import FlightRadarClient
from src.config import AppConfig
from src.db import DatabaseClient
from src.pagination import page_for_index
from src.persistence import upsert_flights
from src.reference import load_coordinates
from src.transform import extract_departure_records

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunConfig:
    region: str
    max_pages: Optional[int] = None
    limit_per_page: int = 100
    retry_attempts: int = 3
    retry_delay_seconds: float = 2.0


def _page_sequence(start_page: int, max_pages: Optional[int]) -> List[int]:
    pages = [page for page in range(start_page, 2) if page != 0]
    if max_pages is None:
        return pages
    return pages[:max_pages]


def run_job(
    config: AppConfig,
    db_client: DatabaseClient,
    api_client: FlightRadarClient,
    job_config: RunConfig,
) -> str:
    ingest_run_id = str(uuid.uuid4())
    job_name = getattr(config, "app_name", "flight-data")
    airports = load_airport_codes(job_config.region)
    if not airports:
        LOGGER.warning("No airports configured for region %s", job_config.region)
        return ingest_run_id

    coordinates = load_coordinates(db_client)
    LOGGER.info("Using %s coordinate entries", len(coordinates))

    LOGGER.info(
        "%s run %s started for region %s",
        job_name,
        ingest_run_id,
        job_config.region,
    )

    for index, airport in enumerate(airports):
        oldest_page = page_for_index(job_config.region, index)
        pages = _page_sequence(oldest_page, job_config.max_pages)
        LOGGER.info(
            "Processing airport %s (index %s) pages %s",
            airport,
            index,
            pages,
        )

        for page in pages:
            payload = _fetch_with_retries(
                api_client,
                airport,
                page,
                job_config.limit_per_page,
                job_config.retry_attempts,
                job_config.retry_delay_seconds,
            )
            if not payload:
                continue

            records = extract_departure_records(
                payload,
                airport,
                coordinates=coordinates,
            )
            if not records:
                LOGGER.info("No records returned for %s page %s", airport, page)
                continue

            upsert_count = upsert_flights(db_client, ingest_run_id, records)
            LOGGER.info(
                "Upserted %s records for %s page %s", upsert_count, airport, page
            )

    LOGGER.info("%s run %s completed", job_name, ingest_run_id)
    return ingest_run_id


def _fetch_with_retries(
    api_client: FlightRadarClient,
    airport: str,
    page: int,
    limit: int,
    attempts: int,
    delay_seconds: float,
):
    for attempt in range(1, attempts + 1):
        try:
            return api_client.fetch_departures(
                airport,
                page=page,
                limit=limit,
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning(
                "API fetch failed for %s page %s (attempt %s/%s): %s",
                airport,
                page,
                attempt,
                attempts,
                exc,
            )
            if attempt == attempts:
                LOGGER.error(
                    "Giving up on airport %s page %s after %s attempts",
                    airport,
                    page,
                    attempts,
                )
                return None
            time.sleep(delay_seconds)
    return None


__all__ = ["RunConfig", "run_job"]
