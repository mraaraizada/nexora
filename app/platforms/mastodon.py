"""Mastodon REST API adapter (works against any standard Mastodon instance).

Official docs: https://docs.joinmastodon.org/methods/statuses/#create
Auth: OAuth2 bearer access token (create one under Settings > Development > New
Application on the chosen instance, with the "write:statuses" scope).
"""
from __future__ import annotations

import httpx

from app.config import settings
from app.platforms.base import PlatformAdapter, PlatformPublishError


class MastodonAdapter(PlatformAdapter):
    name = "Mastodon"

    def is_configured(self) -> bool:
        return bool(settings.mastodon_access_token and settings.mastodon_instance_url)

    def missing_config_error(self) -> str:
        return "Not configured: MASTODON_ACCESS_TOKEN (and MASTODON_INSTANCE_URL) are required"

    async def _do_publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> tuple[str, bool]:
        url = f"{settings.mastodon_instance_url}/api/v1/statuses"
        headers = {"Authorization": f"Bearer {settings.mastodon_access_token}"}
        resp = await client.post(url, headers=headers, json={"status": message, "visibility": "public"})
        resp.raise_for_status()
        body = resp.json()

        posted_url = body.get("url")
        if not posted_url:
            raise PlatformPublishError("Mastodon response did not include a status URL")
        # visibility "public" statuses are listed on public timelines and viewable
        # without authentication, so this is a genuine (not assumed) public post.
        return posted_url, body.get("visibility") == "public"
