-- Defines the core flights fact table used by the ingestion pipeline.
-- All schedule/actual timestamps are stored as Unix epoch values (seconds since 1970-01-01 UTC).

CREATE TABLE IF NOT EXISTS public.flights (
    flight_id               BIGINT     PRIMARY KEY,
    ingest_run_id           UUID        NOT NULL,
    flight_num              TEXT        NOT NULL,
    status_detail           TEXT,
    aircraft_code           TEXT,
    aircraft_text           TEXT,
    aircraft_reg            TEXT,
    aircraft_co2            NUMERIC(12,2),
    aircraft_restricted     BOOLEAN,
    owner_name              TEXT,
    owner_iata              TEXT,
    owner_icao              TEXT,
    airline                 TEXT,
    airline_iata            TEXT,
    airline_icao            TEXT,
    origin_iata             TEXT,
    origin_offset           SMALLINT,
    origin_offset_abbr      TEXT,
    origin_offset_dst       BOOLEAN,
    origin_terminal         TEXT,
    origin_gate             TEXT,
    dest_iata               TEXT,
    dest_icao               TEXT,
    dest_offset             SMALLINT,
    dest_offset_abbr        TEXT,
    dest_offset_dst         BOOLEAN,
    dest_terminal           TEXT,
    dest_gate               TEXT,
    sched_dep               BIGINT,
    sched_arr               BIGINT,
    real_dep                BIGINT,
    real_arr                BIGINT,
    origin_lat              DOUBLE PRECISION,
    origin_lng              DOUBLE PRECISION,
    dest_lat                DOUBLE PRECISION,
    dest_lng                DOUBLE PRECISION,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Primary key on flight_id ensures uniqueness per upstream flight.
CREATE INDEX IF NOT EXISTS idx_flights_sched_dep ON public.flights (sched_dep);
CREATE INDEX IF NOT EXISTS idx_flights_sched_arr ON public.flights (sched_arr);
CREATE INDEX IF NOT EXISTS idx_flights_airline_iata ON public.flights (airline_iata);
CREATE INDEX IF NOT EXISTS idx_flights_origin_dest ON public.flights (origin_iata, dest_iata);
