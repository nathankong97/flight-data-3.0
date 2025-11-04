#!/usr/bin/env python3
"""Command-line entrypoint for running the flight data job."""

import argparse
import logging

from src.api import FlightRadarClient
from src.config import load_config, AppConfig, REPO_ROOT
from src.db import DatabaseClient
from src.jobs import RunConfig, run_job
from src.logging_utils import configure_logging, perf_span
from src.network import ProxyPool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the flight data ingestion job.")
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
        default=2.0,
        help="Seconds to wait between page fetches (default: 2.0).",
    )
    parser.add_argument(
        "--airport-delay",
        type=float,
        default=15.0,
        help="Seconds to wait between airports (default: 15.0).",
    )
    # Optional proxy support
    parser.add_argument(
        "--use-proxy",
        action="store_true",
        help="Enable proxy validation and concurrent fetching.",
    )
    parser.add_argument(
        "--proxy-fetch-limit",
        type=int,
        default=300,
        help="Max proxies to fetch from the public list (default: 300).",
    )
    parser.add_argument(
        "--proxy-survivor-max",
        type=int,
        default=50,
        help="Max validated proxies to keep for rotation (default: 50).",
    )
    parser.add_argument(
        "--proxy-stage1-url",
        type=str,
        default="https://httpbin.org/ip",
        help="Generic validation URL for proxy reachability.",
    )
    parser.add_argument(
        "--proxy-connect-timeout",
        type=float,
        default=10,
        help="Proxy connect timeout in seconds (default: 10.0).",
    )
    parser.add_argument(
        "--proxy-read-timeout",
        type=float,
        default=10.0,
        help="Proxy read timeout in seconds (default: 10.0).",
    )
    parser.add_argument(
        "--proxy-workers",
        type=int,
        default=16,
        help="Workers used during proxy validation (default: 16).",
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

    db_client = DatabaseClient(config.database_url)

    # Optional proxy pool & concurrency
    proxy_getter = None
    proxy_failure_cb = None
    concurrent_workers = None

    if args.use_proxy:
        from src.api.flightradar import BASE_URL, HEADERS
        import random
        import requests

        def stage2_probe(proxies: dict[str, str]):
            params = {
                "code": random.choice(["HND", "SFO", "JFK", "HKG", "LHR", "YYZ"]),
                "page": random.choice([-1, -2, 1]),
                "limit": 1,
                "plugin[]": "schedule",
                "plugin-setting[schedule][mode]": "departures",
                "_t": str(random.randint(1, 1_000_000)),
            }
            try:
                resp = requests.get(
                    BASE_URL,
                    headers=HEADERS,
                    params=params,
                    timeout=(args.proxy_connect_timeout, args.proxy_read_timeout),
                    proxies=proxies,
                )
                return (200 <= resp.status_code < 300, resp.status_code, None)
            except Exception as exc:  # noqa: BLE001
                return (False, None, str(exc))

        pool, survivors, counts = ProxyPool.build(
            source_url=("https://raw.githubusercontent.com/monosans/proxy-list/refs/heads/main/proxies/http.txt"),
            stage1_url=args.proxy_stage1_url,
            stage2_probe=stage2_probe,
            fetch_limit=args.proxy_fetch_limit,
            survivors_max=args.proxy_survivor_max,
            connect_timeout=args.proxy_connect_timeout,
            read_timeout=args.proxy_read_timeout,
            max_workers=args.proxy_workers,
            latency_threshold_ms=15000.0,
            strategy="round_robin",
        )

        logging.getLogger(__name__).info(
            "Proxy build: fetched=%s stage1=%s stage2=%s",
            counts.get("fetched"),
            counts.get("stage1"),
            counts.get("stage2"),
        )

        if survivors:
            proxy_getter = pool.get_proxies_for_request
            proxy_failure_cb = pool.report_failure
            concurrent_workers = min(len(survivors), 8)

    api_client = FlightRadarClient(
        get_proxies=proxy_getter,
        report_proxy_failure=proxy_failure_cb,
    )

    run_config = RunConfig(
        region=args.region,
        max_pages=args.max_pages,
        limit_per_page=args.limit,
        retry_attempts=args.retry_attempts,
        retry_delay_seconds=args.retry_delay,
        page_delay_seconds=args.page_delay,
        airport_delay_seconds=args.airport_delay,
        concurrent_workers=concurrent_workers,
    )

    try:
        with perf_span(
            "job.total",
            tags={"region": run_config.region, "app": config.app_name},
        ):
            run_job(config, db_client, api_client, run_config)
    finally:
        api_client.close()
        db_client.close()

    return 0


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    raise SystemExit(main())
