import pytest

from src.transform.flights import FlightRecord, extract_departure_records


def make_payload(**overrides):
    base = {
        "result": {
            "response": {
                "airport": {
                    "pluginData": {
                        "schedule": {
                            "departures": {
                                "data": [
                                    {
                                        "flight": {
                                            "identification": {
                                                "number": {"default": "NH123"}
                                            },
                                            "status": {"text": "Scheduled"},
                                            "aircraft": {
                                                "model": {
                                                    "code": "789",
                                                    "text": "Boeing 787-9",
                                                },
                                                "registration": "JA123A",
                                                "co2": {"value": 123.45},
                                                "restricted": False,
                                            },
                                            "owner": {
                                                "name": "ANA",
                                                "code": {"iata": "NH", "icao": "ANA"},
                                            },
                                            "airline": {
                                                "name": "All Nippon Airways",
                                                "code": {"iata": "NH", "icao": "ANA"},
                                            },
                                            "airport": {
                                                "origin": {
                                                    "timezone": {
                                                        "offset": 9,
                                                        "abbr": "JST",
                                                        "isDst": False,
                                                    },
                                                    "info": {
                                                        "terminal": "2",
                                                        "gate": "54",
                                                    },
                                                },
                                                "destination": {
                                                    "code": {"iata": "SFO", "icao": "KSFO"},
                                                    "timezone": {
                                                        "offset": -7,
                                                        "abbr": "PDT",
                                                        "isDst": True,
                                                    },
                                                    "info": {"terminal": "I", "gate": "15"},
                                                    "position": {
                                                        "latitude": 37.6213,
                                                        "longitude": -122.379,
                                                    },
                                                },
                                            },
                                            "time": {
                                                "scheduled": {
                                                    "departure": 1718653200,
                                                    "arrival": 1718689200,
                                                },
                                                "real": {
                                                    "departure": 1718655000,
                                                    "arrival": 1718690400,
                                                },
                                            },
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
    }
    base.update(overrides)
    return base


def test_extract_departure_records_parses_fields():
    payload = make_payload()
    coords = {"HND": {"lat": 35.5494, "lng": 139.7798}}

    records = extract_departure_records(payload, "hnd", coordinates=coords)

    assert len(records) == 1
    record = records[0]
    assert isinstance(record, FlightRecord)
    assert record.flight_num == "NH123"
    assert record.status_detail == "Scheduled"
    assert record.aircraft_code == "789"
    assert record.origin_iata == "HND"
    assert record.dest_iata == "SFO"
    assert record.origin_offset == 9
    assert record.real_dep == 1718655000
    assert record.dest_lat == pytest.approx(37.6213)
    assert record.origin_lat == pytest.approx(35.5494)


def test_extract_departure_handles_missing_sections():
    payload = {"result": {"response": {"airport": {}}}}
    records = extract_departure_records(payload, "HND")
    assert records == []


def test_to_db_params_requires_ingest_id():
    record = FlightRecord(
        flight_num="NH1",
        status_detail=None,
        aircraft_code=None,
        aircraft_text=None,
        aircraft_reg=None,
        aircraft_co2=None,
        aircraft_restricted=None,
        owner_name=None,
        owner_iata=None,
        owner_icao=None,
        airline=None,
        airline_iata=None,
        airline_icao=None,
        origin_iata="HND",
        origin_offset=None,
        origin_offset_abbr=None,
        origin_offset_dst=None,
        origin_terminal=None,
        origin_gate=None,
        dest_iata=None,
        dest_icao=None,
        dest_offset=None,
        dest_offset_abbr=None,
        dest_offset_dst=None,
        dest_terminal=None,
        dest_gate=None,
        sched_dep=None,
        sched_arr=None,
        real_dep=None,
        real_arr=None,
        origin_lat=None,
        origin_lng=None,
        dest_lat=None,
        dest_lng=None,
    )

    with pytest.raises(ValueError):
        record.to_db_params()

    params = record.to_db_params(ingest_run_id="run-1")
    assert params["ingest_run_id"] == "run-1"
