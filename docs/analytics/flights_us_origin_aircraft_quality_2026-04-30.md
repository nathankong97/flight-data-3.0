# `flights` US-Origin Aircraft Data Quality Report - 2026-04-30

## Scope

- Database: `flight_data`
- Core table: `public.flights`
- Reference table: `public.aircrafts`
- Departure filter:
  - Joined `public.flights.origin_iata` to `public.airports.iata`
  - Included `airports.country IN ('United States', 'Puerto Rico', 'Guam')`
- Rows analyzed: `5,166,241`
- Main columns reviewed:
  - `aircraft_code`
  - `aircraft_reg`
  - `aircraft_text`
  - Related context: `status_detail`, `airline`, `airline_iata`, `owner_name`

## Executive Conclusion

- `aircraft_code` is reliable and broadly populated.
- `aircraft_reg` is highly useful for completed/departed flights, but should not be required for open, future, or unresolved flights.
- Missing `aircraft_reg` is mostly an unresolved-feed signal, not mainly a cancellation signal.
- Missing `aircraft_reg` on `Departed` rows is rare and should be treated as a quality issue.
- Missing `aircraft_reg` on `Canceled` rows is expected enough that it should not be treated as a failure.
- For passenger-focused analysis, use `aircraft_code` together with airline/owner/status signals to filter likely cargo, freighter, business, and private flights.

## Overall Aircraft Field Coverage

| Metric | Value |
|---|---:|
| Rows analyzed | `5,166,241` |
| Distinct `aircraft_code` values | `635` |
| Distinct `aircraft_reg` values | `42,061` |
| Missing `aircraft_code` | `0.30%` |
| Missing `aircraft_reg` | `4.38%` |
| Missing `aircraft_text` | `4.40%` |
| Both `aircraft_code` and `aircraft_reg` missing | `0.28%` |

## Is `aircraft_reg` Useful?

- Yes, especially for completed flights.
- `aircraft_reg` gives tail-level identity, which enables:
  - Repeat-aircraft analysis
  - Utilization analysis
  - Tail-level delay behavior
  - Detecting private/business aviation patterns
  - Spotting aircraft reuse and route patterns
- It should be considered an enrichment field, not a universal required field.
- For open statuses, missing registration is common because the actual aircraft may not have been assigned or captured by the feed yet.

## Registration Patterns

| Registration pattern | Rows | Distinct registrations | Percent |
|---|---:|---:|---:|
| US N-number | `4,731,716` | `36,271` | `91.59%` |
| Missing | `226,456` | `0` | `4.38%` |
| Foreign hyphenated | `188,689` | `5,280` | `3.65%` |
| Compact alphanumeric | `11,304` | `283` | `0.22%` |
| Other | `8,076` | `227` | `0.16%` |

Interpretation:

- Registration data is mostly US N-numbers, which is expected for US-origin data.
- Foreign registrations are present and useful for international carriers or non-US aircraft operating from US airports.
- Missing registrations are a minority overall, but their distribution is highly status-dependent.

## Missing Aircraft Fields By Status

| Status | Rows | Missing `aircraft_code` | Missing `aircraft_reg` | Both missing | Both real timestamps missing |
|---|---:|---:|---:|---:|---:|
| `Departed` | `4,797,553` | `0.02%` | `0.00%` | `0.00%` | `0.00%` |
| `Estimated` | `223,056` | `6.26%` | `68.76%` | `6.18%` | `100.00%` |
| `Canceled` | `92,444` | `0.01%` | `34.34%` | `0.01%` | `100.00%` |
| `Unknown` | `51,171` | `1.32%` | `77.63%` | `1.30%` | `100.00%` |
| `Scheduled` | `2,017` | `0.05%` | `74.57%` | `0.05%` | `100.00%` |

Key interpretation:

- `Departed` rows almost always have `aircraft_reg`.
- `Estimated`, `Unknown`, and `Scheduled` rows often lack `aircraft_reg`.
- The same unresolved statuses also have both `real_dep` and `real_arr` missing, so missing registration aligns with open/incomplete flight records.
- `Canceled` has meaningful missing registration, but that is operationally reasonable because the flight did not operate.

## Missing `aircraft_reg`: Is It Mostly Canceled?

No. Missing registration is not mainly a cancellation pattern.

| Status | Missing `aircraft_reg` rows |
|---|---:|
| `Estimated` | `153,370` |
| `Unknown` | `39,724` |
| `Canceled` | `31,741` |
| `Scheduled` | `1,504` |
| `Departed` | `117` |

Conclusion:

- Missing `aircraft_reg` is mostly an unresolved/open-feed signal.
- `Canceled` contributes some missing registrations, but it is not the dominant cause.
- Missing `aircraft_reg` on `Departed` is rare and should be flagged.

## Future Versus Past/Open Status Pattern

| Schedule bucket | Status | Rows | Missing `aircraft_reg` | Missing `aircraft_code` |
|---|---|---:|---:|---:|
| Future | `Estimated` | `1,170` | `18.63%` | `0.51%` |
| Future | `Scheduled` | `458` | `24.67%` | `0.00%` |
| Past/current | `Departed` | `4,797,553` | `0.00%` | `0.02%` |
| Past/current | `Estimated` | `221,886` | `69.02%` | `6.29%` |
| Past/current | `Canceled` | `92,444` | `34.34%` | `0.01%` |
| Past/current | `Unknown` | `51,171` | `77.63%` | `1.32%` |
| Past/current | `Scheduled` | `1,559` | `89.22%` | `0.06%` |

Interpretation:

- Future scheduled or estimated flights can legitimately be missing aircraft registration.
- Past/current `Estimated`, `Scheduled`, and `Unknown` rows with missing registration are stale incomplete candidates.
- Past/current `Departed` rows are extremely strong for aircraft registration quality.

## Aircraft Reference Table Coverage

The local `public.aircrafts` table has:

- `246` reference rows
- `name`
- `iata_code`
- `icao_code`

Coverage against `flights.aircraft_code`:

| Metric | Value |
|---|---:|
| Rows with `aircraft_code` | `5,150,824` |
| Row match by ICAO code | `92.33%` |
| Row match by IATA code | `0.77%` |
| Row match by either IATA or ICAO | `93.09%` |
| Distinct aircraft codes | `635` |
| Distinct aircraft codes matched | `226` |

Interpretation:

- The reference table covers high-volume commercial aircraft well by row count.
- It does not cover many distinct lower-volume codes.
- Many unmatched codes appear to be business aircraft, general aviation, or freighter/special variants.
- Do not treat every unmatched `aircraft_code` as bad data.

## High-Volume Aircraft Codes

| Aircraft code | Rows | Missing `aircraft_reg` | Cargo/freighter signal | Business/private signal |
|---|---:|---:|---:|---:|
| `B738` | `531,458` | `0.23%` | `0.22%` | `0.02%` |
| `E75L` | `466,176` | `1.12%` | `0.00%` | `0.00%` |
| `B38M` | `401,151` | `0.12%` | `0.00%` | `0.00%` |
| `B737` | `312,028` | `0.21%` | `0.29%` | `0.00%` |
| `A321` | `281,454` | `1.17%` | `0.20%` | `0.00%` |
| `A320` | `251,280` | `1.02%` | `0.00%` | `0.00%` |
| `B739` | `220,332` | `0.18%` | `0.00%` | `0.00%` |
| `CRJ9` | `207,589` | `0.45%` | `0.00%` | `0.00%` |
| `A21N` | `200,036` | `0.44%` | `0.00%` | `0.00%` |
| `A319` | `178,433` | `0.22%` | `0.00%` | `0.00%` |

Interpretation:

- Common passenger aircraft types have very low missing-registration rates.
- `aircraft_code` is reliable for passenger fleet grouping.

## Passenger And Non-Passenger Signals

Simple signal rules used:

- Cargo/freighter signal:
  - Airline or owner contains `cargo` or `freight`
  - Aircraft code/text suggests freighter type
  - Known freighter-style codes such as `77F`, `74F`, `74N`, `73F`, etc.
- Business/private signal:
  - Airline/operator names such as NetJets, Flexjet, Private owner, VistaJet, Solairus, Executive Jet, etc.
  - Flight number prefixes such as `EJA`, `LXJ`, `NJE`, `VJA`, etc.
  - Business aircraft type patterns such as Citation, Gulfstream, Learjet, Falcon, Phenom, PC-12, King Air, etc.

Overall passenger/non-passenger signal summary:

| Signal | Percent of rows |
|---|---:|
| Cargo/freighter signal | `3.12%` |
| Business/private signal | `7.74%` |
| No obvious non-passenger signal | `89.15%` |

Among rows missing `aircraft_reg`:

| Signal | Percent of missing-registration rows |
|---|---:|
| Cargo/freighter signal | `10.61%` |
| Business/private signal | `20.02%` |

Interpretation:

- Missing registration is disproportionately associated with non-passenger-like records.
- Passenger-like records still have some missing registration, but at a lower rate.

## Passenger-Like Quality After Removing Obvious Non-Passenger Signals

Passenger-like definition for this check:

- Not cargo/freighter signal
- Not business/private signal

| Metric | Value |
|---|---:|
| Passenger-like rows | `4,605,701` |
| Missing `aircraft_code` | `0.14%` |
| Missing `aircraft_reg` | `3.41%` |
| Canceled | `2.00%` |
| Open status (`Estimated`, `Scheduled`, `Unknown`) | `4.13%` |

Interpretation:

- Aircraft metadata quality is better after removing obvious cargo/business/private traffic.
- Passenger-like analysis should still account for open and canceled statuses.

## Top Missing-Registration Airlines

| Airline IATA | Airline | Missing `aircraft_reg` rows | Canceled | Open status |
|---|---|---:|---:|---:|
| `(missing)` | NetJets | `30,550` | `0.01%` | `99.99%` |
| `AS` | Alaska Airlines | `19,000` | `1.61%` | `98.39%` |
| `(missing)` | `(missing)` | `15,465` | `0.05%` | `99.88%` |
| `DL` | Delta Air Lines | `10,970` | `85.94%` | `14.06%` |
| `AA` | American Airlines | `10,930` | `82.44%` | `17.56%` |
| `9X` | Southern Airways Express | `7,056` | `0.00%` | `100.00%` |
| `5X` | UPS | `5,413` | `0.00%` | `99.93%` |
| `(missing)` | Flexjet | `4,818` | `0.00%` | `100.00%` |
| `FX` | FedEx | `4,502` | `0.00%` | `99.82%` |
| `OO` | SkyWest Airlines | `4,491` | `0.00%` | `100.00%` |

Interpretation:

- Missing registration for business/private operators is mostly open/unresolved status.
- Missing registration for some major passenger airlines is heavily cancellation-related.
- Missing registration for cargo operators is mostly open/unresolved status.

## Unmatched Aircraft Codes In Reference Table

High-volume unmatched codes include:

| Aircraft code | Rows | Cargo/freighter signal | Business/private signal |
|---|---:|---:|---:|
| `C68A` | `37,369` | `0.00%` | `99.18%` |
| `E45X` | `32,648` | `0.00%` | `0.00%` |
| `CL35` | `25,615` | `0.00%` | `87.48%` |
| `C700` | `15,418` | `0.00%` | `99.45%` |
| `BE20` | `12,554` | `0.05%` | `94.85%` |
| `C402` | `10,708` | `0.00%` | `0.28%` |
| `B350` | `9,753` | `0.00%` | `92.28%` |
| `CNC` | `9,227` | `0.00%` | `0.00%` |
| `C560` | `8,063` | `0.00%` | `93.84%` |
| `BE40` | `7,382` | `0.00%` | `94.68%` |
| `77F` | `4,925` | `100.00%` | `0.00%` |
| `74F` | `3,733` | `100.00%` | `0.00%` |
| `74N` | `2,181` | `100.00%` | `0.00%` |

Interpretation:

- The local reference table is incomplete for many non-mainline aircraft types.
- Many unmatched aircraft codes are useful signals rather than bad data.
- Examples:
  - `C68A`, `CL35`, `C700`, `BE20`, `B350`, `C560`, `BE40` are strong business/private indicators in this dataset.
  - `77F`, `74F`, and `74N` are strong freighter indicators.

## Cleaning Recommendations

- Keep `aircraft_code`:
  - It is highly populated.
  - It is useful for aircraft family/type grouping.
  - It is useful for passenger versus freighter/business filtering.

- Keep `aircraft_reg`:
  - It is very useful for completed flights.
  - It should be used for tail-level analysis only when present.
  - It should not be required for open or future records.

- Treat missing `aircraft_reg` by status:
  - `Departed`: flag as rare aircraft-data quality issue.
  - `Estimated`, `Scheduled`, `Unknown`: treat as expected for open records; if old, classify as stale incomplete.
  - `Canceled`: treat as acceptable/expected.

- Improve passenger filtering:
  - Exclude obvious cargo/freighter signals when analyzing passenger service.
  - Exclude obvious business/private signals when analyzing scheduled commercial passenger service.
  - Use `aircraft_code`, `airline`, `owner_name`, and `flight_num` together; no single column is enough.

- Improve reference data:
  - Do not rely only on `public.aircrafts` to validate `aircraft_code`.
  - Add supplemental mappings for common unmatched business aircraft, general aviation, and freighter codes.
  - Keep unmatched code reporting, but do not automatically classify unmatched codes as invalid.

## Suggested Derived Fields

```sql
CASE
  WHEN NULLIF(btrim(aircraft_code), '') IS NULL THEN 'missing_code'
  ELSE 'present_code'
END AS aircraft_code_quality
```

```sql
CASE
  WHEN NULLIF(btrim(aircraft_reg), '') IS NULL THEN 'missing_reg'
  WHEN upper(btrim(aircraft_reg)) IN ('N/A', 'NA', 'NULL', '-') THEN 'placeholder_reg'
  ELSE 'present_reg'
END AS aircraft_reg_quality
```

```sql
CASE
  WHEN status_detail ILIKE 'Departed%'
       AND NULLIF(btrim(aircraft_reg), '') IS NULL
    THEN 'departed_missing_reg'
  WHEN status_detail ILIKE 'Canceled%'
       AND NULLIF(btrim(aircraft_reg), '') IS NULL
    THEN 'canceled_missing_reg_expected'
  WHEN (
      status_detail ILIKE 'Estimated%'
      OR status_detail ILIKE 'Scheduled%'
      OR status_detail ILIKE 'Unknown%'
    )
    AND NULLIF(btrim(aircraft_reg), '') IS NULL
    THEN 'open_missing_reg'
  ELSE 'aircraft_reg_ok_or_not_required'
END AS aircraft_reg_quality_status
```

## Final Simple Rule

- For completed passenger flight analytics, require:
  - Clean completed-flight status/timestamps
  - `aircraft_code` present
  - Prefer `aircraft_reg` present
  - No obvious cargo/freighter signal
  - No obvious business/private signal

- For live operational dashboards:
  - Allow missing `aircraft_reg` on future or recently open flights.
  - Do not interpret missing registration as cancellation by itself.

- For historical quality cleanup:
  - Missing `aircraft_reg` plus old `Estimated`, `Scheduled`, or `Unknown` is a stale incomplete signal.
  - Missing `aircraft_reg` plus `Departed` is a rare quality exception.
  - Missing `aircraft_reg` plus `Canceled` is acceptable.
