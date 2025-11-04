# Telegram Alerts

This module provides lightweight Telegram notifications for critical errors and important events.
It includes:

- `TelegramAlerter`: a minimal client to send messages via the Telegram Bot API.
- `TelegramLogHandler`: a logging handler that forwards ERROR/CRITICAL records (with optional tracebacks).
- `install_telegram_log_handler_from_env()`: convenience function to enable alerts automatically when env vars are present and log a warning when not.

## Setup

1) Create a bot and get a token

- Talk to `@BotFather` in Telegram and create a bot.
- Copy the bot token (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`).

2) Get a target chat id

- For a private chat: send a message to your bot, then use an API such as `getUpdates` or a helper to find the chat id.
- For a group/channel: add the bot and use the group/channel id (often negative, e.g. `-1001234567890`).

3) Configure environment

- Add the following to your `.env` (see `.env.example`):

```env
TELEGRAM_BOT_TOKEN=123456:abcDEF-your-bot-token
TELEGRAM_CHAT_ID=-1001234567890
# Optional: HTML or MarkdownV2
TELEGRAM_PARSE_MODE=HTML
```

## Automatic Integration (Recommended)

`run_job` will automatically install the alert handler when credentials are present.
If credentials are missing, a single warning is logged and the job continues normally.

No code changes are required in callers: just set env vars and run your job.

## Manual Usage

Send a message directly:

```python
from src.alerts.telegram import TelegramAlerter

alerter = TelegramAlerter.from_env()  # requires TELEGRAM_* env vars
alerter.send_text("flight-data: manual alert test")
```

Attach the logging handler explicitly (if not using the runner integration):

```python
import logging
from src.alerts.telegram import TelegramAlerter, TelegramLogHandler

root = logging.getLogger()
alerter = TelegramAlerter.from_env()
root.addHandler(TelegramLogHandler(alerter, level=logging.ERROR, include_traceback=True))
```

## What Gets Alerted

- ERROR: concise message (no traceback).
- CRITICAL or `logger.exception(...)`: message plus full traceback.
- Long messages are split to satisfy Telegram’s 4096 character limit.

## Testing

- Unit tests: `pytest -q` (integration tests are deselected by default).
- Integration test (live Telegram API):

```bash
# Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
pytest -q -m integration
```

## Troubleshooting

- No alerts received
  - Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set and correct.
  - Ensure the bot is allowed in the target chat/group.
- Warnings in logs about missing credentials
  - This is expected when env vars are not provided; alerts are disabled but the job continues.
- Message too long
  - The alerter automatically chunks messages; no action required.
- Network/transport errors
  - Occasional transient errors are retried by your application logic; confirm outbound access and proxy/VPN settings if persistent.

## Reference

- Code: `src/alerts/telegram.py`
- Env: `.env.example` (search for `TELEGRAM_`)
- Runner wiring: `src/jobs/runner.py` (calls `install_telegram_log_handler_from_env()`)

