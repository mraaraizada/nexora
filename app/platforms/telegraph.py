"""Telegra.ph adapter.

Official docs: https://telegra.ph/api
Auth: NONE required to get started — `createAccount` issues a fresh access token with
just a short_name, no email/signup/verification at all. This is the one NEXORA
platform where even account creation is a pure, unattended API call rather than a
human clicking through a web dashboard once.

An optional `TELEGRAPH_ACCESS_TOKEN` can be set to reuse one persistent author
identity across posts; otherwise a new account is created on every publish call,
which is exactly what the API is designed for.

NOT live-verified in this environment (createAccount is an account-creation call this
environment's action policy blocks making automatically) — implemented directly
against the documented API contract, same honesty caveat as Telegram/Mastodon/Dev.to/
Bluesky before it (see docs/platform_research.md).
"""
from __future__ import annotations

import json

import httpx

from app.config import settings
from app.platforms.base import PlatformAdapter, PlatformPublishError

_TITLE_MAX_LEN = 80


def _derive_title(message: str, cta_url: str) -> str:
    without_url = message.replace(cta_url, "").strip(" -—:")
    title = without_url or message
    if len(title) > _TITLE_MAX_LEN:
        title = title[: _TITLE_MAX_LEN - 1].rstrip() + "…"
    return title


class TelegraphAdapter(PlatformAdapter):
    name = "Telegra.ph"

    def is_configured(self) -> bool:
        # Always configured — account creation needs no credentials at all.
        return True

    async def _ensure_access_token(self, client: httpx.AsyncClient) -> str:
        if settings.telegraph_access_token:
            return settings.telegraph_access_token

        resp = await client.post("https://api.telegra.ph/createAccount", data={"short_name": "NEXORA"})
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            raise PlatformPublishError(body.get("error", "Telegra.ph createAccount failed"))
        return body["result"]["access_token"]

    async def _do_publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> tuple[str, bool]:
        access_token = await self._ensure_access_token(client)

        content = json.dumps([{"tag": "p", "children": [message]}])
        resp = await client.post(
            "https://api.telegra.ph/createPage",
            data={"access_token": access_token, "title": _derive_title(message, cta_url), "content": content, "return_content": "false"},
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            raise PlatformPublishError(body.get("error", "Telegra.ph createPage failed"))

        posted_url = body["result"].get("url")
        if not posted_url:
            raise PlatformPublishError("Telegra.ph response did not include a page URL")
        # Telegra.ph pages are public by default, viewable with no auth.
        return posted_url, True
