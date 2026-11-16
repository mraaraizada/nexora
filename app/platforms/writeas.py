"""Write.as adapter.

Official docs: https://developers.write.as/docs/api/#publish-a-post
Auth: NONE required for a basic anonymous post — Write.as is unique among NEXORA's
platforms in that `POST /api/posts` with just a body works with no account, no API
key, no token. An optional `WRITEAS_ACCESS_TOKEN` can be set to attribute the post to a
real account instead of posting anonymously, but it is not required to publish.

Live-verified against the real API during development (two real anonymous POSTs to
https://write.as/api/posts, deliberately kept to the minimum needed to confirm the
integration — see docs/platform_research.md): a successful response includes a
`full_post_url` field directly, which this adapter uses rather than hand-constructing a
URL from `id`/`slug`. The live calls also surfaced two real failure modes not obvious
from the docs alone:
  1. Write.as's own content filter can reject a post, returned as 201 with
     `data.id == "contentisblocked"` and an empty `full_post_url` rather than an
     HTTP error status.
  2. Anonymous posting is subject to IP-based abuse detection: a second post shortly
     after the first returned a real `403 {"error_msg": "We've detected abusive
     activity on your IP address."}` — note this is NOT a credentials problem (this
     platform has none), so it's deliberately NOT reported via the base class's generic
     401/403 -> "Authentication failed" mapping, which would be a misleading message for
     a platform with no auth concept; see the explicit check below instead.
"""
from __future__ import annotations

import httpx

from app.config import settings
from app.platforms.base import PlatformAdapter, PlatformPublishError


class WriteAsAdapter(PlatformAdapter):
    name = "Write.as"

    def is_configured(self) -> bool:
        # Deliberately always "configured" — Write.as's anonymous posting needs no
        # credentials at all, which is the whole reason it was chosen as a platform
        # (the easiest possible integration to get genuinely working).
        return True

    async def _do_publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> tuple[str, bool]:
        headers = {}
        if settings.writeas_access_token:
            headers["Authorization"] = f"Token {settings.writeas_access_token}"

        resp = await client.post("https://write.as/api/posts", headers=headers, json={"body": message})
        if resp.status_code == 403:
            try:
                detail = resp.json().get("error_msg", "")
            except ValueError:
                detail = ""
            if "abusive" in detail.lower():
                raise PlatformPublishError(f"Blocked by Write.as abuse detection: {detail}")
        resp.raise_for_status()
        body = resp.json()

        data = body.get("data") or {}
        if data.get("id") == "contentisblocked":
            raise PlatformPublishError("Write.as rejected this post's content (content filter)")

        posted_url = data.get("full_post_url")
        if not posted_url:
            # Fallback for older/alternate API responses that omit full_post_url but
            # still include an id — construct the same URL shape by hand.
            post_id, slug = data.get("id"), data.get("slug")
            if not post_id:
                raise PlatformPublishError("Write.as response did not include a post id")
            posted_url = f"https://write.as/{post_id}/{slug}" if slug else f"https://write.as/{post_id}"

        # Write.as posts are public by default with no sign-in required to view them.
        return posted_url, True
