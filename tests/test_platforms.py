"""Platform adapter tests. All external HTTP calls are mocked with respx — these tests
verify each adapter's request construction and response parsing is correct, not real
connectivity to the live platforms (see README for what has/hasn't been live-verified)."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.config import settings
from app.platforms.bluesky import BlueskyAdapter
from app.platforms.devto import DevToAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.telegraph import TelegraphAdapter
from app.platforms.writeas import WriteAsAdapter

MESSAGE = "Check out our latest platform https://example.com"
CTA = "https://example.com"


@pytest.fixture
def client():
    return httpx.AsyncClient()


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    """Configures every adapter's required env vars so is_configured() is true for
    these tests; individual tests override specific values as needed."""
    monkeypatch.setattr(settings, "telegraph_access_token", "test-telegraph-token")
    monkeypatch.setattr(settings, "mastodon_instance_url", "https://mastodon.example")
    monkeypatch.setattr(settings, "mastodon_access_token", "test-token")
    monkeypatch.setattr(settings, "devto_api_key", "test-api-key")
    monkeypatch.setattr(settings, "bluesky_handle", "test.bsky.social")
    monkeypatch.setattr(settings, "bluesky_app_password", "test-app-password")


# ---------------------------------------------------------------------------
# Telegra.ph
# ---------------------------------------------------------------------------


@respx.mock
async def test_telegraph_success_with_configured_token(client):
    # telegraph_access_token is set, so createAccount should NOT be called.
    respx.post("https://api.telegra.ph/createPage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"path": "Test-11-16", "url": "https://telegra.ph/Test-11-16"}})
    )
    result = await TelegraphAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "success"
    assert result.posted_url == "https://telegra.ph/Test-11-16"
    assert result.public_access is True


@respx.mock
async def test_telegraph_creates_account_when_no_token_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "telegraph_access_token", None)
    respx.post("https://api.telegra.ph/createAccount").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"access_token": "generated-token"}})
    )
    respx.post("https://api.telegra.ph/createPage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"path": "Test-11-16", "url": "https://telegra.ph/Test-11-16"}})
    )
    result = await TelegraphAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "success"


@respx.mock
async def test_telegraph_create_page_error_is_a_failure(client):
    respx.post("https://api.telegra.ph/createPage").mock(return_value=httpx.Response(200, json={"ok": False, "error": "CONTENT_TEXT_REQUIRED"}))
    result = await TelegraphAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert result.error == "CONTENT_TEXT_REQUIRED"


def test_telegraph_is_always_configured():
    # Account creation needs no pre-existing credentials at all.
    assert TelegraphAdapter().is_configured() is True


# ---------------------------------------------------------------------------
# Mastodon
# ---------------------------------------------------------------------------


@respx.mock
async def test_mastodon_success(client):
    respx.post("https://mastodon.example/api/v1/statuses").mock(
        return_value=httpx.Response(200, json={"url": "https://mastodon.example/@user/1", "visibility": "public"})
    )
    result = await MastodonAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "success"
    assert result.posted_url == "https://mastodon.example/@user/1"
    assert result.public_access is True


@respx.mock
async def test_mastodon_rate_limited(client):
    respx.post("https://mastodon.example/api/v1/statuses").mock(return_value=httpx.Response(429, json={"error": "too many requests"}))
    result = await MastodonAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert result.error == "Rate limited by platform"


# ---------------------------------------------------------------------------
# Write.as
# ---------------------------------------------------------------------------


@respx.mock
async def test_writeas_success_anonymous(client):
    # Real shape confirmed with one live anonymous POST during development — a
    # successful response includes full_post_url directly.
    respx.post("https://write.as/api/posts").mock(
        return_value=httpx.Response(200, json={"data": {"id": "abc123", "slug": None, "full_post_url": "https://write.as/abc123"}})
    )
    result = await WriteAsAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "success"
    assert result.posted_url == "https://write.as/abc123"
    assert result.public_access is True


@respx.mock
async def test_writeas_falls_back_to_id_slug_when_full_post_url_missing(client):
    respx.post("https://write.as/api/posts").mock(
        return_value=httpx.Response(200, json={"data": {"id": "abc123", "slug": "my-post", "full_post_url": ""}})
    )
    result = await WriteAsAdapter().publish(client, MESSAGE, CTA)
    assert result.posted_url == "https://write.as/abc123/my-post"


@respx.mock
async def test_writeas_content_blocked_is_a_real_failure(client):
    # Live-observed real failure mode: Write.as's content filter rejects a post as a
    # 201/200 with data.id == "contentisblocked" rather than an HTTP error status.
    respx.post("https://write.as/api/posts").mock(
        return_value=httpx.Response(201, json={"data": {"id": "contentisblocked", "slug": None, "full_post_url": ""}})
    )
    result = await WriteAsAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert "content filter" in result.error


@respx.mock
async def test_writeas_abuse_detection_is_not_mislabeled_as_auth_failure(client):
    # Live-observed real failure mode: anonymous posting can be IP-rate-limited with a
    # real 403 {"error_msg": "We've detected abusive activity..."} — must NOT be
    # reported via the generic 401/403 "Authentication failed" mapping, since this
    # platform has no credentials to get wrong in the first place.
    respx.post("https://write.as/api/posts").mock(
        return_value=httpx.Response(403, json={"code": 403, "error_msg": "We've detected abusive activity on your IP address."})
    )
    result = await WriteAsAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert "abuse detection" in result.error
    assert result.error != "Authentication failed"


def test_writeas_is_always_configured():
    # Write.as needs no credentials at all for anonymous posting.
    assert WriteAsAdapter().is_configured() is True


@respx.mock
async def test_writeas_malformed_response(client):
    respx.post("https://write.as/api/posts").mock(return_value=httpx.Response(200, json={"data": {}}))
    result = await WriteAsAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert "did not include a post id" in result.error


# ---------------------------------------------------------------------------
# Dev.to
# ---------------------------------------------------------------------------


@respx.mock
async def test_devto_success(client):
    respx.post("https://dev.to/api/articles").mock(
        return_value=httpx.Response(201, json={"url": "https://dev.to/user/post-1", "published": True})
    )
    result = await DevToAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "success"
    assert result.posted_url == "https://dev.to/user/post-1"
    assert result.public_access is True


@respx.mock
async def test_devto_timeout(client):
    respx.post("https://dev.to/api/articles").mock(side_effect=httpx.TimeoutException("timed out"))
    result = await DevToAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert result.error == "Request timed out"


# ---------------------------------------------------------------------------
# Bluesky
# ---------------------------------------------------------------------------


@respx.mock
async def test_bluesky_success(client):
    respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(
        return_value=httpx.Response(200, json={"accessJwt": "jwt-token", "did": "did:plc:abc123"})
    )
    respx.post("https://bsky.social/xrpc/com.atproto.repo.createRecord").mock(
        return_value=httpx.Response(200, json={"uri": "at://did:plc:abc123/app.bsky.feed.post/xyz"})
    )
    result = await BlueskyAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "success"
    assert result.posted_url == "https://bsky.app/profile/test.bsky.social/post/xyz"
    assert result.public_access is True


@respx.mock
async def test_bluesky_login_failure(client):
    respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(
        return_value=httpx.Response(401, json={"error": "AuthenticationRequired"})
    )
    result = await BlueskyAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert result.error == "Authentication failed"


@respx.mock
async def test_network_failure_is_isolated(client):
    respx.post("https://api.telegra.ph/createPage").mock(side_effect=httpx.ConnectError("no route to host"))
    result = await TelegraphAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert "Network error" in result.error
