from pathlib import Path

from src.admin.update_flights_commercial_view import (
    build_view_sql,
    load_airline_codes,
    quote_literal,
)


def test_load_airline_codes_dedup_upper_ignores_blanks(airlines_sample_path: Path) -> None:
    codes = load_airline_codes(airlines_sample_path)

    assert codes == ["FDX", "NCA", "NULL"]


def test_quote_literal_escapes_single_quotes() -> None:
    assert quote_literal("ACME'O") == "'ACME''O'"


def test_build_view_sql_includes_blocklist_and_predicates() -> None:
    sql = build_view_sql(["nca", "FDX", "Null"])  # mixed case input

    # Blocklist normalized to uppercase and properly quoted
    assert "UPPER(COALESCE(f.airline_icao, '')) IN ('NCA','FDX','NULL')" in sql

    # Housekeeping predicates exist
    assert "UPPER(COALESCE(f.dest_iata, '')) = 'NULL'" in sql
    assert "COALESCE(f.airline, '') ILIKE 'Private owner'" in sql

    # B744 exception clause present
    assert "COALESCE(f.aircraft_code, '') = 'B744'" in sql


def test_build_view_sql_without_blocklist_omits_clause() -> None:
    sql = build_view_sql([])
    assert "UPPER(COALESCE(f.airline_icao" not in sql
