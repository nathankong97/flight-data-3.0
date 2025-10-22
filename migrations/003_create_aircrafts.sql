-- Source: https://raw.githubusercontent.com/jpatokal/openflights/master/data/planes.dat
-- Notes:
--   * Dataset uses '\N' to represent null values; convert them during import.
--   * Dataset is UTF-8 encoded.

CREATE TABLE IF NOT EXISTS public.aircrafts (
    name        TEXT PRIMARY KEY,
    iata_code   TEXT,
    icao_code   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aircrafts_iata_code ON public.aircrafts (iata_code);
CREATE INDEX IF NOT EXISTS idx_aircrafts_icao_code ON public.aircrafts (icao_code);
