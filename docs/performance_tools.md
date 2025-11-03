# Performance & Logging Utilities (src/logging_utils.py)

This guide shows how to configure logging and use the performance helpers
provided by `src/logging_utils.py`: `configure_logging`, `generate_run_id`,
`perf` (decorator), and `perf_span` (context manager).

## Configure logging

`configure_logging` sets up a per-run file under `LOG_DIR` and (by default) a
console handler. It also injects a stable `run_id` into every log record.

```python
from src.config import load_config
from src.logging_utils import configure_logging

config = load_config()  # reads .env / environment
log_path = configure_logging(config, run_id="my-run-001")
print(f"logs to: {log_path}")
```

- File name pattern: `<APP_NAME>-<run_id>.log`, created under `LOG_DIR`.
- Default format: `%(asctime)s %(levelname)s %(name)s [run=%(run_id)s] %(message)s`.
- `run_id` in the file name is sanitized for filesystem safety, while the
  `run_id` inside log records preserves the original value.
- Source: see `src/logging_utils.py` (`DEFAULT_LOG_FORMAT`, `_RunContextFilter`).

Environment keys used via `load_config()` (see `.env.example`):
- `LOG_DIR` (default: `logs`)
- `LOG_LEVEL` (default: `INFO`)
- `APP_NAME` (default: `flight-data`)

## Measure function execution with perf

Decorate any function to automatically log a single `event=perf` line with
its duration and success/failure.

```python
from src.logging_utils import perf

@perf("api.fetch_departures", tags={"component": "api"})
def fetch(...):
    ...
```

What gets logged (on return):
- `event=perf name=<span_name> duration_ms=<float>`
- `success=true`
- `tags={k='v', ...}` when provided

On exceptions, `success=false` is logged and the exception is re-raised.

This works for both synchronous and `async def` functions. The decorator
selects the correct wrapper at runtime.

Examples in this repo using `perf`:
- `src/api/flightradar.py`: `fetch_departures`
- `src/db/client.py`: `executemany`
- `src/jobs/runner.py`: `run_job`
- `src/reference/coordinates.py`: `load_coordinates`
- `src/transform/flights.py`: `extract_departure_records`

See also tests for expected log content:
- `tests/test_logging_utils.py`

## Measure code blocks with perf_span

Use `perf_span` as a context manager to time arbitrary code blocks.

```python
from src.logging_utils import perf_span

with perf_span("jobs.airport_loop", tags={"airport": "HND", "index": 0}):
    # work to be timed
    ...
```

- Logs the same single-line structure as `perf` with `event=perf` and
  `duration_ms`, including a `success=false` entry if an exception is raised
  inside the block (the exception is not suppressed).
- Callers may supply a custom logger and level via the constructor; defaults
  match `logging.getLogger(__name__)` and `logging.INFO`.

Examples in this repo using `perf_span`:
- `src/jobs/runner.py`: page and airport loops
- `scripts/run_job.py`: total job span around `run_job`

## Putting it together

```python
from src.config import load_config
from src.logging_utils import configure_logging, perf, perf_span

config = load_config()
configure_logging(config)  # enables file + console logging

@perf("compute.something", tags={"k": "v"})
def compute(x: int) -> int:
    return x + 1

with perf_span("batch.process", tags={"size": 10}):
    out = compute(41)
    assert out == 42
```

The result is a per-run log file (under `LOG_DIR`) containing lines like:

```
event=perf name=compute.something duration_ms=... success=true tags={k='v'}
event=perf name=batch.process duration_ms=... success=true tags={size='10'}
```

Implementation details and defaults are in `src/logging_utils.py`.
