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
from app.platforms.discord import DiscordAdapter
from app.platforms.mastodon import MastodonAdapter
from app.platforms.telegram import TelegramAdapter

MESSAGE = "Check out our latest platform https://example.com"
CTA = "https://example.com"


@pytest.fixture
def client():
    return httpx.AsyncClient()


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    """Configures every adapter's required env vars so is_configured() is true for
    these tests; individual tests override specific values as needed."""
    monkeypatch.setattr(settings, "telegram_bot_token", "test-bot-token")
    monkeypatch.setattr(settings, "telegram_chat_id", "12345")
    monkeypatch.setattr(settings, "telegram_channel_username", "testchannel")
    monkeypatch.setattr(settings, "mastodon_instance_url", "https://mastodon.example")
    monkeypatch.setattr(settings, "mastodon_access_token", "test-token")
    monkeypatch.setattr(settings, "discord_webhook_url", "https://discord.com/api/webhooks/1/abc")
    monkeypatch.setattr(settings, "discord_guild_id", "999")
    monkeypatch.setattr(settings, "devto_api_key", "test-api-key")
    monkeypatch.setattr(settings, "bluesky_handle", "test.bsky.social")
    monkeypatch.setattr(settings, "bluesky_app_password", "test-app-password")


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


@respx.mock
async def test_telegram_success(client):
    respx.post("https://api.telegram.org/bottest-bot-token/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})
    )
    result = await TelegramAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "success"
    assert result.posted_url == "https://t.me/testchannel/42"
    assert result.public_access is True


@respx.mock
async def test_telegram_auth_failure(client):
    respx.post("https://api.telegram.org/bottest-bot-token/sendMessage").mock(return_value=httpx.Response(401, json={"ok": False}))
    result = await TelegramAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert result.error == "Authentication failed"


def test_telegram_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "telegram_bot_token", None)
    assert TelegramAdapter().is_configured() is False


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
# Discord
# ---------------------------------------------------------------------------


@respx.mock
async def test_discord_success(client):
    respx.post("https://discord.com/api/webhooks/1/abc", params={"wait": "true"}).mock(
        return_value=httpx.Response(200, json={"id": "111", "channel_id": "222"})
    )
    result = await DiscordAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "success"
    assert result.posted_url == "https://discord.com/channels/999/222/111"
    assert result.public_access is False  # Discord messages require server membership


@respx.mock
async def test_discord_malformed_response(client):
    respx.post("https://discord.com/api/webhooks/1/abc", params={"wait": "true"}).mock(return_value=httpx.Response(200, json={}))
    result = await DiscordAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert "did not include a message id" in result.error


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
    respx.post("https://api.telegram.org/bottest-bot-token/sendMessage").mock(side_effect=httpx.ConnectError("no route to host"))
    result = await TelegramAdapter().publish(client, MESSAGE, CTA)
    assert result.status == "failed"
    assert "Network error" in result.error
