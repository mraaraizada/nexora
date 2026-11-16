"""Concurrent, independent publishing across every registered platform adapter.

Platform selection is entirely internal (the registry below) — callers never choose
which platforms to post to. Each adapter's publish() is isolated: one platform raising
or returning a failed result never prevents the others from being attempted, and the
whole batch always completes (no uncontrolled retries, no partial crash)."""
from __future__ import annotations

import asyncio

import httpx

from app.config import settings
from app.platforms.base import PlatformAdapter
from app.platforms.bluesky import BlueskyAdapter
from app.platforms.devto import DevToAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.telegraph import TelegraphAdapter
from app.platforms.writeas import WriteAsAdapter
from app.schemas import PlatformResult
from app.services.result_service import aggregate
from app.services.validation_service import validate_message

#: The platform registry — the single place platform selection is decided.
PLATFORM_ADAPTERS: list[PlatformAdapter] = [
    TelegraphAdapter(),
    MastodonAdapter(),
    WriteAsAdapter(),
    DevToAdapter(),
    BlueskyAdapter(),
]


async def _publish_one(adapter: PlatformAdapter, client: httpx.AsyncClient, message: str, cta_url: str) -> PlatformResult:
    try:
        return await adapter.publish(client, message, cta_url)
    except Exception as exc:  # noqa: BLE001 - last-resort isolation: a bug in one
        # adapter must never take down the whole batch or crash the request.
        return PlatformResult(platform=adapter.name, status="failed", error=f"Unexpected error: {exc}")


async def publish_everywhere(message: str):
    """Validates the message, then publishes it to every registered platform
    concurrently, returning the aggregated PostingResponse."""
    cta_url = validate_message(message)

    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        results = await asyncio.gather(*(_publish_one(adapter, client, message, cta_url) for adapter in PLATFORM_ADAPTERS))

    return aggregate(list(results))
