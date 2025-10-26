"""Centralized logging utilities for flight-data ingestion runs.

This module also provides lightweight performance monitoring helpers:

- ``perf``: a decorator to time sync/async functions and log one structured line
  at INFO level with the duration and success state.
- ``perf_span``: a context manager to time arbitrary code blocks and log the
  same structured line.

Both helpers write to the existing logger hierarchy configured by
``configure_logging`` so timings appear in the per-run log file under ``logs/``.
"""

import logging
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

from src.config import AppConfig

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s [run=%(run_id)s] %(message)s"


class _RunContextFilter(logging.Filter):
    """Inject the current run identifier into every log record."""

    def __init__(self, run_id: str) -> None:
        super().__init__()
        self._run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self._run_id
        return True


def _sanitize_run_id(run_id: str) -> str:
    """Convert a run identifier into a filesystem-friendly token."""
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in run_id)


def generate_run_id() -> str:
    """Return a default run identifier based on the current UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def configure_logging(
    config: AppConfig,
    run_id: Optional[str] = None,
    include_console: bool = True,
    fmt: str = DEFAULT_LOG_FORMAT,
) -> Path:
    """Configure root logging handlers for the current run."""
    resolved_run_id = run_id or generate_run_id()
    safe_run_id = _sanitize_run_id(resolved_run_id)

    log_dir = config.log_directory
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{config.app_name}-{safe_run_id}.log"

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handlers = [logging.FileHandler(log_path, encoding="utf-8")]
    if include_console:
        handlers.append(logging.StreamHandler(sys.stdout))

    for handler in handlers:
        handler.setFormatter(logging.Formatter(fmt))
        handler.addFilter(_RunContextFilter(resolved_run_id))
        root_logger.addHandler(handler)

    level = getattr(logging, config.log_level.upper(), logging.INFO)
    root_logger.setLevel(level)

    return log_path


def _format_tags(tags: Optional[Mapping[str, Any]]) -> str:
    """Return a compact string representation for tags.

    Keeps logging simple while remaining readable in a single line.
    """
    if not tags:
        return "{}"
    # Convert to a stable, minimal representation
    items = ", ".join(f"{k}={tags[k]!r}" for k in sorted(tags))
    return "{" + items + "}"


def perf(
    name: Optional[str] = None,
    *,
    tags: Optional[Mapping[str, Any]] = None,
    level: int = logging.INFO,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that logs execution time of a function.

    Args:
        name: Optional span name; defaults to ``<module>.<func>``.
        tags: Optional mapping of additional metadata to include in the log.
        level: Logging level to use (defaults to ``logging.INFO``).

    Returns:
        A callable that wraps the target function, logging a structured
        ``event=perf`` line with duration in milliseconds and success flag.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        span_name = name or f"{func.__module__}.{func.__qualname__}"
        logger = logging.getLogger(func.__module__)

        def _log(duration_ms: float, success: bool) -> None:
            logger.log(
                level,
                "event=perf name=%s duration_ms=%.3f success=%s tags=%s",
                span_name,
                duration_ms,
                str(success).lower(),
                _format_tags(tags),
            )

        try:
            import asyncio  # local import to avoid overhead if unused

            is_coro = asyncio.iscoroutinefunction(func)
        except Exception:
            is_coro = False

        if is_coro:
            import functools
            import asyncio

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_ns = time.monotonic_ns()
                try:
                    result = await func(*args, **kwargs)
                except Exception:
                    end_ns = time.monotonic_ns()
                    _log((end_ns - start_ns) / 1_000_000.0, False)
                    raise
                end_ns = time.monotonic_ns()
                _log((end_ns - start_ns) / 1_000_000.0, True)
                return result

            return async_wrapper

        import functools

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_ns = time.monotonic_ns()
            try:
                result = func(*args, **kwargs)
            except Exception:
                end_ns = time.monotonic_ns()
                _log((end_ns - start_ns) / 1_000_000.0, False)
                raise
            end_ns = time.monotonic_ns()
            _log((end_ns - start_ns) / 1_000_000.0, True)
            return result

        return sync_wrapper

    return decorator


class perf_span:
    """Context manager to time an arbitrary code block and log its duration.

    Example:
        with perf_span("upsert_batch", tags={"airport": "NRT"}):
            upsert_flights(...)
    """

    def __init__(
        self,
        name: str,
        *,
        tags: Optional[Mapping[str, Any]] = None,
        level: int = logging.INFO,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._name = name
        self._tags = tags or {}
        self._level = level
        self._logger = logger or logging.getLogger(__name__)
        self._start_ns: Optional[int] = None

    def __enter__(self) -> "perf_span":
        self._start_ns = time.monotonic_ns()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        end_ns = time.monotonic_ns()
        start_ns = self._start_ns or end_ns
        duration_ms = (end_ns - start_ns) / 1_000_000.0
        success = exc_type is None
        self._logger.log(
            self._level,
            "event=perf name=%s duration_ms=%.3f success=%s tags=%s",
            self._name,
            duration_ms,
            str(success).lower(),
            _format_tags(self._tags),
        )
        # Do not suppress exceptions
        return False


__all__ = [
    "configure_logging",
    "generate_run_id",
    "DEFAULT_LOG_FORMAT",
    "perf",
    "perf_span",
]
