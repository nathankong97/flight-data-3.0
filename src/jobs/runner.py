"""Job runner orchestrating API fetch, transform, and persistence."""

import logging
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.airport_codes import load_airport_codes
from src.api import FlightRadarClient
from src.config import AppConfig
from src.db import DatabaseClient
from src.pagination import page_for_index
from src.persistence import upsert_flights
from src.reference import load_coordinates
from src.logging_utils import perf, perf_span
from src.alerts import install_telegram_log_handler_from_env
from src.transform import extract_departure_records

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunConfig:
    region: str
    max_pages: Optional[int] = None
    limit_per_page: int = 100
    retry_attempts: int = 3
    retry_delay_seconds: float = 2.0
    page_delay_seconds: float = 5.0
    airport_delay_seconds: float = 30.0
    concurrent_workers: Optional[int] = None
    direct_fallback: bool = False
    direct_fallback_on_429: bool = False
    proxy_attempts: Optional[int] = None  # if None, use retry_attempts - direct_attempts
    direct_attempts: int = 1
    degraded_fail_threshold: int = 1


def _page_sequence(start_page: int, max_pages: Optional[int]) -> List[int]:
    pages = [page for page in range(start_page, 2) if page != 0]
    if max_pages is None:
        return pages
    return pages[:max_pages]


@perf("jobs.run_job", tags={"component": "jobs"})
def run_job(
    config: AppConfig,
    db_client: DatabaseClient,
    api_client: FlightRadarClient,
    job_config: RunConfig,
) -> str:
    # Enable Telegram alerts when configured; logs a warning if not configured.
    install_telegram_log_handler_from_env()
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

    # If concurrent workers requested, switch to parallel page processing
    if job_config.concurrent_workers and job_config.concurrent_workers > 1:
        _run_concurrent(
            airports,
            job_config,
            api_client,
            db_client,
            ingest_run_id,
            coordinates,
        )
        LOGGER.info("%s run %s completed", job_name, ingest_run_id)
        return ingest_run_id

    giveups = 0

    for index, airport in enumerate(airports):
        oldest_page = page_for_index(job_config.region, index)
        pages = _page_sequence(oldest_page, job_config.max_pages)
        LOGGER.info(
            "Processing airport %s (index %s) pages %s",
            airport,
            index,
            pages,
        )

        with perf_span(
            "jobs.airport_loop",
            tags={"airport": airport, "index": index},
            logger=LOGGER,
        ):
            for page in pages:
                payload = _fetch_with_retries(
                    api_client,
                    airport,
                    page,
                    job_config.limit_per_page,
                    job_config.retry_attempts,
                    job_config.retry_delay_seconds,
                    job_config=job_config,
                )
                if not payload:
                    giveups += 1
                    continue

                with perf_span(
                    "jobs.page_loop",
                    tags={"airport": airport, "page": page},
                    logger=LOGGER,
                ):
                    records = extract_departure_records(
                        payload,
                        airport,
                        coordinates=coordinates,
                    )
                    if not records:
                        LOGGER.info("No records returned for %s page %s", airport, page)
                        # Even when empty, honor page delay throttling
                        if job_config.page_delay_seconds > 0 and page != pages[-1]:
                            LOGGER.debug(
                                "Sleeping %.1fs between pages for %s",
                                job_config.page_delay_seconds,
                                airport,
                            )
                            time.sleep(job_config.page_delay_seconds)
                        continue

                    upsert_count = upsert_flights(db_client, ingest_run_id, records)
                    LOGGER.info("Upserted %s records for %s page %s", upsert_count, airport, page)
                    # Throttle between page fetches
                    if job_config.page_delay_seconds > 0 and page != pages[-1]:
                        LOGGER.debug(
                            "Sleeping %.1fs between pages for %s",
                            job_config.page_delay_seconds,
                            airport,
                        )
                        time.sleep(job_config.page_delay_seconds)

        # Throttle between airports
        if job_config.airport_delay_seconds > 0 and index < len(airports) - 1:
            LOGGER.debug(
                "Sleeping %.1fs before next airport",
                job_config.airport_delay_seconds,
            )
            time.sleep(job_config.airport_delay_seconds)
    # End-of-run summary
    if giveups > job_config.degraded_fail_threshold:
        LOGGER.warning(
            "Run summary: giveups=%s threshold=%s status=DEGRADED",
            giveups,
            job_config.degraded_fail_threshold,
        )
    else:
        LOGGER.info(
            "Run summary: giveups=%s threshold=%s status=OK",
            giveups,
            job_config.degraded_fail_threshold,
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
    *,
    job_config: RunConfig,
):
    """Fetch with retries, optionally falling back to a direct attempt.

    Returns the payload dict on success, or None after exhausting attempts.
    """
    import requests  # local import to keep module import surface minimal

    # Determine attempt split
    proxy_attempts = (
        job_config.proxy_attempts
        if job_config.proxy_attempts is not None
        else max(0, attempts - (job_config.direct_attempts if job_config.direct_fallback else 0))
    )
    direct_attempts = job_config.direct_attempts if job_config.direct_fallback else 0

    # Proxy phase
    for attempt in range(1, proxy_attempts + 1):
        try:
            return api_client.fetch_departures(
                airport,
                page=page,
                limit=limit,
                force_proxies=True,
            )
        except Exception as exc:  # noqa: BLE001
            total = proxy_attempts + direct_attempts if job_config.direct_fallback else attempts
            LOGGER.warning(
                "API fetch failed for %s page %s (attempt %s/%s): %s",
                airport,
                page,
                attempt,
                total,
                exc,
            )
            # Special handling for HTTP 429: respect Retry-After when present
            sleep_s = delay_seconds
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                status = getattr(exc.response, "status_code", None)
                if status == 429:
                    ra = exc.response.headers.get("Retry-After")
                    try:
                        # Retry-After can be seconds or HTTP date; assume seconds here
                        sleep_s = float(ra) if ra is not None else max(delay_seconds * 2, 30.0)
                    except Exception:
                        sleep_s = max(delay_seconds * 2, 30.0)
                    # If direct fallback is allowed on 429, break to direct phase on last proxy try
                    if job_config.direct_fallback and job_config.direct_fallback_on_429 and attempt == proxy_attempts:
                        LOGGER.info(
                            "Falling back to direct for %s page %s after %s proxy attempts (last=429)",
                            airport,
                            page,
                            proxy_attempts,
                        )
                        break
            if attempt == proxy_attempts and not job_config.direct_fallback:
                LOGGER.error(
                    "Giving up on airport %s page %s after %s attempts",
                    airport,
                    page,
                    proxy_attempts,
                )
                return None
            time.sleep(sleep_s)

    # Direct phase (optional)
    for d_attempt in range(1, direct_attempts + 1):
        try:
            return api_client.fetch_departures(
                airport,
                page=page,
                limit=limit,
                force_proxies=False,
            )
        except Exception as exc:  # noqa: BLE001
            total = proxy_attempts + direct_attempts if job_config.direct_fallback else attempts
            current = proxy_attempts + d_attempt
            LOGGER.warning(
                "API fetch failed for %s page %s (attempt %s/%s, route=direct): %s",
                airport,
                page,
                current,
                total,
                exc,
            )
            if d_attempt == direct_attempts:
                LOGGER.error(
                    "Giving up on airport %s page %s after %s attempts",
                    airport,
                    page,
                    total,
                )
                return None
            # Respect Retry-After if present for 429
            sleep_s = delay_seconds
            if (
                isinstance(exc, requests.HTTPError)
                and exc.response is not None
                and getattr(exc.response, "status_code", None) == 429
            ):
                ra = exc.response.headers.get("Retry-After")
                try:
                    sleep_s = float(ra) if ra is not None else max(delay_seconds * 2, 30.0)
                except Exception:
                    sleep_s = max(delay_seconds * 2, 30.0)
            time.sleep(sleep_s)
    return None


def _build_tasks(region: str, airports: List[str], max_pages: Optional[int]) -> List[Tuple[str, int]]:
    tasks: List[Tuple[str, int]] = []
    for index, airport in enumerate(airports):
        oldest_page = page_for_index(region, index)
        pages = _page_sequence(oldest_page, max_pages)
        for page in pages:
            tasks.append((airport, page))
    return tasks


def _run_concurrent(
    airports: List[str],
    job_config: RunConfig,
    api_client: FlightRadarClient,
    db_client: DatabaseClient,
    ingest_run_id: str,
    coordinates,
) -> None:
    tasks = _build_tasks(job_config.region, airports, job_config.max_pages)
    if not tasks:
        LOGGER.info("No tasks to process for region %s", job_config.region)
        return

    LOGGER.info(
        "Starting concurrent fetch with %d workers over %d tasks",
        job_config.concurrent_workers,
        len(tasks),
    )

    def worker(task: Tuple[str, int]) -> Tuple[str, int, int, bool]:
        airport, page = task
        payload = _fetch_with_retries(
            api_client,
            airport,
            page,
            job_config.limit_per_page,
            job_config.retry_attempts,
            job_config.retry_delay_seconds,
            job_config=job_config,
        )
        if not payload:
            return airport, page, 0, True
        records = extract_departure_records(payload, airport, coordinates=coordinates)
        if not records:
            return airport, page, 0, False
        count = upsert_flights(db_client, ingest_run_id, records)
        return airport, page, count, False

    with ThreadPoolExecutor(max_workers=job_config.concurrent_workers) as executor:
        future_map = {executor.submit(worker, t): t for t in tasks}
        giveups = 0
        for fut in as_completed(future_map):
            airport, page, count, gave_up = fut.result()
            if count > 0:
                LOGGER.info("Upserted %s records for %s page %s", count, airport, page)
            if gave_up:
                giveups += 1

    # End-of-run summary (concurrent)
    if giveups > job_config.degraded_fail_threshold:
        LOGGER.warning(
            "Run summary: giveups=%s threshold=%s status=DEGRADED",
            giveups,
            job_config.degraded_fail_threshold,
        )
    else:
        LOGGER.info(
            "Run summary: giveups=%s threshold=%s status=OK",
            giveups,
            job_config.degraded_fail_threshold,
        )


__all__ = ["RunConfig", "run_job"]
