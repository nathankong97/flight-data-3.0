"""Shared pytest fixtures for the flight_data package tests.

Provides reusable fakes and configuration objects to keep tests
deterministic and isolated, following AGENTS.md guidance.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest

from src.config import AppConfig


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    """Application config fixture.

    Points logging to a temporary directory and uses a local test
    database URL. Avoids touching real user config or network.
    """
    return AppConfig(
        database_url="postgresql://user:pass@localhost:5432/db",
        log_directory=tmp_path,
        log_level="INFO",
    )


class FakeCursor:
    def __init__(self) -> None:
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append(("execute", query, params))

    def executemany(self, query, params_seq):
        self.executed.append(("executemany", query, list(params_seq)))

    def fetchall(self):
        return [{"value": 1}]

    def fetchone(self):
        return {"value": 1}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeTransaction:
    def __init__(self, conn):
        self.conn = conn
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        self.exited = True
        return False


class FakeConnection:
    def __init__(self):
        self.cursors = []
        self.transaction_calls = []
        self.last_transaction = None

    def cursor(self, *_, **__):
        cursor = FakeCursor()
        self.cursors.append(cursor)
        return cursor

    def transaction(self):
        txn = FakeTransaction(self)
        self.last_transaction = txn
        self.transaction_calls.append(txn)
        return txn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, conn):
        self.conn = conn
        self.request_count = 0
        self.closed = False

    @contextmanager
    def connection(self):
        self.request_count += 1
        yield self.conn

    def close(self):
        self.closed = True


@pytest.fixture
def fake_conn() -> FakeConnection:
    """In-memory fake DB connection used by db client tests."""
    return FakeConnection()


@pytest.fixture
def fake_pool(fake_conn: FakeConnection) -> Generator[FakePool, None, None]:
    """In-memory fake connection pool wrapping ``fake_conn``."""
    pool = FakePool(fake_conn)
    yield pool


@pytest.fixture
def airlines_sample_path() -> Path:
    """Absolute path to the sample filtered airlines list.

    Resolves relative to this tests/ directory to be robust to
    the current working directory used to invoke pytest.
    """
    return Path(__file__).resolve().parent / "fixtures" / "filtered_airlines_sample.txt"
