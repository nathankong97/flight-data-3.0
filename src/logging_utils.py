"""Centralized logging utilities for flight-data ingestion runs."""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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


__all__ = ["configure_logging", "generate_run_id", "DEFAULT_LOG_FORMAT"]
