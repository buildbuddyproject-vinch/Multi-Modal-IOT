"""Sends an alert message via the Telegram Bot HTTP API directly (rather than the
`python-telegram-bot` SDK, which is async-only as of v21 and would be awkward to
call from this codebase's synchronous FastAPI routes) -- one POST, no bot session
to manage."""
import logging

import httpx

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_alert(message: str) -> str:
    """Returns 'sent', 'failed', or 'skipped' (not configured) -- never raises,
    so a notification-channel outage can't take down alert creation itself."""
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return "skipped"

    url = TELEGRAM_API_URL.format(token=settings.telegram_bot_token)
    try:
        resp = httpx.post(url, json={"chat_id": settings.telegram_chat_id, "text": message}, timeout=10.0)
        resp.raise_for_status()
        return "sent"
    except httpx.HTTPError:
        logger.exception("Telegram alert dispatch failed")
        return "failed"
