# Migration Guide

## 001_create_airports.sql
- Bootstraps the `public.airports` reference table used by flight ingestion.
- Apply with `psql "$DATABASE_URL" -f migrations/001_create_airports.sql`; ensure the role has privileges before running.
- Creates indexes on IATA, ICAO, and country/city to accelerate lookup queries.
- After creating the table, seed it with the OpenFlights data:
  ```bash
  curl -o airports.dat https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat
  psql "$DATABASE_URL" \
    -c "\COPY airports (airport_id,name,city,country,iata,icao,latitude,longitude,altitude_feet,timezone_utc_offset,dst_rule,tz_database_timezone,airport_type,source) \
        FROM '$(pwd)/airports.dat' WITH (FORMAT csv, NULL '\\N', QUOTE '\"');"
  rm airports.dat
  ```
- Expected row count after loading: 7,698.
- Required access:
  * Role must have `USAGE` and `CREATE` on the target schema (`public` by default):
    ```sql
    GRANT USAGE, CREATE ON SCHEMA public TO codex;
    ```
  * Role must own or have `INSERT`, `UPDATE`, and `SELECT` on `public.airports` to support upserts:
    ```sql
    GRANT SELECT, INSERT, UPDATE ON TABLE public.airports TO codex;
    ```
- The OpenFlights seed uses UTF-8 encoding and represents missing values as `\N`; the `\copy` command above handles null conversion automatically.

## 002_create_airlines.sql
- Creates the `public.airlines` reference table with indexes on IATA, ICAO, and country.
- Apply with `psql "$DATABASE_URL" -f migrations/002_create_airlines.sql` after ensuring the role has `USAGE` and `CREATE` on the target schema.
- Populate with the OpenFlights airline catalog:
  ```bash
  curl -o airlines.dat https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat
  psql "$DATABASE_URL" \
    -c "\COPY airlines (airline_id,name,alias,iata,icao,callsign,country,active_flag) \
        FROM '$(pwd)/airlines.dat' WITH (FORMAT csv, NULL '\\N', QUOTE '\"');"
  rm airlines.dat
  ```
- Expected row count after loading: 6,162.
- Grant the application role `SELECT`, `INSERT`, and `UPDATE` on `public.airlines` to allow ongoing upserts.

## 003_create_aircrafts.sql
- Creates the `public.aircrafts` lookup table with indexes on both IATA and ICAO codes.
- Apply with `psql "$DATABASE_URL" -f migrations/003_create_aircrafts.sql` once the role has `USAGE` and `CREATE` on the schema.
- Populate the table with the OpenFlights aircraft catalog:
  ```bash
  curl -o planes.dat https://raw.githubusercontent.com/jpatokal/openflights/master/data/planes.dat
  psql "$DATABASE_URL" \
    -c "\COPY aircrafts (name,iata_code,icao_code) \
        FROM '$(pwd)/planes.dat' WITH (FORMAT csv, NULL '\\N', QUOTE '\"');"
  rm planes.dat
  ```
- Expected row count after loading: 246.
- Grant the application role `SELECT`, `INSERT`, and `UPDATE` on `public.aircrafts` for future refreshes.

## 004_create_countries.sql
- Defines the `public.countries` lookup table with a surrogate `country_id` primary key and unique index on `(name, iso_code, dafif_code)`.
- Apply with `psql "$DATABASE_URL" -f migrations/004_create_countries.sql` after confirming schema privileges.
- Populate using the OpenFlights countries dataset:
  ```bash
  curl -o countries.dat https://raw.githubusercontent.com/jpatokal/openflights/master/data/countries.dat
  psql "$DATABASE_URL" \
    -c "\COPY countries (name,iso_code,dafif_code) \
        FROM '$(pwd)/countries.dat' WITH (FORMAT csv, NULL '\\N', QUOTE '\"');"
  rm countries.dat
  ```
- Expected row count after loading: 261.
- Grant `SELECT`, `INSERT`, and `UPDATE` on `public.countries` to the application role for refresh runs.

## 005_create_flights.sql
- Creates the primary `public.flights` fact table keyed by the upstream flight identifier (`flight_id` from `identification.row`). This replaces the prior surrogate `id` sequence.
- Columns capture aircraft metadata, offsets, gates, coordinates, and schedule/actual times stored as Unix epoch seconds (`BIGINT`); `ingest_run_id` (UUID) links to batch metadata.
- Apply with `psql "$DATABASE_URL" -f migrations/005_create_flights.sql` once the role has `USAGE`, `CREATE`, and table-level DML privileges.
- Recommended privileges for the ingestion role:
  ```sql
  GRANT SELECT, INSERT, UPDATE ON TABLE public.flights TO ingest_app;
  ```
- Ingestion should normalize incoming timestamps to epoch seconds; downstream analytics can convert with `TO_TIMESTAMP(sched_dep)` when needed.
- Populate the table via parameterized `INSERT ... ON CONFLICT (flight_id) DO UPDATE` statements to upsert by source flight identity across runs.

## 006_create_flights_commercial_view.sql
- Creates the `public.flights_commercial` view exposing commercial passenger flights only.
- The view filters out cargo and private flights using:
  - Cargo/freight keywords on owner/airline (`~* '(cargo|freight)'`)
  - Freighter suffix in `aircraft_text` (manufacturers + `F$`)
  - Explicit freighter codes when `aircraft_text` is empty
  - Converted freighter text: `Boeing 747-48E(BDSF)`
  - B744 exception: only allow airlines `LH`, `CA`, `FV`
  - Housekeeping: `dest_iata IS NULL` or literal `'NULL'`, `(airline IS NULL AND airline_icao IS NULL)`, and `airline ILIKE 'Private owner'`
- Apply with `psql "$DATABASE_URL" -f migrations/006_create_flights_commercial_view.sql`.
- To update the airline blocklist dynamically from `data/filtered_airlines.txt`:
  - Ensure `DATABASE_URL` is set
  - Run: `python scripts/update_flights_commercial_view.py`
  - Verify (expect 0):
    ```sql
    SELECT COUNT(*)
    FROM public.flights_commercial
    WHERE UPPER(COALESCE(airline_icao, '')) IN ('NCA','PAC','FDX', ...);
    ```

## Postgres Role Setup Cheatsheet
- Grant schema and database privileges needed for migrations and integration tests:
  ```sql
  GRANT CREATE ON DATABASE flight_data TO ingest_app;
  GRANT USAGE, CREATE ON SCHEMA public TO ingest_app;
  ```
- Ensure the role defaults to the `public` schema (avoids surprises with `$user`):
  ```sql
  ALTER ROLE ingest_app SET search_path TO public;
  ```
- Allow runtime DML on the fact table:
  ```sql
  GRANT SELECT, INSERT, UPDATE ON TABLE public.flights TO ingest_app;
  ```
 
