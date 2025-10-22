-- Source: https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat
-- Notes:
--   * Dataset uses '\N' for null values; ensure import steps translate them to SQL NULLs.
--   * Dataset is UTF-8 encoded.

CREATE TABLE IF NOT EXISTS public.airlines (
    airline_id      INTEGER PRIMARY KEY,
    name            TEXT        NOT NULL,
    alias           TEXT,
    iata            TEXT,
    icao            TEXT,
    callsign        TEXT,
    country         TEXT,
    active_flag     VARCHAR(1),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_airlines_iata ON public.airlines (iata);
CREATE INDEX IF NOT EXISTS idx_airlines_icao ON public.airlines (icao);
CREATE INDEX IF NOT EXISTS idx_airlines_country ON public.airlines (country);
