"""Configuration utilities for flight-data ingestion workflows.

This module reads environment variables (optionally from an `.env` file) and
produces an application configuration object consumed across the project.

See `.env.example` for supported keys, including `DATABASE_URL` (or
`HOST`/`USER`/`PASSWORD`/`DB`/`PORT`), `LOG_DIR`, `LOG_LEVEL`, and optional
`APP_NAME`.

Usage example:

    from src.config import load_config

    config = load_config()
    client = DatabaseClient(config.database_url)
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, MutableMapping, Optional
from urllib.parse import quote_plus

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"


def _load_env_file(path: Path) -> Dict[str, str]:
    """Parse a dotenv-style file into a dictionary."""
    if not path.exists():
        return {}

    data: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data


def _build_database_url_from_components(
    values: Mapping[str, str], dotenv_values: Mapping[str, str]
) -> Optional[str]:
    """Construct a PostgreSQL DSN from discrete HOST/USER/PASSWORD/DB keys."""

    host = (
        values.get("DATABASE_HOST")
        or dotenv_values.get("DATABASE_HOST")
        or dotenv_values.get("HOST")
        or values.get("HOST")
    )
    user = (
        values.get("DATABASE_USER")
        or dotenv_values.get("DATABASE_USER")
        or dotenv_values.get("USER")
        or values.get("USER")
    )
    password = (
        values.get("DATABASE_PASSWORD")
        or dotenv_values.get("DATABASE_PASSWORD")
        or dotenv_values.get("PASSWORD")
        or values.get("PASSWORD")
    )
    database = (
        values.get("DATABASE_NAME")
        or dotenv_values.get("DATABASE_NAME")
        or dotenv_values.get("DB")
        or values.get("DB")
    )
    port = (
        values.get("DATABASE_PORT")
        or dotenv_values.get("DATABASE_PORT")
        or dotenv_values.get("DB_PORT")
        or values.get("DB_PORT")
        or dotenv_values.get("PORT")
        or values.get("PORT")
        or "5432"
    )

    if not all([host, user, password, database]):
        return None

    safe_user = quote_plus(user)
    safe_password = quote_plus(password)
    safe_host = host.strip()
    safe_database = database.strip()

    return f"postgresql://{safe_user}:{safe_password}@{safe_host}:{port}/{safe_database}"


@dataclass(frozen=True)
class AppConfig:
    """Application-level configuration values."""

    database_url: str
    log_directory: Path
    log_level: str
    app_name: str = "flight-data"


def _merge_envs(dotenv_values: Mapping[str, str], env: MutableMapping[str, str]) -> Dict[str, str]:
    """Merge dotenv values with the current environment, preferring os.environ."""
    merged = dict(dotenv_values)
    merged.update(env)  # os.environ wins
    return merged


def load_config(env_file: Optional[Path] = None) -> AppConfig:
    """Load configuration values using environment defaults."""
    target_file = env_file or DEFAULT_ENV_FILE
    dotenv_values = _load_env_file(target_file)
    merged = _merge_envs(dotenv_values, os.environ)

    database_url = merged.get("DATABASE_URL")
    if not database_url:
        database_url = _build_database_url_from_components(merged, dotenv_values)
        if not database_url:
            raise ValueError("DATABASE_URL (or HOST/USER/PASSWORD/DB combination) must be defined.")

    log_directory = Path(merged.get("LOG_DIR", REPO_ROOT / "logs"))
    if not log_directory.is_absolute():
        log_directory = REPO_ROOT / log_directory

    log_level = merged.get("LOG_LEVEL", "INFO").upper()

    return AppConfig(
        database_url=database_url,
        log_directory=log_directory,
        log_level=log_level,
        app_name=merged.get("APP_NAME", "flight-data"),
    )


__all__ = ["AppConfig", "load_config", "REPO_ROOT"]
