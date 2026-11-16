"""Opt-in LIVE end-to-end tests: real HTTP calls to real platforms using whatever
credentials are actually in `.env`, through the real running posting pipeline.

These are deliberately NOT part of the default `pytest` run (that suite, per
tests/test_platforms.py and tests/test_posting.py, makes zero real network calls) —
they're a separate, explicit tool for a human to confirm the real end-to-end behavior
this README/docs/platform_research.md's "Honesty note" sections describe, without
relying on someone's word for it. Skipped automatically if no platform is configured.

These are marked `live` and excluded from the default `pytest` run via `pytest.ini`'s
`addopts = -m "not live"` — a plain `pytest` invocation never makes a real network call.

Run explicitly with:
    pytest -m live -v -s

Each test prints the real response it got, including any real `posted_url`, so you can
open it yourself. A platform that isn't configured (no API key/token/handle) simply
reports `"failed: Not configured: ..."`, same as production behavior — this suite
never requires every platform to be set up.
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.services.posting_service import publish_everywhere

pytestmark = pytest.mark.live


def _print_result(label: str, response) -> None:
    print(f"\n--- {label} ---")
    for r in response.results:
        marker = "OK " if r.status == "success" else "FAIL"
        print(f"[{marker}] {r.platform}: {r.status} url={r.posted_url} public_access={r.public_access} error={r.error}")


async def test_live_publish_to_all_configured_platforms():
    """The real test: one real call through the real pipeline, exactly as a real
    client would make it. Does not assert every platform succeeds (that depends on
    which real credentials are actually configured) — it asserts the response is
    well-formed and prints the real outcome for a human to verify."""
    message = "NEXORA automated live-verification test post. https://example.com/nexora-test"
    response = await publish_everywhere(message)
    _print_result("test_live_publish_to_all_configured_platforms", response)

    assert len(response.results) == 5
    for r in response.results:
        # Every result must be well-formed regardless of outcome: a "success" must
        # carry a real posted_url, a "failed" must carry a real error message — never
        # a half-filled or ambiguous result.
        if r.status == "success":
            assert r.posted_url, f"{r.platform} reported success with no posted_url"
        else:
            assert r.error, f"{r.platform} reported failure with no error message"


async def test_live_devto_public_access_is_confirmed_not_assumed():
    """Specifically re-tests the real anomaly documented in
    docs/platform_research.md: Dev.to's own `published` response field was observed to
    disagree with actual public readability. Skipped if no real Dev.to key is set."""
    if not settings.devto_api_key:
        pytest.skip("DEVTO_API_KEY not configured — skipping live Dev.to check")

    from app.platforms.devto import DevToAdapter
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        result = await DevToAdapter().publish(client, "NEXORA live public_access check. https://example.com", "https://example.com")

    print(f"\n--- Dev.to public_access check ---\nstatus={result.status} url={result.posted_url} public_access={result.public_access}")
    assert result.status == "success"
    assert result.posted_url
    # public_access here is independently confirmed via a real GET to Dev.to's public
    # read endpoint inside the adapter itself (see app/platforms/devto.py) - this test
    # just surfaces whatever that real, live check determined, rather than re-asserting
    # a fixed expected value (which could become stale if Dev.to's moderation behavior
    # for this specific test account changes over time).
