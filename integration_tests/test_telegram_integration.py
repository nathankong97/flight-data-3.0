import os
import time

import pytest

from src.alerts.telegram import TelegramAlerter, load_telegram_settings


@pytest.mark.integration
def test_send_message_to_telegram_if_configured():
    settings = load_telegram_settings()
    if settings is None:
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            pytest.fail("Telegram credentials must be configured for CI runs.")
        pytest.skip("Telegram creds not configured; skipping integration test")

    alerter = TelegramAlerter(
        token=settings.token, chat_id=settings.chat_id, parse_mode=settings.parse_mode
    )
    ok = alerter.send_text(f"flight-data integration test ping {int(time.time())}")
    assert ok is True
