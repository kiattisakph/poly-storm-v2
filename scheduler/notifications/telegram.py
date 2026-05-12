"""Telegram transport for scheduler notifications."""

import logging

import httpx

from scheduler.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_ENABLED,
)

logger = logging.getLogger(__name__)

TIMEOUT = 10


def send_message(text: str) -> bool:
    if not TELEGRAM_ENABLED:
        return False
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("telegram enabled but token/chat id is missing")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        resp = httpx.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        return True
    except httpx.HTTPStatusError as e:
        logger.warning(
            "telegram notification failed: HTTP %s",
            e.response.status_code,
        )
        return False
    except Exception as e:
        logger.warning("telegram notification failed: %s", type(e).__name__)
        return False
