# Feature Request: flights_commercial view improvement

## Context

- Currently, the file `update_flights_commercial_view.py` accepted `data/filtered_airlines.txt`, which is great.
However, I explored another filter, that need file load with py file.
- will add another txt file filter: `data/filtered_airlines_name.txt`.
- `filtered_airlines_name.txt` is mapping with column `airline` in table `flights`.

## Desired Outcome

- Pass the unit test
- Provide proper solution to accommodate new filter file. 
- Review "cargo" keyword to make sure it is correct.

## Implementation Notes

- Target files or directories to modify/create (`src/...`, `tests/...`):
  - `src/admin/update_flights_commercial_view.py`
- Coding style expectations follow AGENTS.md

## Test Plan

- Required unit tests passed, 
- No need for new unit test or integration test.