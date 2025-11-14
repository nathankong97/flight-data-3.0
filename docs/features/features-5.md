# Feature Request: Data Mining - labelling non-commercial flights; increasing data quality

## Context

### Working Taxonomy

- A pragmatic, iterative set of categories to bootstrap labeling.
- Clear boundaries so a flight lands in exactly one bucket.
- Adjustable: we can split/merge later as we learn from the data.

#### Scheduled Passenger (commercial) -> This is the target commercial flights

- Definition: Published, ticketed airline services carrying passengers on fixed schedules.
- Typical operators: Major, regional, LCCs (AA, DL, UA, WN, AS, B6, NK, F9, HA, ASQ, SKW, RPA).
- Operational pattern: Regular route patterns; airport pairs matching public timetables; normal day-time wave banks by
  hub.
- Primary signals:
    - Airline operator code in passenger carriers.
    - Aircraft not flagged as freighter or bizjet type.
    - Callsign format like airline prefix + numeric (AAL1234), not tailnumber-style.
    - Route appears repeatedly on a weekly cadence.
- Edge cases:
    - Passenger wide-bodies occasionally fly ferry/maintenance legs (should fall under positioning if unscheduled and
      marked as such).
    - Combi or dual-use operators (resolve by aircraft type and callsign).

#### Scheduled Cargo/Freight -> We will label this

- Definition: Published cargo networks (often nightly banks) moving freight on set schedules.
- Typical operators: FDX (FedEx), UPS, GTI (Atlas), CKS (Kalitta), WGN (Western Global), ABX, ATN, CLX, ABW, 5X/FX where
  applicable.
- Operational pattern: Night banks at cargo hubs (MEM, SDF, CVG, ILN, PANC, ONT, RFD, MIA); repeated lanes, fewer
  weekend reductions.
- Primary signals:
    - Operator in cargo carrier, airline name contains keywords such as cargo, and freight.
    - Aircraft model flagged freighter (777F, 767F, 757-200PCF, 747-8F, A300F, A330F), or contains "F".
    - Departure local hour in 21:00–04:00 window near cargo hubs.

#### Airline-Operated Charter/Jet Transfer -> We will label this

- Definition: Flights by passenger airlines that are not regular scheduled services: charters (e.g., sports/team),
  positioning/ferry legs, maintenance hops.
- Typical operators: Same as scheduled passenger airlines, plus charter specialists (iAero/SWI, Swift, Sun Country
  charters).
- Operational pattern: One-off or irregular routes; short same-day hops; hub-to-MRO; spikes around events.
- Primary signals:
    - Missing origin and destination's terminal and gates data.
    - Airline operator code present but no schedule match; unusual airport pair for that carrier.
    - Origin=dest (circuits) or hub-to-MRO airports (GWO, GYR, ROW, VCV).
    - Missing tailnumber in this flight.

### Target Data Slice

- Scope: filter to flights with US origin IATA only.
- Source: flights_commercial joined to a US airports reference (IATA→country/state).
- Output: a working subset table/view for labeling and iterative analysis.

### Reference Data Needed

- Airports: will use `public.airports` table.
- Airlines: primarily use fields: `airline`, `airline_iata`, and `airline_icao`; use `public.airlines` table for backup.
- Aircraft: fields `aircraft_code` for iata or icao code, `aircraft_text` for callsign or aircraft name.
- Tail number: fields `aircraft_reg` shows the registered tail number.

## Desired Outcome

- Build features for US‑origin flights in public.flights_commercial.
- Score two leakage classes: suspected_cargo_leak and suspected_airline_charter.
- Preserve auditability (signals, scores, versions) and support rapid iteration.

### Data Inputs

- Core: public.flights_commercial (derived from public.flights).
- Reference: public.airports (US origin filter).
- Offsets: use origin_offset/dest_offset as hours; fallback to airport tz if null.

### Slices & Features

- Materialized View
    - Temporal: dep_local_ts/arr_local_ts (timestamp + interval '1 hour' * offset), dep_local_hour, dep_dow, block_mins,
      is_night_bank (hour ≥21 or ≤4).
    - Operator: airline_iata/icao/name, cargo_letter (airline contains cargo/freight).
    - Aircraft: is_freighter_type_guess, is_bizjet_type_guess (safety net), missing_tailnumber.
    - Route/Airport: involves_cargo_hub, involves_mro_storage, origin_equals_dest, both_terminals_missing,
      both_gates_missing.
    - Recurrence: flights_per_week per (airline_iata, origin_iata, dest_iata, week), low_recurrence (<=3).

### Materialized View Definition

- Name: public.flights_us_origin_commercial_features
- Purpose: engineered features to detect cargo/charter leakage within commercial US‑origin flights
- **Fields**:
    - **Keys**: flight_id, flight_num
    - **Temporal**: dep_local_ts, arr_local_ts, dep_local_hour, dep_dow, block_mins, is_night_bank
    - **Operator**: airline, airline_iata, cargo_letter
    - **Aircraft**: aircraft_code, aircraft_text, aircraft_reg, is_freighter_type_guess, is_bizjet_type_guess,
      missing_tailnumber
    - **Route/Airport**: origin_iata, dest_iata, involves_cargo_hub, involves_mro_storage, origin_equals_dest, 
      both_terminals_missing, both_gates_missing
    - **Recurrence**: flights_per_week, low_recurrence (<=3/week)
    - **Result Score**: suspected_cargo_leak, suspected_airline_charter

## Implementation Notes

- First, review sql files for schema check-in: `migrations/*.sql`.

### Taxonomy & Signals

- Scheduled Passenger (commercial)
    - Using `public.flights_commercial` as the base is appropriate. Consider a backstop to catch residual non-passenger:
      widebody “F” types in aircraft_code/aircraft_text and “cargo/freight” keywords are already excluded by the
      view.
    - Repetition signal: compute route recurrence per week per airline to validate schedule-like routes.
- Scheduled Cargo/Freight
    - Since flights_commercial filters out most cargo, build this from public.flights (not the view). Good signals:
      cargo keywords in airline/owner_name, freighter codes in aircraft_code or trailing “F” in aircraft_text, and
      night bank windows at cargo hubs.
    - Add operator code lists (FDX/UPS/GTI/CKS/WGN/ABX/ATN/CLX/ABW). Without per-flight callsign, rely on
      airline_iata/icao membership and aircraft type.
- Airline-Operated Charter/Jet Transfer
    - Signals you listed exist in the schema:
        - Missing terminal/gate: origin_terminal, origin_gate, dest_terminal, dest_gate.
        - Airline operator present: airline_iata or airline_icao not null.
        - Origin = Dest: origin_iata = dest_iata.
        - MRO fields: route includes airports like GWO/GYR/ROW/VCV.
        - Missing tail number: aircraft_reg is null.
    - Caution: gate/terminal and tail number missingness alone are weak (common for smaller airports and some
      schedules). Combine with:
        - Low route recurrence for that airline (e.g., <=3 per week).
        - “Unscheduled” proxy: sched_dep IS NULL AND real_dep IS NOT NULL or large deviations.
        - Known charter-heavy carriers (e.g., SWQ/Sun Country charter ops, iAero) via airline_icao.
        - Positioning/maintenance: origin=dest, very short blocks, or MRO airport involvement.
- Business/Private
    - Haven't found a good clue to mine the data.

### Feature to Engineer

- Temporal
    - dep_local_ts, arr_local_ts: local timestamps using offsets.
    - dep_local_hour, dep_dow: hour-of-day and day-of-week.
    - is_night_bank: dep hour ≥21 or <=4 (cargo bank window).
    - block_mins: (arr - dep) minutes using actual, fallback to sched.
- Operator
    - airline_iata, airline_icao, airline.
    - cargo_letter: check `airline` contains keywords like "cargo" and "freight".
- Aircraft
    - is_freighter_type_guess: aircraft_code like freighter codes or aircraft_text ends with “F”.
    - is_bizjet_type_guess (safety net): bizjet families in aircraft_text (Citation, Gulfstream, Learjet, Hawker,
      Falcon, Phenom, Global, PC-12, King Air).
    - missing_tailnumber: aircraft_reg is null.
- Route/Airport
    - involves_cargo_hub: MEM, SDF, CVG, ILN, ANC, ONT, RFD, MIA, LCK, IND, IAH, DFW.
    - involves_mro_storage: GYR, ROW, VCV, SBD, MZJ, GWO, PAE, GKY.
    - origin_equals_dest: circuits/returns.
    - both_terminals_missing, both_gates_missing: both sides null.
- Behavior/Recurrence
    - flights_per_week: weekly count per (airline_iata, origin_iata, dest_iata).
    - low_recurrence: weekly count <= 3 (proxy for non-scheduled/charter).

### Signals and Weights

- Cargo leak
    - cargo_letter (+3)
    - is_freighter_type_guess (+4)
    - is_night_bank (+1)
    - involves_cargo_hub (+1)
- Airline charter/positioning
    - low_recurrence (<=3/week) (+3)
    - origin_equals_dest (+4)
    - involves_mro_storage (+3)
    - missing_tailnumber (+2)
    - both_terminals_missing (+1)
    - both_gates_missing (+1)
    - is_night_bank (when cargo score=0) (+1)

### Thresholds and Confidence

- Category thresholds
    - cargo_threshold = 5
    - charter_threshold = 5
- Confidence mapping
    - High: score ≥ 7 or includes any strong signal (is_freighter_type_guess OR origin_equals_dest OR
      involves_mro_storage) plus ≥1 other signal
    - Medium: threshold ≤ score < 7
    - Low: tied or exactly at threshold with conflict

## Test Plan

- Required unit tests (file names, scenarios)
- Integration/manual checks
- Acceptance test data or fixtures

## Deliverables

- Code changes
- Tests
- Documentation updates (README, AGENTS.md, etc.)

## Additional Guidance

- Edge cases to handle
- What to avoid (e.g., “Don’t refactor module X”)
- Format for final summary (bullets, sections)

## Dependencies

- Internal: other features, refactors, tech debt.
- External: datasets, MCP agents, approvals, infra tasks.
- Unit tests: planned modules/files.
- Integration tests: scenarios or fixtures.
- QA checklist/manual validation steps.
- Metrics to monitor post-release.