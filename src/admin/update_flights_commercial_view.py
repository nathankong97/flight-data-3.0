import argparse
import os
from pathlib import Path
from typing import List

import psycopg


def load_airline_codes(file_path: Path) -> List[str]:
    """Load ICAO airline codes from data/filtered_airlines.txt.

    Args:
        file_path: Path to data/filtered_airlines.txt.

    Returns:
        A list of uppercased, deduplicated airline ICAO codes.
    """
    seen = set()
    codes: List[str] = []
    with file_path.open("r", encoding="utf-8") as f:
        for raw in f:
            code = raw.strip().upper()
            if not code:
                continue
            if code in seen:
                continue
            seen.add(code)
            codes.append(code)
    return codes


def quote_literal(value: str) -> str:
    """Return a SQL single-quoted literal.

    Args:
        value: Text value to quote.

    Returns:
        Safely single-quoted SQL literal with quotes escaped.
    """
    return "'" + value.replace("'", "''") + "'"


def build_view_sql(blocklist_codes: List[str]) -> str:
    """Construct the CREATE OR REPLACE VIEW SQL including the airline blocklist.

    Args:
        blocklist_codes: Uppercased ICAO airline codes to exclude.

    Returns:
        Complete SQL statement string to recreate the view.
    """
    in_list = ",".join(quote_literal(c) for c in blocklist_codes) if blocklist_codes else None

    blocklist_clause = (
        f" OR UPPER(COALESCE(f.airline_icao, '')) IN ({in_list})\n" if in_list else ""
    )

    sql = f"""
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

    -- Airline ICAO blocklist from data/filtered_airlines.txt
    {blocklist_clause}

    -- Non-commercial/unknown housekeeping from legacy rules
    OR f.dest_iata IS NULL
    OR UPPER(COALESCE(f.dest_iata, '')) = 'NULL'
    OR (f.airline IS NULL AND f.airline_icao IS NULL)
    OR COALESCE(f.airline, '') ILIKE 'Private owner'
);

COMMENT ON VIEW public.flights_commercial IS 'Filtered commercial passenger flights including dynamic airline blocklist.';
"""
    return sql


def main() -> None:
    """Entry point: update the view using data/filtered_airlines.txt and DATABASE_URL."""
    parser = argparse.ArgumentParser(
        description="Update public.flights_commercial view using data/filtered_airlines.txt"
    )
    parser.add_argument(
        "--database-url",
        dest="database_url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection string. Defaults to env DATABASE_URL.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL is required (or pass --database-url)")

    file_path = Path("data/filtered_airlines.txt")
    if not file_path.exists():
        raise SystemExit(f"Airlines file not found: {file_path}")

    codes = load_airline_codes(file_path)
    sql = build_view_sql(codes)

    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()

    print(
        f"Updated view public.flights_commercial with {len(codes)} airline ICAO code(s) from {file_path}."
    )


if __name__ == "__main__":
    main()
