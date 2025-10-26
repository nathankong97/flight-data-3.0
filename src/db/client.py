"""
PostgreSQL client utilities backed by a connection pool.

The DatabaseClient centralizes how the application interacts with the database,
offering convenience helpers for acquiring connections, running queries, and
executing transactional work units.
"""

import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Iterable, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from src.logging_utils import perf

LOGGER = logging.getLogger(__name__)


class DatabaseClient:
    """Thin wrapper around a psycopg connection pool."""

    def __init__(
        self,
        dsn: str,
        *,
        min_size: int = 1,
        max_size: int = 5,
        connection_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        if min_size < 1 or max_size < 1 or min_size > max_size:
            raise ValueError("Pool size must be positive and min_size <= max_size.")

        self._dsn = dsn
        self._pool = ConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs=connection_config or {},
        )
        LOGGER.debug(
            "Initialized database client with pool size min=%s max=%s",
            min_size,
            max_size,
        )

    @contextmanager
    def connection(self) -> Generator[psycopg.Connection, None, None]:
        """Yield a pooled PostgreSQL connection."""
        with self._pool.connection() as conn:
            yield conn

    @contextmanager
    def transaction(self) -> Generator[psycopg.Connection, None, None]:
        """Yield a connection wrapped in a transaction block."""
        with self.connection() as conn:
            with conn.transaction():
                yield conn

    @perf("db.execute", tags={"component": "db"})
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Execute a write statement (INSERT/UPDATE/DELETE)."""
        with self.transaction() as conn:
            with conn.cursor() as cur:
                LOGGER.debug("Executing query: %s params=%s", query, params)
                cur.execute(query, params or {})

    @perf("db.executemany", tags={"component": "db"})
    def executemany(self, query: str, param_list: Iterable[Dict[str, Any]]) -> None:
        """Execute the same statement for multiple parameter sets within one transaction."""
        params = list(param_list)
        if not params:
            LOGGER.debug("No parameters supplied for batch statement: %s", query)
            return

        with self.transaction() as conn:
            with conn.cursor() as cur:
                LOGGER.debug(
                    "Executing batch statement (%s rows): %s",
                    len(params),
                    query,
                )
                cur.executemany(query, params)

    @perf("db.fetch_all", tags={"component": "db"})
    def fetch_all(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> list[Dict[str, Any]]:
        """Run a SELECT statement and return all rows as dictionaries."""
        with self.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                LOGGER.debug("Fetching rows with query: %s params=%s", query, params)
                cur.execute(query, params or {})
                return cur.fetchall()

    @perf("db.fetch_one", tags={"component": "db"})
    def fetch_one(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run a SELECT statement and return the first row or None."""
        with self.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                LOGGER.debug("Fetching single row: %s params=%s", query, params)
                cur.execute(query, params or {})
                return cur.fetchone()

    def run_in_transaction(self, func: Callable[[psycopg.Connection], Any]) -> Any:
        """Execute the given callable inside a managed transaction."""
        with self.transaction() as conn:
            LOGGER.debug("Running callable within transaction: %s", func)
            return func(conn)

    def close(self) -> None:
        """Close the underlying connection pool."""
        LOGGER.debug("Closing database client pool")
        self._pool.close()

    def __enter__(self) -> "DatabaseClient":
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self.close()
