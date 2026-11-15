"""Telegram Bot API adapter.

Official docs: https://core.telegram.org/bots/api#sendmessage
Auth: bot token embedded in the request URL (no separate header).
"""
from __future__ import annotations

import httpx

from app.config import settings
from app.platforms.base import PlatformAdapter, PlatformPublishError


class TelegramAdapter(PlatformAdapter):
    name = "Telegram"

    def is_configured(self) -> bool:
        return bool(settings.telegram_bot_token and settings.telegram_chat_id)

    def missing_config_error(self) -> str:
        return "Not configured: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required"

    async def _do_publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> tuple[str, bool]:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        resp = await client.post(url, json={"chat_id": settings.telegram_chat_id, "text": message})
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            raise PlatformPublishError(body.get("description", "Telegram API returned ok=false"))

        result = body["result"]
        message_id = result.get("message_id")
        if settings.telegram_channel_username:
            # Only a channel with a public @username has a stable, publicly-viewable
            # permalink; a private group/chat has no equivalent public URL.
            posted_url = f"https://t.me/{settings.telegram_channel_username}/{message_id}"
            public_access = True
        else:
            posted_url = f"telegram://message/{message_id}"
            public_access = False
        return posted_url, public_access
