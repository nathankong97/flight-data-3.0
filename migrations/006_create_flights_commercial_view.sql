-- Creates a view exposing only commercial passenger flights
-- based on cargo/freight and freighter heuristics from legacy rules.
--
-- Notes:
-- - Uses PostgreSQL regex operators (~ for case-sensitive, ~* for case-insensitive).
-- - Coalesces nullable text fields to avoid null-propagation in predicates.
-- - Keeps B744 flights only for specific passenger operators (LH, CA, FV).

CREATE OR REPLACE VIEW public.flights_commercial AS
SELECT
    *
FROM public.flights f
WHERE NOT (
    -- Cargo/freight keywords on owner or airline
    COALESCE(f.owner_name, '') ~* '(cargo|freight)'
    OR COALESCE(f.airline, '') ~* '(cargo|freight)'

    -- Aircraft text suggests a freighter (suffix 'F' on common manufacturers)
    OR (
        COALESCE(f.aircraft_text, '') ~* '(Boeing|CRJ|Airbus|McDonnell)'
        AND COALESCE(f.aircraft_text, '') ~ 'F$'
    )

    -- Explicit freighter/legacy codes when no aircraft_text present
    OR (
        COALESCE(f.aircraft_text, '') = ''
        AND COALESCE(f.aircraft_code, '') IN (
            'B77F','B77L','B741','76F','74F','74Y','77F','74N','77X','75F','747','741','74H','73E','33F','33X','33Y'
        )
    )

    -- Specific converted freighter type text
    OR COALESCE(f.aircraft_text, '') IN ('Boeing 747-48E(BDSF)')

    -- Treat most B744 flights as non-commercial, except specific passenger operators
    OR (
        COALESCE(f.aircraft_code, '') = 'B744'
        AND (f.airline_iata IS NULL OR f.airline_iata NOT IN ('LH','CA','FV'))
    )

    -- Non-commercial/unknown housekeeping from legacy rules
    OR f.dest_iata IS NULL
    OR UPPER(COALESCE(f.dest_iata, '')) = 'NULL'
    OR (f.airline IS NULL AND f.airline_icao IS NULL)
    OR COALESCE(f.airline, '') ILIKE 'Private owner'
);

COMMENT ON VIEW public.flights_commercial IS 'Filtered commercial passenger flights based on cargo/freighter heuristics and B744 exceptions.';
