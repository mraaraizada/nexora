"""Discord incoming webhook adapter.

Official docs: https://discord.com/developers/docs/resources/webhook#execute-webhook
Auth: the webhook URL itself is the credential (Server Settings > Integrations >
Webhooks > New Webhook on the target channel).
"""
from __future__ import annotations

import httpx

from app.config import settings
from app.platforms.base import PlatformAdapter, PlatformPublishError


class DiscordAdapter(PlatformAdapter):
    name = "Discord"

    def is_configured(self) -> bool:
        return bool(settings.discord_webhook_url)

    def missing_config_error(self) -> str:
        return "Not configured: DISCORD_WEBHOOK_URL is required"

    async def _do_publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> tuple[str, bool]:
        # ?wait=true makes Discord return the created message object (id, channel_id)
        # instead of an empty 204 — needed to build a permalink and confirm success.
        url = f"{settings.discord_webhook_url}?wait=true"
        resp = await client.post(url, json={"content": message})
        resp.raise_for_status()
        body = resp.json()

        message_id = body.get("id")
        channel_id = body.get("channel_id")
        if not message_id or not channel_id:
            raise PlatformPublishError("Discord response did not include a message id")

        if settings.discord_guild_id:
            posted_url = f"https://discord.com/channels/{settings.discord_guild_id}/{channel_id}/{message_id}"
        else:
            posted_url = f"https://discord.com/channels/@me/{channel_id}/{message_id}"
        # A Discord message link only resolves for someone who is already a member of
        # that server — never genuinely publicly accessible like a web page, even
        # though the post itself was created successfully.
        return posted_url, False
