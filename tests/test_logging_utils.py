import logging
from datetime import datetime

from src.logging_utils import (
    configure_logging,
    generate_run_id,
    perf,
    perf_span,
)


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


def test_perf_decorator_logs_success(app_config):
    log_path = configure_logging(app_config, run_id="perf-decorator-success")

    @perf("test_func", tags={"k": "v"})
    def fast_fn(x: int) -> int:
        return x + 1

    assert fast_fn(1) == 2

    for handler in logging.getLogger().handlers:
        handler.flush()

    contents = log_path.read_text(encoding="utf-8")
    assert "event=perf name=test_func" in contents
    assert "success=true" in contents
    assert "duration_ms=" in contents
    assert "k" in contents and "v" in contents


def test_perf_decorator_logs_failure_and_reraises(app_config):
    log_path = configure_logging(app_config, run_id="perf-decorator-failure")

    @perf("explode")
    def boom():
        raise RuntimeError("boom")

    try:
        boom()
        raise AssertionError("Expected RuntimeError to be raised")
    except RuntimeError:
        pass

    for handler in logging.getLogger().handlers:
        handler.flush()

    contents = log_path.read_text(encoding="utf-8")
    assert "event=perf name=explode" in contents
    assert "success=false" in contents


def test_perf_span_logs_block(app_config):
    log_path = configure_logging(app_config, run_id="perf-span")

    with perf_span("block", tags={"airport": "NRT"}):
        _ = sum(range(10))

    for handler in logging.getLogger().handlers:
        handler.flush()

    contents = log_path.read_text(encoding="utf-8")
    assert "event=perf name=block" in contents
    assert "success=true" in contents
    assert "airport" in contents and "NRT" in contents
