from unittest.mock import MagicMock

import pytest

from src.jobs import RunConfig, run_job


@pytest.fixture
def app_config(tmp_path):
    class Config:
        log_directory = tmp_path
        log_level = "INFO"
    return Config()


def test_run_job_orders_calls(monkeypatch, app_config):
    load_codes = MagicMock(return_value=["HND", "NRT"])
    monkeypatch.setattr("src.jobs.runner.load_airport_codes", load_codes)

    pagination = MagicMock(side_effect=[-2, -1])
    monkeypatch.setattr("src.jobs.runner.page_for_index", pagination)

    fetch = MagicMock(side_effect=[{"result": {}}, {"result": {}}])
    api_client = MagicMock()
    api_client.fetch_departures = fetch

    monkeypatch.setattr("src.jobs.runner.load_coordinates", MagicMock(return_value={}))

    transform = MagicMock(return_value=[])
    monkeypatch.setattr("src.jobs.runner.extract_departure_records", transform)

    upsert = MagicMock()
    monkeypatch.setattr("src.jobs.runner.upsert_flights", upsert)

    run_config = RunConfig(region="jp", max_pages=1)

    run_job(app_config, MagicMock(), api_client, run_config)

    assert load_codes.call_args[0][0] == "jp"
    assert pagination.call_count == 2
    assert fetch.call_count == 2
    transform.assert_called()
