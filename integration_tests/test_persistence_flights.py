import uuid
from dataclasses import replace

import pytest

from src.persistence import upsert_flights
from src.transform import FlightRecord


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS flights (
    id BIGSERIAL PRIMARY KEY,
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

CREATE UNIQUE INDEX IF NOT EXISTS uq_flights_conflict
    ON flights (ingest_run_id, flight_num, sched_dep, dest_iata);
"""


@pytest.mark.integration
def test_upsert_flights_updates_existing(db_client):
    db_client.execute(CREATE_TABLE_SQL)
    ingest_run_id = str(uuid.uuid4())

    record = FlightRecord(
        flight_num="NH123",
        status_detail="Scheduled",
        aircraft_code="789",
        aircraft_text="Boeing 787-9",
        aircraft_reg="JA123A",
        aircraft_co2=120.5,
        aircraft_restricted=False,
        owner_name="ANA",
        owner_iata="NH",
        owner_icao="ANA",
        airline="All Nippon Airways",
        airline_iata="NH",
        airline_icao="ANA",
        origin_iata="HND",
        origin_offset=9,
        origin_offset_abbr="JST",
        origin_offset_dst=False,
        origin_terminal="2",
        origin_gate="54",
        dest_iata="SFO",
        dest_icao="KSFO",
        dest_offset=-7,
        dest_offset_abbr="PDT",
        dest_offset_dst=True,
        dest_terminal="I",
        dest_gate="15",
        sched_dep=1718653200,
        sched_arr=1718689200,
        real_dep=1718655000,
        real_arr=1718690400,
        origin_lat=35.5494,
        origin_lng=139.7798,
        dest_lat=37.6213,
        dest_lng=-122.379,
    )

    upsert_flights(db_client, ingest_run_id, [record])

    inserted = db_client.fetch_one(
        "SELECT status_detail FROM flights WHERE flight_num = %(flight_num)s",
        {"flight_num": "NH123"},
    )
    assert inserted["status_detail"] == "Scheduled"

    updated_record = replace(record, status_detail="Departed")

    upsert_flights(db_client, ingest_run_id, [updated_record])

    after = db_client.fetch_one(
        "SELECT status_detail FROM flights WHERE flight_num = %(flight_num)s",
        {"flight_num": "NH123"},
    )
    assert after["status_detail"] == "Departed"

    db_client.execute("DROP TABLE flights")
