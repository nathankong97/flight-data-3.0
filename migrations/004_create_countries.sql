-- Source: https://raw.githubusercontent.com/jpatokal/openflights/master/data/countries.dat
-- Notes:
--   * Dataset uses '\N' to represent null values; convert them to SQL NULL during import.
--   * Data is UTF-8 encoded.

CREATE TABLE IF NOT EXISTS public.countries (
    country_id  SERIAL PRIMARY KEY,
    name        TEXT        NOT NULL,
    iso_code    TEXT,
    dafif_code  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_countries_name_iso_dafif
    ON public.countries (name, iso_code, dafif_code);
CREATE INDEX IF NOT EXISTS idx_countries_iso_code ON public.countries (iso_code);
