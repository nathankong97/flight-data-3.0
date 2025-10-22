"""Transform FlightRadar API responses into structured flight records."""

from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Optional


DATA_PATH: Iterable[str] = (
    "result",
    "response",
    "airport",
    "pluginData",
    "schedule",
    "departures",
    "data",
)


def _nested_get(source: Any, path: Iterable[str]) -> Any:
    current = source
    for key in path:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current


def _to_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "t", "1", "yes", "y"}:
            return True
        if lowered in {"false", "f", "0", "no", "n"}:
            return False
    return None


def _normalize_tz_offset(value: Any) -> Optional[int]:
    """Return timezone offset in hours.

    The upstream payload may report offsets as hours (e.g., 9, -7) or as seconds
    (e.g., 32400, -25200). Convert seconds to whole hours to align with the
    SMALLINT schema and test expectations.
    """
    num = _to_optional_int(value)
    if num is None:
        return None
    if abs(num) > 24:
        # Treat as seconds; convert to hours using integer division.
        # This preserves sign and yields whole-hour offsets used in this project.
        return int(num / 3600)
    return num


def _to_optional_str(value: Any) -> Optional[str]:
    """Return a trimmed string if non-empty; otherwise None."""
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s or None
    try:
        return str(value)
    except Exception:  # pragma: no cover - defensive
        return None


@dataclass(frozen=True)
class FlightRecord:
    """Structured representation of a scheduled or actual flight."""

    flight_num: Optional[str]
    status_detail: Optional[str]
    aircraft_code: Optional[str]
    aircraft_text: Optional[str]
    aircraft_reg: Optional[str]
    aircraft_co2: Optional[float]
    aircraft_restricted: Optional[bool]
    owner_name: Optional[str]
    owner_iata: Optional[str]
    owner_icao: Optional[str]
    airline: Optional[str]
    airline_iata: Optional[str]
    airline_icao: Optional[str]
    origin_iata: Optional[str]
    origin_offset: Optional[int]
    origin_offset_abbr: Optional[str]
    origin_offset_dst: Optional[bool]
    origin_terminal: Optional[str]
    origin_gate: Optional[str]
    dest_iata: Optional[str]
    dest_icao: Optional[str]
    dest_offset: Optional[int]
    dest_offset_abbr: Optional[str]
    dest_offset_dst: Optional[bool]
    dest_terminal: Optional[str]
    dest_gate: Optional[str]
    sched_dep: Optional[int]
    sched_arr: Optional[int]
    real_dep: Optional[int]
    real_arr: Optional[int]
    origin_lat: Optional[float]
    origin_lng: Optional[float]
    dest_lat: Optional[float]
    dest_lng: Optional[float]
    ingest_run_id: Optional[str] = None

    def with_ingest_run(self, ingest_run_id: str) -> "FlightRecord":
        return replace(self, ingest_run_id=ingest_run_id)

    def to_db_params(self, ingest_run_id: Optional[str] = None) -> Dict[str, Any]:
        run_id = ingest_run_id or self.ingest_run_id
        if not run_id:
            raise ValueError("ingest_run_id must be provided")
        return {
            "ingest_run_id": run_id,
            "flight_num": self.flight_num,
            "status_detail": self.status_detail,
            "aircraft_code": self.aircraft_code,
            "aircraft_text": self.aircraft_text,
            "aircraft_reg": self.aircraft_reg,
            "aircraft_co2": self.aircraft_co2,
            "aircraft_restricted": self.aircraft_restricted,
            "owner_name": self.owner_name,
            "owner_iata": self.owner_iata,
            "owner_icao": self.owner_icao,
            "airline": self.airline,
            "airline_iata": self.airline_iata,
            "airline_icao": self.airline_icao,
            "origin_iata": self.origin_iata,
            "origin_offset": self.origin_offset,
            "origin_offset_abbr": self.origin_offset_abbr,
            "origin_offset_dst": self.origin_offset_dst,
            "origin_terminal": self.origin_terminal,
            "origin_gate": self.origin_gate,
            "dest_iata": self.dest_iata,
            "dest_icao": self.dest_icao,
            "dest_offset": self.dest_offset,
            "dest_offset_abbr": self.dest_offset_abbr,
            "dest_offset_dst": self.dest_offset_dst,
            "dest_terminal": self.dest_terminal,
            "dest_gate": self.dest_gate,
            "sched_dep": self.sched_dep,
            "sched_arr": self.sched_arr,
            "real_dep": self.real_dep,
            "real_arr": self.real_arr,
            "origin_lat": self.origin_lat,
            "origin_lng": self.origin_lng,
            "dest_lat": self.dest_lat,
            "dest_lng": self.dest_lng,
        }


def extract_departure_records(
    payload: Mapping[str, Any],
    origin_code: str,
    *,
    coordinates: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> List[FlightRecord]:
    """Parse FlightRadar departures payload into FlightRecord objects."""

    departures = _nested_get(payload, DATA_PATH) or []
    if not isinstance(departures, list):
        return []

    coord_lookup = coordinates or {}
    origin_upper = origin_code.upper()
    origin_coords = coord_lookup.get(origin_upper, {})
    origin_lat = _to_optional_float(origin_coords.get("lat"))
    origin_lng = _to_optional_float(origin_coords.get("lng"))

    records: List[FlightRecord] = []
    for item in departures:
        # Prefer published flight number; if absent (e.g., cancelled/private), use a placeholder
        flight_num = _to_optional_str(
            _nested_get(item, ["flight", "identification", "number", "default"])
        ) or "-"

        record = FlightRecord(
            flight_num=flight_num,
            status_detail=_nested_get(item, ["flight", "status", "text"]),
            aircraft_code=_nested_get(item, ["flight", "aircraft", "model", "code"]),
            aircraft_text=_nested_get(item, ["flight", "aircraft", "model", "text"]),
            aircraft_reg=_nested_get(item, ["flight", "aircraft", "registration"]),
            aircraft_co2=_to_optional_float(
                _nested_get(item, ["flight", "aircraft", "co2", "value"])
            ),
            aircraft_restricted=_to_optional_bool(
                _nested_get(item, ["flight", "aircraft", "restricted"])
            ),
            owner_name=_nested_get(item, ["flight", "owner", "name"]),
            owner_iata=_nested_get(item, ["flight", "owner", "code", "iata"]),
            owner_icao=_nested_get(item, ["flight", "owner", "code", "icao"]),
            airline=_nested_get(item, ["flight", "airline", "name"]),
            airline_iata=_nested_get(item, ["flight", "airline", "code", "iata"]),
            airline_icao=_nested_get(item, ["flight", "airline", "code", "icao"]),
            origin_iata=origin_upper,
            origin_offset=_normalize_tz_offset(
                _nested_get(item, ["flight", "airport", "origin", "timezone", "offset"])
            ),
            origin_offset_abbr=_nested_get(
                item, ["flight", "airport", "origin", "timezone", "abbr"]
            ),
            origin_offset_dst=_to_optional_bool(
                _nested_get(item, ["flight", "airport", "origin", "timezone", "isDst"])
            ),
            origin_terminal=_nested_get(
                item, ["flight", "airport", "origin", "info", "terminal"]
            ),
            origin_gate=_nested_get(item, ["flight", "airport", "origin", "info", "gate"]),
            dest_iata=_nested_get(item, ["flight", "airport", "destination", "code", "iata"]),
            dest_icao=_nested_get(item, ["flight", "airport", "destination", "code", "icao"]),
            dest_offset=_normalize_tz_offset(
                _nested_get(item, ["flight", "airport", "destination", "timezone", "offset"])
            ),
            dest_offset_abbr=_nested_get(
                item, ["flight", "airport", "destination", "timezone", "abbr"]
            ),
            dest_offset_dst=_to_optional_bool(
                _nested_get(item, ["flight", "airport", "destination", "timezone", "isDst"])
            ),
            dest_terminal=_nested_get(
                item, ["flight", "airport", "destination", "info", "terminal"]
            ),
            dest_gate=_nested_get(item, ["flight", "airport", "destination", "info", "gate"]),
            sched_dep=_to_optional_int(
                _nested_get(item, ["flight", "time", "scheduled", "departure"])
            ),
            sched_arr=_to_optional_int(
                _nested_get(item, ["flight", "time", "scheduled", "arrival"])
            ),
            real_dep=_to_optional_int(
                _nested_get(item, ["flight", "time", "real", "departure"])
            ),
            real_arr=_to_optional_int(
                _nested_get(item, ["flight", "time", "real", "arrival"])
            ),
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=_to_optional_float(
                _nested_get(item, ["flight", "airport", "destination", "position", "latitude"])
            ),
            dest_lng=_to_optional_float(
                _nested_get(item, ["flight", "airport", "destination", "position", "longitude"])
            ),
        )
        records.append(record)

    return records


__all__ = ["FlightRecord", "extract_departure_records"]
