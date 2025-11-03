# Flight Data 3.0 ✈️

Ingest scheduled departures from FlightRadar24, transform them into structured records, and persist them to PostgreSQL. Includes a job runner, typed transforms, and a thin psycopg v3 client.

See `AGENTS.md` for conventions and contributor guidelines.

## Quickstart 🚀

1) Create a virtual environment and install deps

- Linux/macOS:
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  python3 -m pip install -r requirements.txt
  ```
- Windows (PowerShell):
  ```powershell
  py -m venv .venv; .\.venv\Scripts\Activate.ps1
  py -m pip install -r requirements.txt
  ```

2) Configure environment

- Copy `.env.example` to `.env` and adjust values.
- Preferred: set a full DSN in `DATABASE_URL` (or provide `HOST`, `USER`, `PASSWORD`, `DB`, `PORT`).
- Optional logging overrides in `.env`: `LOG_DIR`, `LOG_LEVEL`, `APP_NAME`.

3) Run the job

- Example (fetch JP airports, one page per airport):
  ```bash
  python3 scripts/run_job.py JP --max-pages 1 --limit 100
  ```

Logs are written per run to `logs/<app>-<run_id>.log` (see `src/logging_utils.py`).

For complete CLI usage, options, and examples, see `docs/run_job.md`.

For performance logging helpers, see `docs/performance_tools.md`.

## Project Layout 🧭

- `src/api/` — HTTP client (FlightRadar24)
- `src/transform/` — parse and normalize API payloads into `FlightRecord`
- `src/persistence/` — upsert helpers for the `flights` fact table
- `src/db/` — psycopg v3 pool wrapper
- `src/jobs/` — orchestration (fetch → transform → persist)
- `src/reference/` — coordinate lookup from DB
- `src/pagination.py` — index/page mapping per region
- `data/airport_<REGION>.txt` — ordered airport lists used by pagination (order matters)
- `migrations/` — PostgreSQL DDL for reference and fact tables
- `scripts/run_job.py` — CLI entrypoint
- `scripts/update_flights_commercial_view.py` — refresh the commercial flights view

## Testing 🧪

- Unit tests: `pytest -q`
- Skip integration tests: `pytest -q -m "not integration"`
- Only integration tests: `pytest -q -m integration`

Integration tests require a reachable PostgreSQL and (for API tests) outbound network access.

## Database (PostgreSQL) 🗄️

- Start Postgres via Docker:
  ```bash
  docker run --name flight-db -e POSTGRES_PASSWORD=dev -p 5432:5432 -d postgres:15
  ```
- Set `DATABASE_URL`, for example:
  ```bash
  export DATABASE_URL='postgresql://postgres:dev@127.0.0.1:5432/postgres'
  ```
  ```powershell
  $env:DATABASE_URL = 'postgresql://postgres:dev@127.0.0.1:5432/postgres'
  ```
- Apply schema (DDL lives in `migrations/`):
  ```bash
  psql "$DATABASE_URL" -f migrations/001_create_airports.sql
  psql "$DATABASE_URL" -f migrations/002_create_airlines.sql
  psql "$DATABASE_URL" -f migrations/003_create_aircrafts.sql
  psql "$DATABASE_URL" -f migrations/004_create_countries.sql
  psql "$DATABASE_URL" -f migrations/005_create_flights.sql
  psql "$DATABASE_URL" -f migrations/006_create_flights_commercial_view.sql
  ```

### Commercial Flights View

- Create with migration `006_create_flights_commercial_view.sql`.
- Update airline blocklist in `data/filtered_airlines.txt`, then:
  ```bash
  python3 scripts/update_flights_commercial_view.py
  ```

## Optional Proxy (Concurrent Fetch) 🔌

- Default: no proxy, sequential fetching.
- With `--use-proxy` the job:
  - Fetches a public HTTP proxy list (ip:port),
  - Validates proxies in two stages (generic HTTPS; then FlightRadar24 probe),
  - Uses survivors for concurrent fetching and evicts failing proxies,
  - Falls back to direct, sequential fetching if no survivors are available.
- Concurrency: when survivors exist, a thread pool sized to `min(survivors, 8)` processes pages.
- Example:
  ```bash
  python3 scripts/run_job.py JP --use-proxy --proxy-fetch-limit 30 --proxy-survivor-max 10
  ```

## Secrets & Remote Access 🔐

- Do not commit credentials. `.env` is ignored.
- Use SSH tunnels or cloud IAM tokens to avoid storing DB passwords on disk.
  ```bash
  ssh -N -L 5433:127.0.0.1:5432 user@server
  # DATABASE_URL=postgresql://app@127.0.0.1:5433/db?sslmode=require
  ```

## Developer Tips 🛠️

- Absolute imports (`src.`) keep modules importable without packaging.
- PEP 8, type hints, Google-style docstrings.
- Optional tools (install locally): `black src tests`, `ruff check src tests`.

## Troubleshooting 🧰

- "DATABASE_URL must be defined": set `DATABASE_URL` or component variables (`HOST/USER/PASSWORD/DB`).
- API 4xx/5xx: rate limits can apply; try lowering `--limit` and adding retries.
- No rows ingested: confirm airport list for your region in `data/` and DB connectivity.

---

Happy flying! 🛫

