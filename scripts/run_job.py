#!/usr/bin/env python3
"""Command-line entrypoint for running the flight data job."""

import argparse
import logging

from src.api import FlightRadarClient
from src.config import load_config, AppConfig, REPO_ROOT
from src.db import DatabaseClient
from src.jobs import RunConfig, run_job
from src.logging_utils import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the flight data ingestion job."
    )
    parser.add_argument(
        "region",
        help="Region code matching airport list files (e.g., JP, US).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional max pages per airport to fetch (defaults to all).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Rows per page to request from the API (default: 100).",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=3,
        help="Number of retry attempts for failed API calls (default: 3).",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Seconds to wait between API retries (default: 2.0).",
    )
    parser.add_argument(
        "--page-delay",
        type=float,
        default=5.0,
        help="Seconds to wait between page fetches (default: 5.0).",
    )
    parser.add_argument(
        "--airport-delay",
        type=float,
        default=30.0,
        help="Seconds to wait between airports (default: 30.0).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config()
    except Exception as exc:  # noqa: BLE001 - log and exit gracefully with a file
        # Fall back to a default log location so failures are still captured per run.
        fallback = AppConfig(
            database_url="postgresql://invalid",  # unused for logging setup
            log_directory=REPO_ROOT / "logs",
            log_level="INFO",
        )
        log_path = configure_logging(fallback)
        logging.getLogger(__name__).error("Failed to load configuration: %s", exc)
        # Ensure the error is flushed to the log file before exiting.
        for handler in logging.getLogger().handlers:
            try:
                handler.flush()
            except Exception:  # pragma: no cover - defensive
                pass
        return 1

    configure_logging(config)

    run_config = RunConfig(
        region=args.region,
        max_pages=args.max_pages,
        limit_per_page=args.limit,
        retry_attempts=args.retry_attempts,
        retry_delay_seconds=args.retry_delay,
        page_delay_seconds=args.page_delay,
        airport_delay_seconds=args.airport_delay,
    )

    db_client = DatabaseClient(config.database_url)
    api_client = FlightRadarClient()

    try:
        run_job(config, db_client, api_client, run_config)
    finally:
        api_client.close()
        db_client.close()

    return 0


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    raise SystemExit(main())
