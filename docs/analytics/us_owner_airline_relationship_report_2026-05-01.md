# US Owner vs Airline Relationship Analysis

Date: 2026-05-01

## Summary

This report analyzes the relationship between the `owner_*` and `airline_*` fields in
`public.flights` for US-origin flights. The goal is to determine which fields are more
reliable for identifying airlines, and to distinguish real operating-vs-marketed airline
relationships from missing data, display-name differences, and cases that need review.

The main conclusion is:

- Use `airline_*` for public, marketed, route, schedule, and commercial airline identity.
- Use `owner_*` for actual aircraft owner or operating carrier identity.
- Do not treat every owner/airline mismatch as a valid operating-vs-marketed relationship.
  Most mismatch rows are legitimate regional or feeder relationships, but many distinct
  mismatch pairs are missing-data or display-name cases.

## Data Scope

US-origin flights were selected by joining:

```sql
public.flights.origin_iata = public.airports.iata
```

and filtering:

```sql
public.airports.country = 'United States'
```

Dataset size:

| Metric | Value |
|---|---:|
| US-origin flight rows | 5,115,261 |
| Distinct `flight_id` values | 5,115,261 |
| Distinct US origin airports | 131 |
| Earliest scheduled departure | 2025-10-27 10:05:00-04 |
| Latest scheduled departure | 2026-05-01 10:52:00-04 |
| Earliest ingest `created_at` | 2025-10-28 22:00:03.169056-04 |
| Latest ingest `created_at` | 2026-04-29 22:57:28.982996-04 |

## Supporting Artifacts

The full mismatch outputs are stored as CSV files:

- `docs/analytics/us_owner_airline_mismatch_pairs_2026-05-01.csv`
  - Full list of 1,696 distinct owner/airline mismatch pairs.
- `docs/analytics/us_owner_airline_mismatch_review_needed_2026-05-01.csv`
  - Review-focused subset excluding obvious regional/feeder and cargo/feeder patterns.

PostgreSQL reported `COPY 1696` for the full mismatch export and `COPY 1584` for the
review-focused export. The filesystem line counts are slightly higher because some CSV
fields can contain embedded line breaks.

## Field Completeness

`airline_*` fields are generally more complete than `owner_*` fields for US-origin data.

| Field | Present rows | Coverage |
|---|---:|---:|
| `airline` | 4,885,142 | 95.50% |
| `airline_icao` | 4,880,011 | 95.40% |
| `airline_iata` | 4,570,424 | 89.35% |
| `owner_name` | 4,629,775 | 90.51% |
| `owner_icao` | 4,629,775 | 90.51% |
| `owner_iata` | 4,376,384 | 85.56% |

Interpretation:

- `airline_icao` and `airline` have the best coverage.
- `airline_iata` has lower coverage than `airline_icao`, but it is highly useful for
  schedule and flight-number matching.
- `owner_iata` has the weakest coverage among the six identity fields.

## Owner vs Airline Agreement

Owner and airline fields frequently agree, but they also diverge at meaningful scale.

| Comparison | Both present | Same | Different |
|---|---:|---:|---:|
| IATA | 4,374,554 | 3,205,428 | 1,169,126 |
| ICAO | 4,628,531 | 3,439,395 | 1,189,136 |
| Name | 4,628,556 | 3,226,830 | 1,401,726 |

There are 1,659,540 rows with at least one owner/airline mismatch after normalizing blank
values. These rows collapse to 1,696 distinct owner/airline mismatch pairs.

## Mismatch Categories

The mismatch pairs were classified using a conservative rule set:

- `likely_regional_or_feeder_brand`: airline label contains terms such as Express,
  Connection, Eagle, Feeder, Horizon, or SkyWest.
- `likely_cargo_or_feeder_brand`: airline or owner label contains cargo/freight markers
  such as Cargo, Freight, FedEx, UPS, Amazon, or Empire.
- `owner_missing_airline_present`: all owner identity fields are missing but airline
  identity exists.
- `owner_present_airline_missing`: owner identity exists but all airline identity fields
  are missing.
- `same_code_name_or_brand_differs`: owner and airline share IATA or ICAO code, but the
  display name differs.
- `partial_code_missing`: both sides have some identity data, but at least one relevant
  code is missing.
- `other_both_present_mismatch_review`: both sides are present and differ, and the pattern
  is not caught by the feeder/cargo/name rules.

Classification results:

| Classification | Rows | Distinct pairs |
|---|---:|---:|
| likely regional/feeder brand | 1,107,851 | 47 |
| owner missing, airline present | 256,586 | 782 |
| same code, name/brand differs | 180,444 | 715 |
| other both-present mismatch, needs review | 77,093 | 59 |
| likely cargo/feeder brand | 35,792 | 65 |
| owner present, airline missing | 1,219 | 14 |
| partial code missing | 555 | 14 |

Rows that are likely legitimate operating-vs-marketed relationships:

| Group | Rows |
|---|---:|
| likely regional/feeder brand | 1,107,851 |
| likely cargo/feeder brand | 35,792 |
| Total likely legitimate operator/brand rows | 1,143,643 |

This is about 68.9% of all mismatch rows. That is why "mostly real
operating-vs-marketed relationships" is accurate at the row level, but not at the
distinct-pair level.

At the distinct-pair level, many rows are missing-data or display-name cases:

| Group | Distinct pairs |
|---|---:|
| owner missing, airline present | 782 |
| same code, name/brand differs | 715 |
| owner present, airline missing | 14 |
| partial code missing | 14 |

## Top Legitimate Regional or Feeder Patterns

The largest mismatch pairs are mostly regional carriers operating under major airline
brands.

| Owner/operator | Marketed airline | Rows |
|---|---|---:|
| Envoy `MQ/ENY` | American Eagle `AA/AAL` | 134,956 |
| SkyWest Airlines `OO/SKW` | United Express `UA/UAL` | 122,015 |
| PSA Airlines `OH/JIA` | American Eagle `AA/AAL` | 109,719 |
| Endeavor Air `9E/EDV` | Delta Connection `DL/DAL` | 108,891 |
| SkyWest Airlines `OO/SKW` | Delta Connection `DL/DAL` | 105,280 |
| Republic Airways `YX/RPA` | American Eagle `AA/AAL` | 83,846 |
| SkyWest Airlines `OO/SKW` | American Eagle `AA/AAL` | 62,664 |
| Piedmont Airlines `PT/PDT` | American Eagle `AA/AAL` | 59,626 |
| Republic Airways `YX/RPA` | United Express `UA/UAL` | 54,668 |
| Republic Airways `YX/RPA` | Delta Connection `DL/DAL` | 49,782 |

Interpretation:

- In these cases, `owner_*` identifies the actual operator or aircraft owner.
- `airline_*` identifies the public-facing marketed airline brand.
- For passenger route analysis, `airline_*` is usually the correct grouping.
- For operational analysis, `owner_*` is valuable and should be preserved.

## Cases That Are Not Automatically Real Operator/Brand Relationships

### Owner missing, airline present

There are 256,586 rows across 782 distinct pairs where airline identity exists but owner
identity is missing.

Top examples:

| Owner | Airline | Rows |
|---|---|---:|
| missing | NetJets `EJA` | 30,656 |
| missing | Alaska Airlines `AS/ASA` | 19,231 |
| missing | Delta Air Lines `DL/DAL` | 18,289 |
| missing | American Airlines `AA/AAL` | 11,073 |
| missing | United Airlines `UA/UAL` | 8,425 |
| missing | Spirit Airlines `NK/NKS` | 7,541 |
| missing | United Express `UA/UAL` | 7,099 |
| missing | Southern Airways Express `9X/FDY` | 7,078 |

Interpretation:

- These are not owner/airline relationships. They are owner-field missingness.
- For airline identity, use `airline_*`.
- For owner/operator analysis, these rows should be flagged as incomplete.

### Same code but display name or brand differs

There are 180,444 rows across 715 distinct pairs where at least one code matches but the
name or brand text differs.

Interpretation:

- These are usually not meaningful code-level disagreements.
- They often represent spelling, display-name, branding, punctuation, or label variants.
- Code fields should be preferred over name fields for identity resolution.

### Other both-present mismatches that need review

There are 77,093 rows across 59 distinct pairs where both owner and airline are present,
the codes differ, and the pair is not clearly classified as regional/feeder or cargo/feeder.

Top examples:

| Owner/operator | Airline | Rows | Notes |
|---|---|---:|---|
| Alaska Airlines `AS/ASA` | Hawaiian Airlines `HA/HAL` | 51,855 | Large, real-world brand/corporate transition context; should not be treated as generic regional feed. |
| SkyWest Airlines `OO/SKW` | Alaska Airlines `AS/ASA` | 5,589 | Likely operational feed, but airline label is Alaska Airlines rather than Alaska SkyWest. |
| Porter Airlines Canada `PD/POE` | Porter `P3/PTR` | 3,953 | Possible code/name system inconsistency or brand mapping issue. |

Interpretation:

- These need explicit business rules or manual validation.
- Some are likely legitimate, but the current broad text rules should not silently classify them.
- This bucket is the best candidate for a curated mapping table.

### Owner present, airline missing

There are 1,219 rows across 14 distinct pairs where owner identity exists but airline
identity is missing.

Interpretation:

- These rows should not be used for marketed airline analysis without fallback logic.
- For operational analysis, `owner_*` may still be useful.

### Partial code missing

There are 555 rows across 14 distinct pairs where both sides contain some identity data,
but one or more key code fields are missing.

Interpretation:

- These rows are ambiguous.
- Prefer the complete side for identity classification.
- Keep a data-quality flag so downstream analytics can exclude or inspect them.

## Flight Number Prefix Check

For rows with a parseable two-character flight-number prefix:

| Metric | Rows |
|---|---:|
| Rows with prefix and at least one IATA field | 4,562,906 |
| Rows with `airline_iata` | 4,561,119 |
| `airline_iata` matches prefix | 4,441,789 |
| Rows with `owner_iata` | 4,367,869 |
| `owner_iata` matches prefix | 3,237,275 |

Match rates:

| Field | Match rate |
|---|---:|
| `airline_iata` vs flight-number prefix | 97.38% |
| `owner_iata` vs flight-number prefix | 74.11% |

Interpretation:

- `airline_iata` aligns much better with the public flight number.
- This strongly supports using `airline_iata` for marketed airline, schedule, and route
  analysis.
- `owner_iata` is not reliable as a replacement for marketed carrier identity.

## Recommended Reliability Hierarchy

For marketed airline identity:

1. `airline_icao`
2. `airline_iata`
3. `airline`

For public schedule and flight-number matching:

1. `airline_iata`
2. `airline_icao`
3. `airline`

For actual aircraft owner or operating carrier identity:

1. `owner_icao`
2. `owner_iata`
3. `owner_name`

For display/reporting:

1. Resolve by code first.
2. Use name fields only as labels.
3. Normalize name variants through a mapping table rather than treating raw names as
   stable identities.

## Recommended Downstream Rules

### Preserve both identities

Do not overwrite `owner_*` with `airline_*`, or vice versa. They answer different
questions:

- `airline_*`: who the passenger/public sees.
- `owner_*`: who owns or operates the aircraft.

### Add a relationship classification field

For analytics, add a derived field such as `operator_marketer_relationship_type` with
values like:

- `same_carrier`
- `regional_feeder`
- `cargo_feeder`
- `same_code_name_variant`
- `owner_missing`
- `airline_missing`
- `partial_code_missing`
- `review_needed`

### Create a curated mapping table

The `other_both_present_mismatch_review` bucket should be reviewed and converted into
explicit mappings where appropriate. Suggested table shape:

```sql
CREATE TABLE public.airline_owner_relationships (
    owner_iata TEXT,
    owner_icao TEXT,
    owner_name TEXT,
    airline_iata TEXT,
    airline_icao TEXT,
    airline_name TEXT,
    relationship_type TEXT NOT NULL,
    confidence TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

This would make the classification reproducible instead of relying only on text patterns.

### Use data-quality flags

Recommended boolean flags:

- `owner_identity_missing`
- `airline_identity_missing`
- `owner_airline_code_mismatch`
- `owner_airline_name_mismatch`
- `same_code_name_variant`
- `relationship_review_needed`

These flags would let downstream reports distinguish true airline relationships from data
quality issues.

## Final Conclusion

`airline_*` is more reliable for airline, route, schedule, and commercial passenger
analysis in the US-origin dataset. This is supported by both higher field completeness and
the strong flight-number-prefix match rate for `airline_iata`.

`owner_*` is still important, but it should be interpreted as owner/operator identity, not
as a substitute for public airline identity.

The earlier statement that mismatches are "mostly real operating-vs-marketed airline
relationships" is correct by row volume, because about 68.9% of mismatch rows are likely
regional/feeder or cargo/feeder relationships. It is not correct for every mismatch pair.
There are substantial missing-owner, name-variant, and review-needed categories that should
be handled separately.
