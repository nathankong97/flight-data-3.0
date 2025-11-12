-- Creates a US-origin commercial features materialized view for leakage detection
-- Offsets are hours; falls back to airport timezone_utc_offset when per-flight is NULL.

CREATE MATERIALIZED VIEW IF NOT EXISTS public.flights_us_origin_commercial_features AS
WITH base AS (
  SELECT
    f.flight_id,
    f.flight_num,
    f.airline,
    f.airline_iata,
    f.aircraft_code,
    f.aircraft_text,
    f.aircraft_reg,
    f.origin_iata,
    f.dest_iata,
    f.origin_terminal,
    f.origin_gate,
    f.dest_terminal,
    f.dest_gate,
    COALESCE(f.real_dep, f.sched_dep) AS dep_epoch,
    COALESCE(f.real_arr, f.sched_arr) AS arr_epoch,
    COALESCE(f.origin_offset::numeric, ao.timezone_utc_offset) AS origin_offset_hours,
    COALESCE(f.dest_offset::numeric,   ad.timezone_utc_offset) AS dest_offset_hours
  FROM public.flights_commercial f
  JOIN public.airports ao
    ON ao.iata = f.origin_iata AND ao.country = 'United States'
  LEFT JOIN public.airports ad
    ON ad.iata = f.dest_iata
),
feats AS (
  SELECT
    flight_id,
    flight_num,
    -- Temporal
    (to_timestamp(dep_epoch) + (interval '1 hour' * origin_offset_hours)) AS dep_local_ts,
    (to_timestamp(arr_epoch) + (interval '1 hour' * dest_offset_hours))   AS arr_local_ts,
    EXTRACT(HOUR FROM (to_timestamp(dep_epoch) + (interval '1 hour' * origin_offset_hours)))::int AS dep_local_hour,
    EXTRACT(DOW  FROM (to_timestamp(dep_epoch) + (interval '1 hour' * origin_offset_hours)))::int AS dep_dow,
    EXTRACT(EPOCH FROM (to_timestamp(arr_epoch) - to_timestamp(dep_epoch))) / 60.0 AS block_mins,
    (
      EXTRACT(HOUR FROM (to_timestamp(dep_epoch) + (interval '1 hour' * origin_offset_hours))) >= 21
      OR EXTRACT(HOUR FROM (to_timestamp(dep_epoch) + (interval '1 hour' * origin_offset_hours))) <= 4
    ) AS is_night_bank,
    -- Operator
    airline,
    airline_iata,
    (COALESCE(airline,'') ~* '(cargo|freight)') AS cargo_letter,
    -- Aircraft
    aircraft_code,
    aircraft_text,
    aircraft_reg,
    (
      COALESCE(aircraft_text,'') ~ 'F$'
      OR COALESCE(aircraft_code,'') ~ 'F$'
      OR COALESCE(aircraft_code,'') IN (
        'B77F','B77L','B741','76F','74F','74Y','77F','74N','77X','75F','747','741','74H','73E','33F','33X','33Y',
        'B744F','B763F','B752F','A332F','A306F'
      )
    ) AS is_freighter_type_guess,
    (COALESCE(aircraft_text,'') ~* '(Citation|C25[0-9]|C56[0-9]|C68[0-9]|Gulfstream|GLF[0-9]|G280|Global|GLEX|Learjet|H25B|Hawker|Falcon|FA7X|FA8X|Phenom|E55P|EMB[- ]?505|PC-12|King Air|BE20|BE30)') AS is_bizjet_type_guess,
    (aircraft_reg IS NULL OR NULLIF(trim(aircraft_reg),'') IS NULL) AS missing_tailnumber,
    -- Route/Airport
    origin_iata,
    dest_iata,
    ((origin_iata IN ('MEM','SDF','CVG','ILN','ANC','ONT','RFD','MIA','LCK','IND','IAH','DFW'))
      OR (dest_iata IN ('MEM','SDF','CVG','ILN','ANC','ONT','RFD','MIA','LCK','IND','IAH','DFW'))) AS involves_cargo_hub,
    ((origin_iata IN ('GYR','ROW','VCV','SBD','MZJ','GWO','PAE','GKY'))
      OR (dest_iata IN ('GYR','ROW','VCV','SBD','MZJ','GWO','PAE','GKY'))) AS involves_mro_storage,
    (origin_iata = dest_iata AND origin_iata IS NOT NULL) AS origin_equals_dest,
    (origin_terminal IS NULL AND dest_terminal IS NULL) AS both_terminals_missing,
    (origin_gate IS NULL AND dest_gate IS NULL)         AS both_gates_missing
  FROM base
),
with_week AS (
  SELECT
    f.*,
    COUNT(*) OVER (
      PARTITION BY airline_iata, origin_iata, dest_iata, date_trunc('week', dep_local_ts)
    ) AS flights_per_week
  FROM feats f
)
SELECT
  ww.flight_id,
  ww.flight_num,
  -- Temporal
  ww.dep_local_ts,
  ww.arr_local_ts,
  ww.dep_local_hour,
  ww.dep_dow,
  ww.block_mins,
  ww.is_night_bank,
  -- Operator
  ww.airline,
  ww.airline_iata,
  ww.cargo_letter,
  -- Aircraft
  ww.aircraft_code,
  ww.aircraft_text,
  ww.aircraft_reg,
  ww.is_freighter_type_guess,
  ww.is_bizjet_type_guess,
  ww.missing_tailnumber,
  -- Route/Airport
  ww.origin_iata,
  ww.dest_iata,
  ww.involves_cargo_hub,
  ww.involves_mro_storage,
  ww.origin_equals_dest,
  ww.both_terminals_missing,
  ww.both_gates_missing,
  -- Recurrence
  ww.flights_per_week,
  (ww.flights_per_week <= 3) AS low_recurrence,
  -- Result Scores
  ((CASE WHEN ww.cargo_letter THEN 3 ELSE 0 END)
   + (CASE WHEN ww.is_freighter_type_guess THEN 4 ELSE 0 END)
   + (CASE WHEN ww.is_night_bank THEN 1 ELSE 0 END)
   + (CASE WHEN ww.involves_cargo_hub THEN 1 ELSE 0 END)
  ) AS suspected_cargo_leak,
  ((CASE WHEN ww.flights_per_week <= 3 THEN 3 ELSE 0 END)
   + (CASE WHEN ww.origin_equals_dest THEN 4 ELSE 0 END)
   + (CASE WHEN ww.involves_mro_storage THEN 3 ELSE 0 END)
   + (CASE WHEN ww.missing_tailnumber THEN 2 ELSE 0 END)
   + (CASE WHEN ww.both_terminals_missing THEN 1 ELSE 0 END)
   + (CASE WHEN ww.both_gates_missing THEN 1 ELSE 0 END)
   + (CASE WHEN (NOT ww.cargo_letter AND NOT ww.is_freighter_type_guess AND NOT ww.involves_cargo_hub AND ww.is_night_bank) THEN 1 ELSE 0 END)
  ) AS suspected_airline_charter
FROM with_week ww;

CREATE UNIQUE INDEX IF NOT EXISTS idx_flights_us_origin_commercial_features_fid
  ON public.flights_us_origin_commercial_features (flight_id);

COMMENT ON MATERIALIZED VIEW public.flights_us_origin_commercial_features IS
  'Engineered features and scores for detecting cargo/charter leakage within US-origin flights_commercial.';

