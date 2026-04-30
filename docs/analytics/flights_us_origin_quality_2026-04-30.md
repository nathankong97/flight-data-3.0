# `flights` US-Origin Data Quality Analysis - 2026-04-30

## Scope

- Database: `flight_data`
- User used for analysis: `codex`
- Core table: `public.flights`
- Departure filter:
  - Joined `public.flights.origin_iata` to `public.airports.iata`
  - Included only `airports.country IN ('United States', 'Puerto Rico', 'Guam')`
- This analysis is on the core `flights` table, not only `flights_commercial`.

## High-Level Volume

- Total rows in `public.flights`: `9,778,194`
- Rows in US/Puerto Rico/Guam departure scope: `5,166,241`
- Distinct `flight_id`s in scope: `5,166,241`
- Distinct ingest runs in scope: `367`
- Departure airports in scope: `133`
- Distinct destination IATA values in scope: `2,397`
- Row `created_at` range: `2025-10-28 22:00:03-04` through `2026-04-29 22:57:28-04`

## Departure Geography

- United States: `5,115,261` rows across `131` departure airports
- Puerto Rico: `45,527` rows across `1` departure airport
- Guam: `5,453` rows across `1` departure airport

## Top Departure Airports

- `ORD`: `230,135` rows
- `ATL`: `202,556` rows
- `DFW`: `185,035` rows
- `DEN`: `173,420` rows
- `LAX`: `145,528` rows
- `MIA`: `138,999` rows
- `CLT`: `135,787` rows
- `PHX`: `127,030` rows
- `IAH`: `116,708` rows
- `LAS`: `114,623` rows

## Schedule And Time Coverage

- `sched_dep` missing: `0`
- `sched_arr` missing: `0`
- Scheduled departure range: `2025-10-27 10:05:00-04` through `2026-05-01 10:52:00-04`
- `real_dep` missing: `369,001` rows
- `real_arr` missing: `486,793` rows
- Future scheduled departures at analysis time: `2,371`
- Future scheduled departures have `100%` missing real departure and arrival times, which is expected.
- For past/current scheduled departures:
  - Missing `real_dep`: `7.10%`
  - Missing `real_arr`: `9.38%`

## Status Pattern

- `Departed`: `4,797,553` rows (`92.86%`)
- `Estimated`: `223,056` rows (`4.32%`)
- `Canceled`: `92,444` rows (`1.79%`)
- `Unknown`: `51,171` rows (`0.99%`)
- `Scheduled`: `2,017` rows (`0.04%`)

## Field Completeness

- `flight_num`: `0.00%` missing
- `status_detail`: `0.00%` missing
- `airline`: `4.49%` missing
- `airline_iata`: `10.61%` missing
- `aircraft_code`: `0.30%` missing
- `aircraft_reg`: `4.38%` missing
- `origin_terminal`: `55.12%` missing
- `origin_gate`: `22.16%` missing
- `dest_terminal`: `59.57%` missing
- `dest_gate`: `25.62%` missing
- Nullish/bad `dest_iata`: `0.00%` overall, with `22` nullish rows found in detailed route checks

## Destination Pattern

- Domestic US destinations: `4,556,771` rows (`88.20%`)
- Mexico: `93,556` rows (`1.81%`)
- Canada: `86,527` rows (`1.67%`)
- Destination not found in `airports` reference: `55,087` rows (`1.07%`)
- Puerto Rico: `27,390` rows (`0.53%`)
- United Kingdom: `23,062` rows (`0.45%`)
- Dominican Republic: `23,050` rows (`0.45%`)

## Top Destinations

- `ORD`: `170,025` rows
- `ATL`: `158,331` rows
- `DEN`: `132,214` rows
- `DFW`: `127,908` rows
- `PHX`: `105,907` rows
- `LAX`: `101,933` rows
- `CLT`: `98,787` rows
- `LAS`: `98,665` rows
- `MCO`: `92,336` rows
- `LGA`: `85,079` rows

## Reference Data Gaps

- Rows with destination IATA values not found in `public.airports`: `55,087`
- Top unmatched destination codes:
  - `QQN`: `1,894`
  - `NLU`: `1,818`
  - `XWA`: `1,696`
  - `NSB`: `1,674`
  - `JZI`: `1,393`
  - `CSL`: `1,202`
  - `SVC`: `1,193`
  - `QTC`: `1,071`
  - `TQO`: `886`
  - `QQR`: `851`

## Route And Coordinate Quality

- `origin_iata = dest_iata`: `16,275` rows
- Nullish destination rows: `22`
- Missing origin coordinates: `0`
- Missing destination coordinates: `22`
- Bad origin coordinate ranges: `0`
- Bad destination coordinate ranges: `0`

## Timing Quality

- Scheduled arrival before scheduled departure: `5,531` rows
- Real arrival before real departure: `163` rows
- Scheduled block time over 24 hours: `164` rows
- Real block time over 24 hours: `0` rows
- Departure delay median: `17.8` minutes
- Departure delay P90: `73.2` minutes
- Departure delay P99: `255.9` minutes
- Scheduled block median: `131.0` minutes
- Scheduled block P99: `725.0` minutes

## Likely Non-Passenger Leakage In Core Table

- Cargo/freight name signals: `62,019` rows
- Freighter-like aircraft code/text signals: `127,177` rows
- Business/private operator signals, such as NetJets, Flexjet, or private: `160,678` rows
- The core `flights` table is not passenger-only. Use `public.flights_commercial` or apply additional filters when the analysis requires commercial passenger traffic only.

## Monthly Distribution By Scheduled Departure

- `2025-10`: `128,606` rows
- `2025-11`: `847,591` rows
- `2025-12`: `865,475` rows
- `2026-01`: `812,910` rows
- `2026-02`: `763,028` rows
- `2026-03`: `899,464` rows
- `2026-04`: `848,199` rows
- `2026-05`: `968` rows

## Practical Takeaways

- Core IDs and scheduled timestamps are strong: no duplicate `flight_id`s in scope and no missing scheduled departure/arrival timestamps.
- Gate and terminal fields are sparse and should be treated as optional enrichment, not required operational facts.
- Airline identity is usable but incomplete, especially `airline_iata`; downstream grouping should handle missing carrier codes.
- Destination reference coverage needs cleanup for about `1.07%` of scoped rows.
- Same-origin-destination routes and negative/impossible block times should be reviewed before using the table for route duration modeling.
- The core table includes cargo, freighter, business aviation, and private-like records; passenger-only analytics should not use raw `flights` without filtering.

## Reproducibility Notes

- The scoped dataset was built with this pattern:

```sql
SELECT f.*, a.country AS origin_country
FROM public.flights f
JOIN public.airports a
  ON a.iata = f.origin_iata
WHERE a.country IN ('United States', 'Puerto Rico', 'Guam');
```

- The analysis was run on April 30, 2026 against the local PostgreSQL database `flight_data`.
