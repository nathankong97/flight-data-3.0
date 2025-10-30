# Flight Data 3.0

Ingest scheduled flight departures from FlightRadar24, transform them into structured records, and
persist them to PostgreSQL. The repo includes a job runner, a typed transform layer, and a thin DB
client backed by psycopg v3.

(2025 ver.)

- Runtime code lives under `src/`
- Tests live under `tests/` and `integration_tests/`
- Airport lists live under `data/airport_<REGION>.txt` (order matters for pagination)

See `AGENTS.md` for project conventions and contributor guidelines.

## Quickstart

1) Create a virtual environment and install deps

- Bash
  - `python3 -m venv .venv && source .venv/bin/activate`
  - `python3 -m pip install -r requirements.txt`
- PowerShell
  - `py -m venv .venv; .\\.venv\\Scripts\\Activate.ps1`
  - `py -m pip install -r requirements.txt`

2) Configure environment

- Preferred: set a full DSN in `DATABASE_URL`, e.g.
  - Bash: `export DATABASE_URL='postgresql://user:pass@host:5432/db'`
  - PowerShell: `$env:DATABASE_URL = 'postgresql://user:pass@host:5432/db'`
- Or provide components in a `.env` (git-ignored):
  - `HOST=localhost`, `USER=app`, `PASSWORD=secret`, `DB=flights`, `PORT=5432`
- Optional logging overrides:
  - `LOG_DIR=logs` and `LOG_LEVEL=INFO` (default: INFO)

3) Run the job

- Example (fetch JP airports, one page per airport):
  - `python3 scripts/run_job.py JP --max-pages 1 --limit 100`

Logs are written per run to `logs/<app>-<run_id>.log` (see `src/logging_utils.py`).

## Project Layout

- `src/api/` — HTTP clients (FlightRadar24)
- `src/transform/` — parse and normalize API payloads into `FlightRecord`
- `src/persistence/` — upsert helpers for the `flights` fact table
- `src/db/` — psycopg v3 pool wrapper
- `src/jobs/` — orchestration (fetch → transform → persist)
- `src/reference/` — coordinate lookup from DB
- `src/pagination.py` — index→page mapping per region
- `data/airport_<REGION>.txt` — ordered airport lists used by pagination (order matters)
- `migrations/` — PostgreSQL DDL for reference and fact tables
- `scripts/run_job.py` — CLI entrypoint
- `scripts/update_flights_commercial_view.py` — update the commercial flights view from `data/filtered_airlines.txt`

## Testing

- Run unit tests: `pytest -q`
- Skip integration tests: `pytest -q -m "not integration"`
- Run only integration tests: `pytest -q -m integration`

Integration tests require a reachable PostgreSQL and (for API tests) outbound network access.

## Database (PostgreSQL)

- Start a local Postgres via Docker:
  - `docker run --name flight-db -e POSTGRES_PASSWORD=dev -p 5432:5432 -d postgres:15`
- Set `DATABASE_URL`, for example:
  - Bash: `export DATABASE_URL='postgresql://postgres:dev@127.0.0.1:5432/postgres'`
  - PowerShell: `$env:DATABASE_URL = 'postgresql://postgres:dev@127.0.0.1:5432/postgres'`
- Apply schema (DDL lives in `migrations/`), e.g.:
  - `psql "$DATABASE_URL" -f migrations/001_create_airports.sql`
  - `psql "$DATABASE_URL" -f migrations/002_create_airlines.sql`
  - `psql "$DATABASE_URL" -f migrations/003_create_aircrafts.sql`
  - `psql "$DATABASE_URL" -f migrations/004_create_countries.sql`
  - `psql "$DATABASE_URL" -f migrations/005_create_flights.sql`
  - `psql "$DATABASE_URL" -f migrations/006_create_flights_commercial_view.sql`

### Commercial Flights View

We keep all raw data in `public.flights` and expose commercial-only flights via the view
`public.flights_commercial`.

- Initial creation: run `migrations/006_create_flights_commercial_view.sql` as above.
- Update the airline blocklist in `data/filtered_airlines.txt` (one ICAO per line), then refresh the view:
  - Ensure `DATABASE_URL` is set
  - Run: `python3 scripts/update_flights_commercial_view.py`
  - Verify (expect 0):
    - `SELECT COUNT(*) FROM public.flights_commercial WHERE UPPER(COALESCE(airline_icao,'')) IN ('NCA','PAC','FDX', ... );`

### Optional Proxy (Concurrent Fetch)

- Default behavior: no proxy, sequential fetching (airports → pages).
- When enabled with `--use-proxy`, the job:
  - Fetches a public HTTP proxy list (ip:port) from a maintained source.
  - Validates proxies in two stages: a generic HTTPS probe, then a small FlightRadar24 request.
  - Uses the surviving proxies for concurrent fetching; evicts failing proxies during the run.
  - Falls back to direct, sequential fetching if no survivors are available.

- CLI flags (see `scripts/run_job.py`):
  - `--use-proxy` — enable proxy validation and concurrent fetching (default: off)
  - `--proxy-fetch-limit` — cap initial proxies fetched (default: 300)
  - `--proxy-survivor-max` — cap validated proxies kept for rotation (default: 50)
  - `--proxy-stage1-url` — generic validation URL (default: `https://httpbin.org/ip`)
  - `--proxy-connect-timeout` — connect timeout seconds for validation (default: 2.0)
  - `--proxy-read-timeout` — read timeout seconds for validation (default: 4.0)
  - `--proxy-workers` — workers used during validation (default: 16)

- Concurrency: when proxies are enabled and survivors exist, the runner uses a thread pool sized to `min(survivors, 8)` and processes airport pages concurrently. Without proxies, the existing sequential flow is preserved.

- Example (enable proxies with a small sample):
  - `python3 scripts/run_job.py JP --use-proxy --proxy-fetch-limit 30 --proxy-survivor-max 10`

- Notes:
  - Only public API calls are proxied; database access and configuration are never sent through proxies.
  - The proxy list is volatile; counts vary by run. The job logs fetched/stage1/stage2 counts.

## Secrets & Remote Access

- Do not commit credentials. Keep `.env` untracked (already in `.gitignore`).
- Use SSH tunnels or cloud IAM tokens to avoid storing DB passwords on disk.
  - Example tunnel: `ssh -N -L 5433:127.0.0.1:5432 user@server` and set
    `DATABASE_URL=postgresql://app@127.0.0.1:5433/db?sslmode=require`.

## Developer Tips

- Absolute imports (`src.`) keep modules importable without packaging
- Code style: PEP 8; prefer type hints and Google-style docstrings
- Optional tools (install locally):
  - Format: `black src tests`
  - Lint: `ruff check src tests`

## Troubleshooting

- "DATABASE_URL must be defined": set `DATABASE_URL` or component variables (`HOST/USER/PASSWORD/DB`)
- API 4xx/5xx: rate limits can apply; try lowering `--limit` and adding retries
- No rows ingested: confirm airport list for your region in `data/` and DB connectivity

---

Happy flying!
