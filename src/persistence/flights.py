"""Database persistence helpers for flight records."""

from typing import Iterable, List

from src.db import DatabaseClient
from src.transform import FlightRecord
from src.logging_utils import perf


# Upsert when the schema includes `flight_id` primary key (preferred)
UPSERT_SQL_WITH_ID = """
    INSERT INTO flights (
        flight_id,
        ingest_run_id,
        flight_num,
        status_detail,
        aircraft_code,
        aircraft_text,
        aircraft_reg,
        aircraft_co2,
        aircraft_restricted,
        owner_name,
        owner_iata,
        owner_icao,
        airline,
        airline_iata,
        airline_icao,
        origin_iata,
        origin_offset,
        origin_offset_abbr,
        origin_offset_dst,
        origin_terminal,
        origin_gate,
        dest_iata,
        dest_icao,
        dest_offset,
        dest_offset_abbr,
        dest_offset_dst,
        dest_terminal,
        dest_gate,
        sched_dep,
        sched_arr,
        real_dep,
        real_arr,
        origin_lat,
        origin_lng,
        dest_lat,
        dest_lng
    )
    VALUES (
        %(flight_id)s,
        %(ingest_run_id)s,
        %(flight_num)s,
        %(status_detail)s,
        %(aircraft_code)s,
        %(aircraft_text)s,
        %(aircraft_reg)s,
        %(aircraft_co2)s,
        %(aircraft_restricted)s,
        %(owner_name)s,
        %(owner_iata)s,
        %(owner_icao)s,
        %(airline)s,
        %(airline_iata)s,
        %(airline_icao)s,
        %(origin_iata)s,
        %(origin_offset)s,
        %(origin_offset_abbr)s,
        %(origin_offset_dst)s,
        %(origin_terminal)s,
        %(origin_gate)s,
        %(dest_iata)s,
        %(dest_icao)s,
        %(dest_offset)s,
        %(dest_offset_abbr)s,
        %(dest_offset_dst)s,
        %(dest_terminal)s,
        %(dest_gate)s,
        %(sched_dep)s,
        %(sched_arr)s,
        %(real_dep)s,
        %(real_arr)s,
        %(origin_lat)s,
        %(origin_lng)s,
        %(dest_lat)s,
        %(dest_lng)s
    )
    ON CONFLICT (flight_id)
    DO UPDATE SET
        status_detail = EXCLUDED.status_detail,
        aircraft_code = EXCLUDED.aircraft_code,
        aircraft_text = EXCLUDED.aircraft_text,
        aircraft_reg = EXCLUDED.aircraft_reg,
        aircraft_co2 = EXCLUDED.aircraft_co2,
        aircraft_restricted = EXCLUDED.aircraft_restricted,
        owner_name = EXCLUDED.owner_name,
        owner_iata = EXCLUDED.owner_iata,
        owner_icao = EXCLUDED.owner_icao,
        airline = EXCLUDED.airline,
        airline_iata = EXCLUDED.airline_iata,
        airline_icao = EXCLUDED.airline_icao,
        origin_iata = EXCLUDED.origin_iata,
        origin_offset = EXCLUDED.origin_offset,
        origin_offset_abbr = EXCLUDED.origin_offset_abbr,
        origin_offset_dst = EXCLUDED.origin_offset_dst,
        origin_terminal = EXCLUDED.origin_terminal,
        origin_gate = EXCLUDED.origin_gate,
        dest_iata = EXCLUDED.dest_iata,
        dest_icao = EXCLUDED.dest_icao,
        dest_offset = EXCLUDED.dest_offset,
        dest_offset_abbr = EXCLUDED.dest_offset_abbr,
        dest_offset_dst = EXCLUDED.dest_offset_dst,
        dest_terminal = EXCLUDED.dest_terminal,
        dest_gate = EXCLUDED.dest_gate,
        sched_dep = EXCLUDED.sched_dep,
        sched_arr = EXCLUDED.sched_arr,
        real_dep = EXCLUDED.real_dep,
        real_arr = EXCLUDED.real_arr,
        origin_lat = EXCLUDED.origin_lat,
        origin_lng = EXCLUDED.origin_lng,
        dest_lat = EXCLUDED.dest_lat,
        dest_lng = EXCLUDED.dest_lng
"""

# Legacy upsert for deployments without `flight_id` column yet
UPSERT_SQL_LEGACY = """
    INSERT INTO flights (
        ingest_run_id,
        flight_num,
        status_detail,
        aircraft_code,
        aircraft_text,
        aircraft_reg,
        aircraft_co2,
        aircraft_restricted,
        owner_name,
        owner_iata,
        owner_icao,
        airline,
        airline_iata,
        airline_icao,
        origin_iata,
        origin_offset,
        origin_offset_abbr,
        origin_offset_dst,
        origin_terminal,
        origin_gate,
        dest_iata,
        dest_icao,
        dest_offset,
        dest_offset_abbr,
        dest_offset_dst,
        dest_terminal,
        dest_gate,
        sched_dep,
        sched_arr,
        real_dep,
        real_arr,
        origin_lat,
        origin_lng,
        dest_lat,
        dest_lng
    )
    VALUES (
        %(ingest_run_id)s,
        %(flight_num)s,
        %(status_detail)s,
        %(aircraft_code)s,
        %(aircraft_text)s,
        %(aircraft_reg)s,
        %(aircraft_co2)s,
        %(aircraft_restricted)s,
        %(owner_name)s,
        %(owner_iata)s,
        %(owner_icao)s,
        %(airline)s,
        %(airline_iata)s,
        %(airline_icao)s,
        %(origin_iata)s,
        %(origin_offset)s,
        %(origin_offset_abbr)s,
        %(origin_offset_dst)s,
        %(origin_terminal)s,
        %(origin_gate)s,
        %(dest_iata)s,
        %(dest_icao)s,
        %(dest_offset)s,
        %(dest_offset_abbr)s,
        %(dest_offset_dst)s,
        %(dest_terminal)s,
        %(dest_gate)s,
        %(sched_dep)s,
        %(sched_arr)s,
        %(real_dep)s,
        %(real_arr)s,
        %(origin_lat)s,
        %(origin_lng)s,
        %(dest_lat)s,
        %(dest_lng)s
    )
    ON CONFLICT (ingest_run_id, flight_num, sched_dep, dest_iata)
    DO UPDATE SET
        status_detail = EXCLUDED.status_detail,
        aircraft_code = EXCLUDED.aircraft_code,
        aircraft_text = EXCLUDED.aircraft_text,
        aircraft_reg = EXCLUDED.aircraft_reg,
        aircraft_co2 = EXCLUDED.aircraft_co2,
        aircraft_restricted = EXCLUDED.aircraft_restricted,
        owner_name = EXCLUDED.owner_name,
        owner_iata = EXCLUDED.owner_iata,
        owner_icao = EXCLUDED.owner_icao,
        airline = EXCLUDED.airline,
        airline_iata = EXCLUDED.airline_iata,
        airline_icao = EXCLUDED.airline_icao,
        origin_iata = EXCLUDED.origin_iata,
        origin_offset = EXCLUDED.origin_offset,
        origin_offset_abbr = EXCLUDED.origin_offset_abbr,
        origin_offset_dst = EXCLUDED.origin_offset_dst,
        origin_terminal = EXCLUDED.origin_terminal,
        origin_gate = EXCLUDED.origin_gate,
        dest_iata = EXCLUDED.dest_iata,
        dest_icao = EXCLUDED.dest_icao,
        dest_offset = EXCLUDED.dest_offset,
        dest_offset_abbr = EXCLUDED.dest_offset_abbr,
        dest_offset_dst = EXCLUDED.dest_offset_dst,
        dest_terminal = EXCLUDED.dest_terminal,
        dest_gate = EXCLUDED.dest_gate,
        sched_dep = EXCLUDED.sched_dep,
        sched_arr = EXCLUDED.sched_arr,
        real_dep = EXCLUDED.real_dep,
        real_arr = EXCLUDED.real_arr,
        origin_lat = EXCLUDED.origin_lat,
        origin_lng = EXCLUDED.origin_lng,
        dest_lat = EXCLUDED.dest_lat,
        dest_lng = EXCLUDED.dest_lng
"""


def _schema_has_flight_id(db_client: DatabaseClient) -> bool:
    """Return True if the schema expects inserts keyed by flight_id.

    This is true when:
    - The column exists AND
      - it is part of a PRIMARY KEY or UNIQUE constraint, or
      - it is marked NOT NULL (indicating legacy path would fail).

    Falls back to False only when the column is absent.
    """
    try:
        row = db_client.fetch_one(
            """
            SELECT
              -- Column exists
              EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'flights' AND column_name = 'flight_id'
              ) AS has_col,
              -- Column is NOT NULL
              EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'flights' AND column_name = 'flight_id' AND is_nullable = 'NO'
              ) AS not_null,
              -- Column participates in a PK
              EXISTS (
                SELECT 1
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = 'flights'
                  AND kcu.column_name = 'flight_id'
                  AND tc.constraint_type = 'PRIMARY KEY'
              ) AS is_pk,
              -- Column has a UNIQUE constraint
              EXISTS (
                SELECT 1
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = 'flights'
                  AND kcu.column_name = 'flight_id'
                  AND tc.constraint_type = 'UNIQUE'
              ) AS is_unique
            """
        ) or {}

        has_col = bool(row.get("has_col"))
        if not has_col:
            return False

        # Prefer explicit constraints; otherwise treat NOT NULL as requiring flight_id
        is_pk = bool(row.get("is_pk"))
        is_unique = bool(row.get("is_unique"))
        not_null = bool(row.get("not_null"))
        return is_pk or is_unique or not_null
    except Exception:
        # Be conservative: if detection fails, assume flight_id is required
        return True


@perf("db.upsert_flights", tags={"component": "db"})
def upsert_flights(
    db_client: DatabaseClient,
    ingest_run_id: str,
    records: Iterable[FlightRecord],
) -> int:
    """Persist flight records, updating existing rows on conflict."""

    use_flight_id = _schema_has_flight_id(db_client)
    if use_flight_id:
        # Filter out records without a source flight_id (used as primary key).
        valid_records: List[FlightRecord] = [
            r for r in records if r.flight_id is not None
        ]
        query = UPSERT_SQL_WITH_ID
    else:
        # Legacy path: rely on per-run uniqueness
        valid_records = [r for r in records if r.flight_num]
        query = UPSERT_SQL_LEGACY
    if not valid_records:
        return 0

    params_list = [record.to_db_params(ingest_run_id) for record in valid_records]
    db_client.executemany(query, params_list)
    return len(params_list)


__all__ = ["upsert_flights"]
