import logging
from typing import List

import pytest

from src.alerts.telegram import (
    TelegramAlerter,
    TelegramLogHandler,
    chunk_text,
    load_telegram_settings,
)


class DummySender:
    def __init__(self) -> None:
        self.messages: List[str] = []

    def send_text(self, text: str) -> bool:
        self.messages.append(text)
        return True


def test_chunk_text_prefers_newlines():
    text = "line1\n" + ("x" * 4090) + "\nline3"
    chunks = chunk_text(text)
    # Should result in two or more chunks but all under 4096
    assert all(len(c) <= 4096 for c in chunks)
    assert "line1" in chunks[0]
    assert "line3" in chunks[-1]


def test_telegram_log_handler_sends_error_with_traceback():
    sender = DummySender()
    handler = TelegramLogHandler(sender, level=logging.ERROR, include_traceback=True)

    logger = logging.getLogger("tests.telegram")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.addHandler(handler)

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        logger.exception("failed")

    # Ensure a message went out including the exception
    assert sender.messages, "No message was sent by TelegramLogHandler"
    sent = "\n".join(sender.messages)
    assert "failed" in sent
    assert "Traceback" in sent and "RuntimeError: boom" in sent


def test_telegram_alerter_chunks_and_calls_requests(monkeypatch):
    calls = []

    class DummyResp:
        def __init__(self, status_code=200, ok=True):
            self.status_code = status_code
            self._ok = ok

        def json(self):
            return {"ok": self._ok}

    def fake_post(url, json, timeout):  # noqa: A002 - shadow builtins in test OK
        calls.append((url, json, timeout))
        return DummyResp()

    monkeypatch.setattr("requests.post", fake_post)

    # Make a message longer than 4096
    long_text = "A" * 5000

    alerter = TelegramAlerter(token="tkn", chat_id="cid")
    ok = alerter.send_text(long_text)
    assert ok is True
    # Expect 2 calls due to chunking
    assert len(calls) == 2


def test_load_telegram_settings_reads_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=dot_token",
                "TELEGRAM_CHAT_ID=dot_chat",
                "TELEGRAM_PARSE_MODE=MarkdownV2",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_PARSE_MODE", raising=False)

    settings = load_telegram_settings(env_file=env_file)
    assert settings is not None
    assert settings.token == "dot_token"
    assert settings.chat_id == "dot_chat"
    assert settings.parse_mode == "MarkdownV2"


def test_load_telegram_settings_prefers_environment_over_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=file_token",
                "TELEGRAM_CHAT_ID=file_chat",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "env_chat")

    settings = load_telegram_settings(env_file=env_file)
    assert settings is not None
    assert settings.token == "env_token"
    assert settings.chat_id == "env_chat"


def test_telegram_alerter_from_env_requires_settings(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("TELEGRAM_BOT_TOKEN=only_token", encoding="utf-8")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(ValueError):
        TelegramAlerter.from_env(env_file=env_file)
