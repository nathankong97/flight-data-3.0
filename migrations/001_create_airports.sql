-- Source: https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat
-- Notes:
--   * Dataset uses '\N' for null values; ensure ETL converts them to actual NULLs before loading.
--   * All strings are UTF-8 encoded.

CREATE TABLE IF NOT EXISTS public.airports (
    airport_id              INTEGER PRIMARY KEY,
    name                    TEXT        NOT NULL,
    city                    TEXT,
    country                 TEXT,
    iata                    VARCHAR(3),
    icao                    VARCHAR(4),
    latitude                DOUBLE PRECISION NOT NULL,
    longitude               DOUBLE PRECISION NOT NULL,
    altitude_feet           INTEGER,
    timezone_utc_offset     NUMERIC(4,2),
    dst_rule                VARCHAR(1),
    tz_database_timezone    TEXT,
    airport_type            TEXT,
    source                  TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_airports_iata ON airports (iata);
CREATE INDEX IF NOT EXISTS idx_airports_icao ON airports (icao);
CREATE INDEX IF NOT EXISTS idx_airports_country_city ON airports (country, city);
