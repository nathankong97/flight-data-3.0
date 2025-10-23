# Flight Data Ingestion ✈️

Ingest scheduled flight departures from FlightRadar24, transform them into structured records, and
persist to PostgreSQL. The repo includes a small job runner, a typed transform layer, and a thin DB
client backed by psycopg v3.

- Runtime code lives under `src/`
- Tests live under `tests/` and `integration_tests/`
- Airport lists live under `data/airport_<REGION>.txt` (order matters for pagination)

See `AGENTS.md` for project conventions and contributor guidelines.

## Quickstart 🔧

1) Create a virtual environment and install deps

- Bash
  - `python -m venv .venv && source .venv/bin/activate`
  - `python -m pip install -r requirements.txt`
- PowerShell
  - `python -m venv .venv; .\\.venv\\Scripts\\Activate.ps1`
  - `python -m pip install -r requirements.txt`

2) Configure environment

- Preferred: set a full DSN in `DATABASE_URL`, e.g.
  - Bash: `export DATABASE_URL='postgresql://user:pass@host:5432/db'`
  - PowerShell: `$env:DATABASE_URL = 'postgresql://user:pass@host:5432/db'`
- Or provide components in a `.env` (git‑ignored):
  - `HOST=localhost`, `USER=app`, `PASSWORD=secret`, `DB=flights`, `PORT=5432`
- Optional logging overrides:
  - `LOG_DIR=logs` and `LOG_LEVEL=INFO` (default: INFO)

3) Run the job

- Example (fetch JP airports, one page per airport):
  - `python scripts/run_job.py JP --max-pages 1 --limit 100`

Logs are written per run to `logs/<app>-<run_id>.log` (see `src/logging_utils.py`).

## Project Layout

- `src/api/` — HTTP clients (FlightRadar24)
- `src/transform/` — parse + normalize API payloads into `FlightRecord`
- `src/persistence/` — upsert helpers for `flights` fact table (keyed by upstream `flight_id`)
- `src/db/` — psycopg v3 pool wrapper
- `src/jobs/` — orchestration (fetch → transform → persist)
- `src/reference/` — coordinate lookup from DB
- `src/pagination.py` — index→page mapping per region
- `data/airport_<REGION>.txt` — ordered airport lists used by pagination
- `migrations/` — PostgreSQL DDL for reference + fact tables
- `scripts/run_job.py` — CLI entrypoint

## Testing 🧪

- Run unit tests: `pytest -q`
- Skip integration tests: `pytest -q -m "not integration"`
- Run only integration tests: `pytest -q -m integration`

Integration tests require a reachable PostgreSQL and (for API tests) outbound network access.

## Database (PostgreSQL) 🐘

- Start a local Postgres via Docker:
  - `docker run --name flight-db -e POSTGRES_PASSWORD=dev -p 5432:5432 -d postgres:15`
- Set `DATABASE_URL`, for example:
  - Bash: `export DATABASE_URL='postgresql://postgres:dev@127.0.0.1:5432/postgres'`
  - PowerShell: `$env:DATABASE_URL = 'postgresql://postgres:dev@127.0.0.1:5432/postgres'`
- Apply schema (DDL lives in `migrations/`), e.g.:
  - `psql "$DATABASE_URL" -f migrations/001_create_airports.sql`
  - `psql "$DATABASE_URL" -f migrations/005_create_flights.sql`

## Secrets & Remote Access 🔒

- Do not commit credentials. Keep `.env` untracked (already in `.gitignore`).
- Use SSH tunnels or cloud IAM tokens to avoid storing DB passwords on disk.
  - Example tunnel: `ssh -N -L 5433:127.0.0.1:5432 user@server` and set
    `DATABASE_URL=postgresql://app@127.0.0.1:5433/db?sslmode=require`.

## Developer Tips

- Absolute imports (`src.`) keep modules importable without packaging
- Code style: PEP 8; prefer type hints and Google‑style docstrings
- Optional tools (install locally):
  - Format: `black src tests`
  - Lint: `ruff check src tests`

## Troubleshooting

- "DATABASE_URL must be defined": set `DATABASE_URL` or component variables (`HOST/USER/PASSWORD/DB`)
- API 4xx/5xx: rate limits can apply; try lowering `--limit` and adding retries
- No rows ingested: confirm airport list for your region in `data/` and DB connectivity

---

Happy flying! ✨
