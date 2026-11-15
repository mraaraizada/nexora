"""Bluesky (AT Protocol) adapter.

Official docs:
  - Auth:   https://docs.bsky.app/docs/api/com-atproto-server-create-session
  - Post:   https://docs.bsky.app/docs/api/com-atproto-repo-create-record
Auth: an app password (NOT the real account password) exchanged for a short-lived
access JWT via createSession, then used as a Bearer token for createRecord.
"""
from __future__ import annotations

from datetime import timezone

import httpx

from app.config import settings
from app.platforms.base import PlatformAdapter, PlatformPublishError
from app.utils.time_utils import now_utc

_BASE = "https://bsky.social/xrpc"


class BlueskyAdapter(PlatformAdapter):
    name = "Bluesky"

    def is_configured(self) -> bool:
        return bool(settings.bluesky_handle and settings.bluesky_app_password)

    def missing_config_error(self) -> str:
        return "Not configured: BLUESKY_HANDLE and BLUESKY_APP_PASSWORD are required"

    async def _do_publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> tuple[str, bool]:
        session_resp = await client.post(
            f"{_BASE}/com.atproto.server.createSession",
            json={"identifier": settings.bluesky_handle, "password": settings.bluesky_app_password},
        )
        session_resp.raise_for_status()
        session = session_resp.json()
        access_jwt, did = session.get("accessJwt"), session.get("did")
        if not access_jwt or not did:
            raise PlatformPublishError("Bluesky login did not return a session token")

        record = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": now_utc().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        post_resp = await client.post(
            f"{_BASE}/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_jwt}"},
            json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
        )
        post_resp.raise_for_status()
        body = post_resp.json()

        uri = body.get("uri")  # at://did:plc:xxxx/app.bsky.feed.post/<rkey>
        if not uri:
            raise PlatformPublishError("Bluesky response did not include a post URI")
        rkey = uri.rsplit("/", 1)[-1]
        posted_url = f"https://bsky.app/profile/{settings.bluesky_handle}/post/{rkey}"
        # Bluesky posts are public by default (no private-post concept in the base protocol).
        return posted_url, True
