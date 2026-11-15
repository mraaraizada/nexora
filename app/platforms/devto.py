"""Dev.to (Forem) REST API adapter.

Official docs: https://developers.forem.com/api/v1#tag/articles/operation/createArticle
Auth: `api-key` header (generate one at https://dev.to/settings/extensions).

Dev.to articles require a title separate from the body; our input is a single short
message, so the title is derived from it (the body still carries the full, original
message and CTA link verbatim).
"""
from __future__ import annotations

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


class DevToAdapter(PlatformAdapter):
    name = "Dev.to"

    def is_configured(self) -> bool:
        return bool(settings.devto_api_key)

    def missing_config_error(self) -> str:
        return "Not configured: DEVTO_API_KEY is required"

    async def _do_publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> tuple[str, bool]:
        headers = {"api-key": settings.devto_api_key}
        article = {
            "title": _derive_title(message, cta_url),
            "body_markdown": message,
            "published": True,
            "tags": ["nexora"],
        }
        resp = await client.post("https://dev.to/api/articles", headers=headers, json={"article": article})
        resp.raise_for_status()
        body = resp.json()

        posted_url = body.get("url")
        if not posted_url:
            raise PlatformPublishError("Dev.to response did not include an article URL")
        # Published (not draft) Dev.to articles are indexed and publicly viewable with no auth.
        return posted_url, bool(body.get("published"))
