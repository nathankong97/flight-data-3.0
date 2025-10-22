import os

import pytest

from src.api.flightradar import FlightRadarClient


@pytest.mark.integration
def test_fetch_departures_live():
    airport_code = os.getenv("TEST_AIRPORT_CODE", "HND")
    with FlightRadarClient(timeout=15) as client:
        data = client.fetch_departures(airport_code, page=1, limit=10)
    assert isinstance(data, dict)
    assert data
