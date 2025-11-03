# Running the Flight Data Ingestion Job (scripts/run_job.py)

This document explains how to run the CLI entrypoint that orchestrates fetching
scheduled departures from FlightRadar24, transforming them into typed records,
and persisting them to PostgreSQL.

## Prerequisites

- Create and activate a virtual environment, then install dependencies:
  - Linux/macOS:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install -r requirements.txt
    ```
  - Windows (PowerShell):
    ```powershell
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    py -m pip install -r requirements.txt
    ```
- Configure environment (see `.env.example`). Either provide:
  - `DATABASE_URL=postgresql://user:pass@host:5432/db`, or
  - Components `HOST`, `USER`, `PASSWORD`, `DB`, `PORT` (the loader builds a DSN)
- Optional logging keys: `LOG_DIR`, `LOG_LEVEL`, `APP_NAME`

## Invocation

Run the script as a module:
- Linux/macOS:
  ```bash
  python3 -m scripts.run_job <REGION> [options]
  ```
- Windows (PowerShell):
  ```powershell
  py -m scripts.run_job <REGION> [options]
  ```

`<REGION>` must correspond to a file `data/airport_<REGION>.txt`.

Currently present region files include: `CA`, `CN`, `EA`, `JP`, `TW`, `US`, and more may be added over time.

To see available regions programmatically (from this project):

```bash
python3 -c "from src.airport_codes import available_regions; print(available_regions())"
```
```powershell
py -c "from src.airport_codes import available_regions; print(available_regions())"
```

## Options

- `--max-pages <int>`: Optional max pages per airport (default: all pages from legacy offset).
- `--limit <int>`: Rows per page to request (default: `100`).
- `--retry-attempts <int>`: API retry attempts (default: `3`).
- `--retry-delay <float>`: Seconds between API retries (default: `2.0`).
- `--page-delay <float>`: Seconds to wait between page fetches (default: `2.0`).
- `--airport-delay <float>`: Seconds to wait between airports (default: `15.0`).

Proxy and concurrency (optional):
- `--use-proxy`: Enable proxy validation and concurrent fetching.
- `--proxy-fetch-limit <int>`: Max proxies to fetch (default: `300`).
- `--proxy-survivor-max <int>`: Max validated proxies to keep (default: `50`).
- `--proxy-stage1-url <str>`: Generic validation URL (default: `https://httpbin.org/ip`).
- `--proxy-connect-timeout <float>`: Proxy connect timeout seconds (default: `10`).
- `--proxy-read-timeout <float>`: Proxy read timeout seconds (default: `10.0`).
- `--proxy-workers <int>`: Workers used during proxy validation (default: `16`).

## Behavior

- Pagination: The job determines the starting page per airport index using
  `src/pagination.py` and iterates pages (excluding 0). Use `--max-pages` to cap work.
- Logging: Per-run structured logs are written under `logs/` with a file name
  based on `APP_NAME` and a run id (see `src/logging_utils.py`). Set `LOG_DIR`/`LOG_LEVEL`
  in `.env` to customize.
- Concurrency: When `--use-proxy` is enabled and validated proxies survive, the job processes
  airport pages concurrently using a thread pool sized to `min(survivors, 8)`.
- Database: Requires a reachable PostgreSQL configured via `.env`. See migrations in `migrations/`.
- Exit codes: Returns `0` on success. If configuration fails, the script logs an error and exits with `1`.

## Examples

Sequential run with a single page per airport:
- Linux/macOS:
  ```bash
  python3 -m scripts.run_job JP --max-pages 1 --limit 100
  ```
- Windows:
  ```powershell
  py -m scripts.run_job JP --max-pages 1 --limit 100
  ```

Enable proxies with a small candidate set (may enable concurrency if survivors exist):
- Linux/macOS:
  ```bash
  python3 -m scripts.run_job JP --use-proxy --proxy-fetch-limit 30 --proxy-survivor-max 10
  ```
- Windows:
  ```powershell
  py -m scripts.run_job JP --use-proxy --proxy-fetch-limit 30 --proxy-survivor-max 10
  ```

Schedule examples are available in `scripts/flight-data.cron`.
