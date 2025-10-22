import pytest

import src.db.client as db_client
from src.db.client import DatabaseClient


@pytest.fixture
def db_client_with_fake_pool(fake_pool, fake_conn, monkeypatch):
    def pool_factory(conninfo, min_size, max_size, kwargs):
        assert conninfo == "postgresql://example"
        assert min_size == 1
        assert max_size == 2
        assert kwargs == {}
        return fake_pool

    monkeypatch.setattr(db_client, "ConnectionPool", pool_factory)
    client = DatabaseClient("postgresql://example", max_size=2)
    return client, fake_pool, fake_conn


def test_connection_uses_pool(db_client_with_fake_pool):
    client, fake_pool, fake_conn = db_client_with_fake_pool

    with client.connection() as conn:
        assert conn is fake_conn

    assert fake_pool.request_count == 1


def test_transaction_wraps_connection(db_client_with_fake_pool):
    client, _, fake_conn = db_client_with_fake_pool

    with client.transaction() as conn:
        assert conn is fake_conn
        assert fake_conn.last_transaction.entered

    assert fake_conn.last_transaction.exited


def test_execute_runs_statement(db_client_with_fake_pool):
    client, _, fake_conn = db_client_with_fake_pool

    client.execute("INSERT INTO t VALUES (%(id)s)", {"id": 10})

    cursor = fake_conn.cursors[-1]
    assert cursor.executed == [("execute", "INSERT INTO t VALUES (%(id)s)", {"id": 10})]


def test_executemany_processes_batch(db_client_with_fake_pool):
    client, _, fake_conn = db_client_with_fake_pool
    items = ({"id": i} for i in range(3))

    client.executemany("INSERT INTO t VALUES (%(id)s)", items)

    cursor = fake_conn.cursors[-1]
    op, query, params = cursor.executed[-1]
    assert op == "executemany"
    assert query == "INSERT INTO t VALUES (%(id)s)"
    assert params == [{"id": 0}, {"id": 1}, {"id": 2}]


def test_executemany_skip_empty_input(db_client_with_fake_pool, fake_conn):
    client, _, _ = db_client_with_fake_pool

    client.executemany("INSERT INTO t VALUES (%(id)s)", [])

    assert not fake_conn.transaction_calls


def test_fetch_all_returns_rows(db_client_with_fake_pool):
    client, _, _ = db_client_with_fake_pool

    rows = client.fetch_all("SELECT 1")

    assert rows == [{"value": 1}]


def test_fetch_one_returns_row(db_client_with_fake_pool):
    client, _, _ = db_client_with_fake_pool

    row = client.fetch_one("SELECT 1")

    assert row == {"value": 1}


def test_run_in_transaction_calls_callable(db_client_with_fake_pool, fake_conn):
    client, _, _ = db_client_with_fake_pool

    def _work(conn):
        assert conn is fake_conn
        return "done"

    result = client.run_in_transaction(_work)

    assert result == "done"
    assert fake_conn.last_transaction.exited


def test_close_shuts_pool(db_client_with_fake_pool):
    client, fake_pool, _ = db_client_with_fake_pool

    client.close()

    assert fake_pool.closed


def test_invalid_pool_sizes_raise():
    with pytest.raises(ValueError):
        DatabaseClient("postgresql://example", min_size=0)
    with pytest.raises(ValueError):
        DatabaseClient("postgresql://example", min_size=3, max_size=2)
