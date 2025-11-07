from unittest.mock import MagicMock

import pytest
import requests

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
    assert "proxies" in kwargs
    assert kwargs["proxies"] is None
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


def test_fetch_departures_uses_proxies_when_provided(mock_session):
    response = MagicMock()
    response.json.return_value = {"data": []}
    response.raise_for_status.return_value = None
    mock_session.get.return_value = response

    proxies_mapping = {"http": "http://1.1.1.1:80", "https": "http://1.1.1.1:80"}
    client = FlightRadarClient(
        session=mock_session,
        get_proxies=lambda: proxies_mapping,
    )

    client.fetch_departures("HND")

    _, kwargs = mock_session.get.call_args
    assert kwargs["proxies"] == proxies_mapping


def test_fetch_departures_can_force_direct(mock_session):
    response = MagicMock()
    response.json.return_value = {"data": []}
    response.raise_for_status.return_value = None
    mock_session.get.return_value = response

    proxies_mapping = {"http": "http://1.1.1.1:80", "https": "http://1.1.1.1:80"}
    client = FlightRadarClient(
        session=mock_session,
        get_proxies=lambda: proxies_mapping,
    )

    client.fetch_departures("HND", force_proxies=False)

    _, kwargs = mock_session.get.call_args
    assert kwargs["proxies"] is None


def test_fetch_departures_429_logs_and_raises(mock_session, caplog):
    # Prepare a response that simulates 429 with Retry-After
    resp = MagicMock()
    resp.status_code = 429
    resp.headers = {"Retry-After": "15"}

    http_err = requests.HTTPError("too many requests")
    http_err.response = resp
    resp.raise_for_status.side_effect = http_err
    mock_session.get.return_value = resp

    client = FlightRadarClient(session=mock_session)

    with pytest.raises(requests.HTTPError):
        client.fetch_departures("HND")


def test_fetch_departures_reports_proxy_failure_on_exception(mock_session):
    def raising_get(*args, **kwargs):
        raise requests.RequestException("proxy failed")

    mock_session.get.side_effect = raising_get

    called = {}

    def report_failure(mapping):
        called["mapping"] = mapping

    proxies_mapping = {"http": "http://2.2.2.2:8080", "https": "http://2.2.2.2:8080"}
    client = FlightRadarClient(
        session=mock_session,
        get_proxies=lambda: proxies_mapping,
        report_proxy_failure=report_failure,
    )

    with pytest.raises(requests.RequestException):
        client.fetch_departures("HND")

    assert called["mapping"] == proxies_mapping
