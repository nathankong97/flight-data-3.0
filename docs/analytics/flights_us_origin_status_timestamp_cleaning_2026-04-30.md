# `flights` US-Origin Status/Timestamp Quality Report - 2026-04-30

## Scope

- Database: `flight_data`
- Table: `public.flights`
- Departure filter:
  - Joined `public.flights.origin_iata` to `public.airports.iata`
  - Included `airports.country IN ('United States', 'Puerto Rico', 'Guam')`
- Rows analyzed: `5,166,241`
- Focus: relationship between `status_detail`, `real_dep`, and `real_arr`
- Status normalization:
  - `Departed ...` -> `Departed`
  - `Estimated ...` -> `Estimated`
  - `Scheduled ...` -> `Scheduled`
  - `Canceled ...` -> `Canceled`
  - `Unknown ...` -> `Unknown`

## Executive Cleaning Conclusion

- `Departed` is the only status that generally indicates actual timestamp data is available.
- `Estimated`, `Scheduled`, and `Unknown` should be treated as unresolved/open statuses, not completed-flight statuses.
- Old `Estimated`, `Scheduled`, and `Unknown` rows with no real timestamps should be treated as stale incomplete data.
- `Canceled` should be kept as its own valid final status; missing `real_dep` and `real_arr` are expected for canceled flights.
- For historical analytics, use rows with both `real_dep` and `real_arr` when analyzing completed flight operations, arrival delays, or block times.
- For departure-only analytics, `Departed` rows with `real_dep` present but `real_arr` missing can still be useful.

## Main Status/Timestamp Pattern

| Status | Rows | `real_dep` present | `real_arr` present | Both real timestamps present | Both real timestamps missing |
|---|---:|---:|---:|---:|---:|
| `Departed` | `4,797,553` | `99.99%` | `97.54%` | `97.53%` | `0.00%` |
| `Estimated` | `223,056` | `0.00%` | `0.00%` | `0.00%` | `100.00%` |
| `Canceled` | `92,444` | `0.00%` | `0.00%` | `0.00%` | `100.00%` |
| `Unknown` | `51,171` | `0.00%` | `0.00%` | `0.00%` | `100.00%` |
| `Scheduled` | `2,017` | `0.00%` | `0.00%` | `0.00%` | `100.00%` |

## Detailed Real-Time Patterns By Status

| Status | Real-time pattern | Rows | Percent within status |
|---|---|---:|---:|
| `Canceled` | Both `real_dep` and `real_arr` missing | `92,444` | `100.00%` |
| `Departed` | Both `real_dep` and `real_arr` present | `4,679,262` | `97.53%` |
| `Departed` | Only `real_dep` present | `117,978` | `2.46%` |
| `Departed` | Only `real_arr` present | `186` | `0.00%` |
| `Departed` | Both `real_dep` and `real_arr` missing | `127` | `0.00%` |
| `Estimated` | Both `real_dep` and `real_arr` missing | `223,056` | `100.00%` |
| `Scheduled` | Both `real_dep` and `real_arr` missing | `2,017` | `100.00%` |
| `Unknown` | Both `real_dep` and `real_arr` missing | `51,171` | `100.00%` |

## Interpretation By Status

### `Departed`

- Most `Departed` rows are high quality for completed-flight analysis.
- `97.53%` have both actual departure and actual arrival timestamps.
- `2.46%` have `real_dep` but no `real_arr`.
- These partial rows are acceptable for departure delay analysis, but not for arrival delay or real block-time analysis.
- `127` `Departed` rows have no real timestamps at all; these should be flagged as inconsistent.

### `Estimated`

- `223,056` rows.
- `100%` have both `real_dep` and `real_arr` missing.
- This means `Estimated` does not mean an actual departure or arrival was captured.
- For live/future operations, `Estimated` can mean the provider has an estimated movement time.
- For historical data, old `Estimated` rows are stale incomplete records because actual timestamps never arrived.

### `Scheduled`

- `2,017` rows.
- `100%` have both `real_dep` and `real_arr` missing.
- Future `Scheduled` rows are normal.
- Past `Scheduled` rows are stale incomplete records and should not count as operated flights.

### `Unknown`

- `51,171` rows.
- `100%` have both `real_dep` and `real_arr` missing.
- No `Unknown` rows had either actual timestamp.
- `Unknown` should be treated as unresolved feed data, not as a meaningful operational outcome.

### `Canceled`

- `92,444` rows.
- `100%` have both `real_dep` and `real_arr` missing.
- This is expected and should not be treated as missing-data failure.
- `Canceled` should remain separate from unresolved statuses because it is a valid final non-operated status.

## Future Versus Past Quality

| Schedule bucket | Status | Rows | Both real present | Both real missing | Only `real_dep` | Only `real_arr` |
|---|---|---:|---:|---:|---:|---:|
| Future | `Estimated` | `1,244` | `0.00%` | `100.00%` | `0.00%` | `0.0000%` |
| Future | `Scheduled` | `460` | `0.00%` | `100.00%` | `0.00%` | `0.0000%` |
| Past/current | `Departed` | `4,797,553` | `97.53%` | `0.00%` | `2.46%` | `0.0039%` |
| Past/current | `Estimated` | `221,812` | `0.00%` | `100.00%` | `0.00%` | `0.0000%` |
| Past/current | `Canceled` | `92,444` | `0.00%` | `100.00%` | `0.00%` | `0.0000%` |
| Past/current | `Unknown` | `51,171` | `0.00%` | `100.00%` | `0.00%` | `0.0000%` |
| Past/current | `Scheduled` | `1,557` | `0.00%` | `100.00%` | `0.00%` | `0.0000%` |

## Staleness Of Unresolved Statuses

These rows have no `real_dep` and no `real_arr`. The key quality question is whether they are future/recent or old.

### `Estimated`

| Staleness bucket | Rows | Percent of `Estimated` |
|---|---:|---:|
| Future | `1,237` | `0.55%` |
| 0-2h past | `521` | `0.23%` |
| 2-6h past | `1,458` | `0.65%` |
| 6-24h past | `7,790` | `3.49%` |
| 1-3d past | `2,003` | `0.90%` |
| 3-7d past | `3,279` | `1.47%` |
| 1-4w past | `23,224` | `10.41%` |
| 4w+ past | `183,544` | `82.29%` |

Cleaning interpretation:

- Only a small fraction of `Estimated` rows are future or very recent.
- Most `Estimated` rows are old unresolved records.
- Historical `Estimated` rows should be excluded from completed-flight metrics unless another source provides actual event times.

### `Scheduled`

| Staleness bucket | Rows | Percent of `Scheduled` |
|---|---:|---:|
| Future | `460` | `22.81%` |
| 0-2h past | `8` | `0.40%` |
| 2-6h past | `43` | `2.13%` |
| 6-24h past | `114` | `5.65%` |
| 1-3d past | `13` | `0.64%` |
| 3-7d past | `20` | `0.99%` |
| 1-4w past | `107` | `5.30%` |
| 4w+ past | `1,252` | `62.07%` |

Cleaning interpretation:

- Future `Scheduled` rows are valid operationally open records.
- Past `Scheduled` rows should age out into a stale incomplete bucket.
- `Scheduled` rows more than 24-72 hours past scheduled departure should not be considered active.

### `Unknown`

| Staleness bucket | Rows | Percent of `Unknown` |
|---|---:|---:|
| 6-24h past | `37` | `0.07%` |
| 1-3d past | `613` | `1.20%` |
| 3-7d past | `924` | `1.81%` |
| 1-4w past | `5,604` | `10.95%` |
| 4w+ past | `43,993` | `85.97%` |

Cleaning interpretation:

- `Unknown` is almost entirely old unresolved feed data.
- Since no `Unknown` rows have actual timestamps, it should not be used as evidence that a flight operated.
- Old `Unknown` rows should be marked as stale incomplete.

## Recommended Derived Quality Buckets

- `completed`
  - `status_detail ILIKE 'Departed%'`
  - `real_dep IS NOT NULL`
  - `real_arr IS NOT NULL`
  - Use for completed-flight, arrival-delay, and block-time analysis.

- `completed_missing_arrival`
  - `status_detail ILIKE 'Departed%'`
  - `real_dep IS NOT NULL`
  - `real_arr IS NULL`
  - Use only for departure-side analysis.

- `canceled`
  - `status_detail ILIKE 'Canceled%'`
  - `real_dep IS NULL`
  - `real_arr IS NULL`
  - Keep separate from missing-data failures.

- `future_or_recent_open`
  - Status is `Estimated`, `Scheduled`, or `Unknown`
  - Scheduled departure is in the future or within a short freshness window after departure.
  - Recommended freshness window: `24` to `72` hours after `sched_dep`.

- `stale_incomplete`
  - Status is `Estimated`, `Scheduled`, or `Unknown`
  - Both `real_dep` and `real_arr` are missing
  - `sched_dep` is more than the freshness window in the past.

- `status_timestamp_inconsistent`
  - `Departed` with neither `real_dep` nor `real_arr`
  - `Departed` with only `real_arr`
  - Any non-`Departed`/non-`Canceled` status with real timestamps, if future data produces those cases.

## Practical SQL Pattern

```sql
CASE
  WHEN status_detail ILIKE 'Canceled%' THEN 'canceled'

  WHEN status_detail ILIKE 'Departed%'
       AND real_dep IS NOT NULL
       AND real_arr IS NOT NULL THEN 'completed'

  WHEN status_detail ILIKE 'Departed%'
       AND real_dep IS NOT NULL
       AND real_arr IS NULL THEN 'completed_missing_arrival'

  WHEN status_detail ILIKE 'Departed%' THEN 'status_timestamp_inconsistent'

  WHEN status_detail ILIKE 'Estimated%'
       OR status_detail ILIKE 'Scheduled%'
       OR status_detail ILIKE 'Unknown%' THEN
    CASE
      WHEN to_timestamp(sched_dep) >= now() - interval '72 hours'
        THEN 'future_or_recent_open'
      ELSE 'stale_incomplete'
    END

  ELSE 'needs_review'
END AS derived_quality_status
```

## Analytics Usage Rules

- Use `completed` for historical:
  - Departure delay
  - Arrival delay
  - Real block time
  - Completed-flight counts

- Use `completed_missing_arrival` for:
  - Departure delay
  - Departure punctuality
  - Departure-volume analysis

- Do not use `completed_missing_arrival` for:
  - Arrival delay
  - Real block time
  - Completed arrival counts

- Exclude `stale_incomplete` from completed-flight metrics.
- Keep `future_or_recent_open` in live operational dashboards only.
- Keep `canceled` in cancellation metrics, but do not mix it with missing-data quality failures.
- Monitor `status_timestamp_inconsistent` as a data-quality alert bucket.

## Simple Final Cleaning Rule

- If `status_detail` is `Departed` and both real timestamps exist, treat the row as a clean completed flight.
- If `status_detail` is `Departed` and only `real_dep` exists, keep it for departure analysis only.
- If `status_detail` is `Canceled`, keep it as a final canceled flight.
- If `status_detail` is `Estimated`, `Scheduled`, or `Unknown` and the flight is old, mark it as stale incomplete.
- If `status_detail` is `Estimated`, `Scheduled`, or `Unknown` and the flight is future/recent, keep it as open but do not count it as completed.

## Reproducibility Query

```sql
WITH scoped AS (
  SELECT
    f.flight_id,
    f.flight_num,
    f.origin_iata,
    f.dest_iata,
    f.airline_iata,
    f.airline,
    f.status_detail,
    CASE
      WHEN f.status_detail ILIKE 'Departed%' THEN 'Departed'
      WHEN f.status_detail ILIKE 'Canceled%' THEN 'Canceled'
      WHEN f.status_detail ILIKE 'Scheduled%' THEN 'Scheduled'
      WHEN f.status_detail ILIKE 'Estimated%' THEN 'Estimated'
      WHEN f.status_detail ILIKE 'Unknown%' THEN 'Unknown'
      ELSE COALESCE(NULLIF(split_part(f.status_detail, ' ', 1), ''), '(missing)')
    END AS status_category,
    f.sched_dep,
    f.sched_arr,
    f.real_dep,
    f.real_arr,
    CASE
      WHEN f.real_dep IS NOT NULL AND f.real_arr IS NOT NULL THEN 'both_real_present'
      WHEN f.real_dep IS NOT NULL AND f.real_arr IS NULL THEN 'only_real_dep'
      WHEN f.real_dep IS NULL AND f.real_arr IS NOT NULL THEN 'only_real_arr'
      ELSE 'both_real_missing'
    END AS real_time_pattern
  FROM public.flights f
  JOIN public.airports a
    ON a.iata = f.origin_iata
  WHERE a.country IN ('United States', 'Puerto Rico', 'Guam')
)
SELECT
  status_category,
  real_time_pattern,
  count(*) AS rows,
  round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY status_category), 2)
    AS pct_within_status
FROM scoped
GROUP BY status_category, real_time_pattern
ORDER BY status_category, rows DESC;
```
