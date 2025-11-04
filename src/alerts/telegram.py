"""Telegram alerting utilities.

Provides a lightweight client to send alerts via the Telegram Bot API and
an optional logging handler that forwards ERROR/CRITICAL records (including
tracebacks) to Telegram.

Environment variables (see .env.example):
- TELEGRAM_BOT_TOKEN: Bot token for the Telegram bot
- TELEGRAM_CHAT_ID: Target chat ID (channel/group/user)
- TELEGRAM_PARSE_MODE: Optional ("HTML" or "MarkdownV2")

Notes:
- Telegram enforces a 4096 character limit per message. This module chunks
  long messages and sends them as multiple messages in order.
- For logging, traceback is included when available (record.exc_info) and
  for CRITICAL messages by default.
"""

from __future__ import annotations

import logging
import os
import traceback
from dataclasses import dataclass
from typing import Iterable, List, Optional

import requests

MAX_MESSAGE_LEN = 4096


def chunk_text(text: str, limit: int = MAX_MESSAGE_LEN) -> List[str]:
    """Split ``text`` into <= ``limit`` sized chunks, preferring newline breaks.

    Args:
        text: The full message to send.
        limit: Maximum characters per chunk (Telegram hard limit is 4096).

    Returns:
        List of message chunks.
    """
    if len(text) <= limit:
        return [text]

    chunks: List[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        # Prefer breaking at the last newline within the limit
        split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1 or split_at < limit // 2:
            # No good newline found; hard split
            split_at = limit
        part, remaining = remaining[:split_at], remaining[split_at:]
        if remaining.startswith("\n"):
            remaining = remaining[1:]
        if part:
            chunks.append(part)
    return chunks


@dataclass(frozen=True)
class TelegramSettings:
    token: str
    chat_id: str
    parse_mode: Optional[str] = None  # "HTML" or "MarkdownV2"


class TelegramAlerter:
    """Minimal Telegram Bot API client for sending alerts.

    Example:
        alerter = TelegramAlerter.from_env()
        alerter.send_text("Flight-data: critical error detected")
    """

    def __init__(self, token: str, chat_id: str, *, parse_mode: Optional[str] = None, timeout: float = 10.0) -> None:
        self._token = token
        self._chat_id = chat_id
        self._parse_mode = parse_mode
        self._timeout = timeout

    @staticmethod
    def from_env() -> "TelegramAlerter":
        """Create an alerter from environment variables.

        Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
        Optionally uses TELEGRAM_PARSE_MODE.
        """
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment.")
        return TelegramAlerter(token, chat_id, parse_mode=os.environ.get("TELEGRAM_PARSE_MODE"))

    def send_text(self, text: str) -> bool:
        """Send text, chunking as needed. Returns True if all chunks succeed."""
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        ok_all = True
        for chunk in chunk_text(text):
            payload = {
                "chat_id": self._chat_id,
                "text": chunk,
            }
            if self._parse_mode:
                payload["parse_mode"] = self._parse_mode
            resp = requests.post(url, json=payload, timeout=self._timeout)
            if resp.status_code != 200:
                ok_all = False
                continue
            data = resp.json()
            if not data.get("ok", False):
                ok_all = False
        return ok_all


class TelegramLogHandler(logging.Handler):
    """Logging handler that forwards ERROR/CRITICAL records to Telegram.

    - Includes traceback when available (record.exc_info) or level >= CRITICAL.
    - Splits long messages to satisfy Telegram limits.
    - Dependency-injected ``sender`` aids unit testing.
    """

    def __init__(
        self,
        sender: "_Sender",
        *,
        level: int = logging.ERROR,
        include_traceback: bool = True,
    ) -> None:
        super().__init__(level=level)
        self._sender = sender
        self._include_traceback = include_traceback

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - exercised via tests
        try:
            base = self._format_base(record)
            parts: List[str] = [base]

            if self._include_traceback and (record.exc_info or record.levelno >= logging.CRITICAL):
                tb_str = self._format_traceback(record)
                if tb_str:
                    parts.append(tb_str)

            message = "\n\n".join([p for p in parts if p])
            # send_text handles chunking
            self._sender.send_text(message)
        except Exception:  # never raise inside logging
            self.handleError(record)

    def _format_base(self, record: logging.LogRecord) -> str:
        level = record.levelname
        logger_name = record.name
        msg = self.format(record) if self.formatter else record.getMessage()
        run_id = getattr(record, "run_id", None)
        prefix = f"[{level}] {logger_name}"
        if run_id:
            prefix += f" [run={run_id}]"
        return f"{prefix}: {msg}"

    @staticmethod
    def _format_traceback(record: logging.LogRecord) -> str:
        if record.exc_info:
            return "Traceback (most recent call last):\n" + "".join(traceback.format_exception(*record.exc_info))
        if record.stack_info:
            return f"Stack:\n{record.stack_info}"
        return ""


class _Sender:
    """Protocol-like minimal interface for sending text (for DI/testing)."""

    def send_text(self, text: str) -> bool:  # pragma: no cover - interface only
        raise NotImplementedError

