from unittest.mock import MagicMock

import pytest

from src.api.flightradar import FlightRadarClient, BASE_URL, HEADERS


@pytest.fixture
def mock_session():
    return MagicMock()


def test_fetch_departures_builds_request(mock_session):
    response = MagicMock()
    response.json.return_value = {"data": []}
    response.raise_for_status.return_value = None
    mock_session.get.return_value = response

    client = FlightRadarClient(session=mock_session, timeout=5)
    result = client.fetch_departures("HND", page=2, limit=50, timestamp=1234567890)

    assert result == {"data": []}
    mock_session.get.assert_called_once()
    args, kwargs = mock_session.get.call_args
    assert args[0] == BASE_URL
    assert kwargs["headers"] == HEADERS
    assert kwargs["timeout"] == 5
    params = kwargs["params"]
    assert params == {
        "code": "HND",
        "page": 2,
        "limit": 50,
        "plugin[]": "schedule",
        "plugin-setting[schedule][mode]": "departures",
        "plugin-setting[schedule][timestamp]": 1234567890,
    }


@pytest.mark.parametrize(
    "airport_code,page,limit",
    [
        ("", 1, 100),
        ("HND", 0, 100),
        ("HND", 1, 0),
    ],
)
def test_fetch_departures_validates_inputs(mock_session, airport_code, page, limit):
    client = FlightRadarClient(session=mock_session)
    with pytest.raises(ValueError):
        client.fetch_departures(airport_code, page=page, limit=limit)
