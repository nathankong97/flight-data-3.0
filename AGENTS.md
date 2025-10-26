# Repository Guidelines

## Project Structure & Module Organization
- Place all runtime code under `src/`, organizing modules and subpackages as needed (e.g., `src/ingest/loader.py`, `src/utils.py`) so related logic stays co-located.
- Keep tests in `tests/`, mirroring source filenames (`tests/test_flight_data.py`) to highlight missing coverage quickly.
- Store lightweight sample datasets in `data/sample/`; large raw feeds remain outside version control per `.gitignore`.
- Configuration artifacts (e.g., `.env.example`, `pyproject.toml`, `config/database.toml`) live at the repository root for easy discovery.
- Airport lists in `data/airport_<region>.txt` are ordered by priority; pagination logic (`src/pagination.py`) depends on their position, so maintain the intended sequence when editing.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` — create and enter an isolated virtual environment. Always activate the venv before running any project commands (`pytest`, scripts, formatters).
- `python -m pip install -r requirements.txt` — install runtime and tooling dependencies; keep pins current.
- `black src tests` — auto-format files before committing to ensure consistent whitespace and wrapping.
- `ruff check src tests` — run static analysis; add `--fix` when safe to apply autofixes locally.
- `pytest -q` — execute the test suite; use `pytest --cov=src --cov-report=term-missing` for coverage validation.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation, 100-character line limits, and explicit imports (`from src.config import load_config`).
- Use snake_case for functions and variables, PascalCase for classes, and lowercase module names with underscores.
- Document public functions with Google-style docstrings describing arguments, return values, and side effects.
- Provide precise type hints for all function signatures and public attributes to improve readability and tooling.
- Prefer absolute imports rooted at `src.` (e.g., `import src.logging_utils`) so modules remain discoverable without relying on package installation.
- Avoid `from __future__ import ...`; target the current runtime’s language features directly.

## Testing Guidelines
- Add pytest unit tests alongside features, naming files `test_<module>.py` and functions `test_<behavior>()`.
- Target ≥85% statement coverage, prioritizing parsing, validation, and scheduling logic.
- Use pytest for all unit and integration cases; avoid stacking mocks on top of mocks, and only patch external dependencies when absolutely necessary.
- Before adding a test, consider whether a fixture is required and prefer reusing existing fixtures from `tests/conftest.py`.
- Centralize reusable fixtures in `tests/conftest.py` and keep deterministic sample payloads under `tests/fixtures/`.

## Commit & Pull Request Guidelines
- Write imperative Conventional Commits (`feat: add runway delay transformer`) and keep scopes narrow.
- Reference issue IDs in the subject or footer (`Refs #42`) and call out breaking changes explicitly.
- PRs must include a concise summary, test evidence (`pytest`, `ruff`/`black`), and notes on data or API impacts.
- Request review from the appropriate module owner and wait for green CI before merging.

## Logging & Diagnostics
- Each application run writes structured output to a dedicated file under `logs/` (e.g., `logs/flight-data-20240214T1530.log`), providing one artifact per execution.
- Exclude the log directory from commits (covered by `.gitignore`) and attach relevant excerpts to PRs when discussing failures.
- Use the shared helper in `src/logging_utils.py` (add if missing) to standardize formatting, timestamps, and file naming.

## Database & Persistence
- PostgreSQL (15+) is the authoritative datastore for structured flight records; local development can use `docker run --name flight-db -e POSTGRES_PASSWORD=dev -p 5432:5432 -d postgres:15`.
- Manage schema migrations with your preferred tool (e.g., Alembic) and keep migration scripts under `migrations/`.
- Store connection details in `.env` (ignored in git) with documented defaults in `.env.example`.

## Data Security & Configuration
- Never commit credentials, raw passenger datasets, or personal tokens; rely on environment variables and secret managers.
- Mask or anonymize any shared data samples and document the masking approach alongside the code that consumes them.
- Review `.gitignore` before adding new directories to ensure generated artifacts (logs, caches, virtual envs) stay untracked.
