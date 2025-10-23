import uuid

import pytest

from src.api.flightradar import FlightRadarClient
from src.jobs.runner import RunConfig, run_job


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS flights (
    flight_id BIGINT PRIMARY KEY,
    ingest_run_id UUID NOT NULL,
    flight_num TEXT NOT NULL,
    status_detail TEXT,
    aircraft_code TEXT,
    aircraft_text TEXT,
    aircraft_reg TEXT,
    aircraft_co2 NUMERIC(12,2),
    aircraft_restricted BOOLEAN,
    owner_name TEXT,
    owner_iata TEXT,
    owner_icao TEXT,
    airline TEXT,
    airline_iata TEXT,
    airline_icao TEXT,
    origin_iata TEXT,
    origin_offset SMALLINT,
    origin_offset_abbr TEXT,
    origin_offset_dst BOOLEAN,
    origin_terminal TEXT,
    origin_gate TEXT,
    dest_iata TEXT,
    dest_icao TEXT,
    dest_offset SMALLINT,
    dest_offset_abbr TEXT,
    dest_offset_dst BOOLEAN,
    dest_terminal TEXT,
    dest_gate TEXT,
    sched_dep BIGINT,
    sched_arr BIGINT,
    real_dep BIGINT,
    real_arr BIGINT,
    origin_lat DOUBLE PRECISION,
    origin_lng DOUBLE PRECISION,
    dest_lat DOUBLE PRECISION,
    dest_lng DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Primary key ensures uniqueness on upstream flight id
"""


@pytest.mark.integration
def test_run_job_full_flow(monkeypatch, app_config, db_client):
    db_client.execute(CREATE_TABLE_SQL)

    airports = ["NRT", "BUF"]
    monkeypatch.setattr("src.jobs.runner.load_airport_codes", lambda region: airports)
    monkeypatch.setattr("src.jobs.runner.page_for_index", lambda region, idx: -1)

    client = FlightRadarClient(timeout=15)
    run_config = RunConfig(
        region="test",
        limit_per_page=10,
        page_delay_seconds=0,
        airport_delay_seconds=0,
    )

    try:
        try:
            ingest_run_id = run_job(app_config, db_client, client, run_config)
            result = db_client.fetch_one(
                "SELECT COUNT(*) AS cnt FROM flights WHERE ingest_run_id = %(run)s",
                {"run": uuid.UUID(ingest_run_id)},
            )
            assert result["cnt"] > 0
        finally:
            db_client.execute("DROP TABLE flights")
    finally:
        client.close()
