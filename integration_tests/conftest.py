"""Fixtures for integration tests that hit a real PostgreSQL instance."""

import uuid
from typing import Generator

import pytest

from src.db.client import DatabaseClient
from src.config import load_config, AppConfig
from psycopg import errors


@pytest.fixture(scope="session")
def app_config() -> AppConfig:
    try:
        return load_config()
    except ValueError:
        pytest.skip("DATABASE_URL must be configured in .env to run integration tests.")


@pytest.fixture(scope="session")
def integration_schema() -> str:
    return f"int_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session", autouse=True)
def ensure_schema(app_config: AppConfig, integration_schema: str) -> Generator[None, None, None]:
    try:
        with DatabaseClient(app_config.database_url, min_size=1, max_size=1).connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {integration_schema};")
    except errors.InsufficientPrivilege:
        pytest.skip("Database user lacks privileges to create schemas for integration tests.")
    yield
    with DatabaseClient(app_config.database_url, min_size=1, max_size=1).connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA IF EXISTS {integration_schema} CASCADE;")


@pytest.fixture(scope="session")
def db_client(app_config: AppConfig, integration_schema: str) -> Generator[DatabaseClient, None, None]:
    client = DatabaseClient(
        app_config.database_url,
        min_size=1,
        max_size=2,
        connection_config={"options": f"-c search_path={integration_schema},public"},
    )
    yield client
    client.close()
