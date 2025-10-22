import os

import pytest

from src.api.flightradar import FlightRadarClient
from src.transform import extract_departure_records


@pytest.mark.integration
def test_api_to_transform_roundtrip():
    airport_code = os.getenv("TEST_AIRPORT_CODE", "HND")
    with FlightRadarClient(timeout=15) as client:
        payload = client.fetch_departures(airport_code, page=1, limit=10)

    records = extract_departure_records(payload, airport_code)

    assert isinstance(records, list)
    if records:
        first = records[0]
        assert first.origin_iata == airport_code.upper()
        assert first.flight_num
