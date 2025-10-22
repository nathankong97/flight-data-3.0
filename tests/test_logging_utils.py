import logging
from datetime import datetime

from src.logging_utils import configure_logging, generate_run_id


def test_configure_logging_creates_run_scoped_file(app_config):
    run_id = "run id/123"
    log_path = configure_logging(app_config, run_id=run_id)

    expected_name = f"{app_config.app_name}-run-id-123.log"
    assert log_path.name == expected_name
    assert log_path.exists()

    logger = logging.getLogger("flight_data.tests")
    logger.info("hello from test")

    for handler in logging.getLogger().handlers:
        handler.flush()

    contents = log_path.read_text(encoding="utf-8")
    assert "hello from test" in contents
    assert "run id/123" in contents

    logging.getLogger().handlers.clear()


def test_generate_run_id_uses_utc_timestamp_format():
    run_id = generate_run_id()
    datetime.strptime(run_id, "%Y%m%dT%H%M%SZ")
