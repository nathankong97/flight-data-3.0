import os
import time

import pytest

from src.alerts.telegram import TelegramAlerter


@pytest.mark.integration
def test_send_message_to_telegram_if_configured():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        pytest.skip("Telegram creds not configured; skipping integration test")

    alerter = TelegramAlerter(token=token, chat_id=chat_id)
    ok = alerter.send_text(f"flight-data integration test ping {int(time.time())}")
    assert ok is True

