"""Dev.to (Forem) REST API adapter.

Official docs: https://developers.forem.com/api/v1#tag/articles/operation/createArticle
Auth: `api-key` header (generate one at https://dev.to/settings/extensions).

Dev.to articles require a title separate from the body; our input is a single short
message, so the title is derived from it (the body still carries the full, original
message and CTA link verbatim).

Live-verified during development with a real API key, and that live test surfaced a
real discrepancy worth recording: the creation response's `published` field came back
`false` despite the request explicitly sending `"published": true`. Checking the
article afterward confirmed it WAS genuinely public anyway — it could be fetched in
full, with no authentication, from Dev.to's own public read endpoint
(`GET /api/articles/:username/:slug`), even though the creation response's own
`published` flag said otherwise and the plain HTML page 404'd for a non-browser
request (most likely Dev.to's server-side rendering skipping brand-new/low-reputation
accounts' pages, unrelated to actual publication state). Trusting the creation
response's `published` field alone would have under-reported `public_access` for a
post that genuinely is public — so this adapter instead confirms public accessibility
with a second, real, unauthenticated GET against the public read endpoint, rather than
trusting a single response field that was directly observed to disagree with reality.
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
        username, slug = body.get("user", {}).get("username"), body.get("slug")
        if not posted_url:
            raise PlatformPublishError("Dev.to response did not include an article URL")

        public_access = await self._confirm_publicly_readable(client, username, slug)
        return posted_url, public_access

    @staticmethod
    async def _confirm_publicly_readable(client: httpx.AsyncClient, username: str | None, slug: str | None) -> bool:
        """Confirms with a real, unauthenticated GET that the article is actually
        fetchable from Dev.to's public read API — see the module docstring for why the
        creation response's own `published` field isn't trustworthy enough on its own."""
        if not username or not slug:
            return False
        try:
            check = await client.get(f"https://dev.to/api/articles/{username}/{slug}")
        except httpx.HTTPError:
            return False
        return check.status_code == 200
