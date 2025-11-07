import uuid

import pytest


@pytest.mark.integration
def test_db_client_round_trip(db_client):
    table_name = f"flights_int_{uuid.uuid4().hex[:8]}"
    create_sql = f"""
        CREATE TABLE {table_name} (
            id SERIAL PRIMARY KEY,
            flight_num TEXT NOT NULL,
            status_detail TEXT
        );
    """

    db_client.execute(create_sql)

    try:
        rows = [
            {"flight_num": "NH101", "status_detail": "scheduled"},
            {"flight_num": "UA202", "status_detail": "boarding"},
        ]
        db_client.executemany(
            f"INSERT INTO {table_name} (flight_num, status_detail) VALUES (%(flight_num)s, %(status_detail)s)",
            rows,
        )

        result = db_client.fetch_all(f"SELECT flight_num, status_detail FROM {table_name} ORDER BY flight_num")
        assert result == [
            {"flight_num": "NH101", "status_detail": "scheduled"},
            {"flight_num": "UA202", "status_detail": "boarding"},
        ]

        solitary = db_client.fetch_one(
            f"SELECT flight_num FROM {table_name} WHERE flight_num = %(flight_num)s",
            {"flight_num": "NH101"},
        )
        assert solitary == {"flight_num": "NH101"}
    finally:
        db_client.execute(f"DROP TABLE IF EXISTS {table_name};")
