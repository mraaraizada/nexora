"""Orchestration tests: verifies concurrent publishing, per-platform isolation and
correct result aggregation, plus the real FastAPI endpoint's validation responses."""
from __future__ import annotations

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.posting_service import publish_everywhere

MESSAGE = "Check out our latest platform https://example.com"


@pytest.fixture(autouse=True)
def configured_all(monkeypatch):
    monkeypatch.setattr(settings, "telegraph_access_token", "tok")
    monkeypatch.setattr(settings, "mastodon_instance_url", "https://mastodon.example")
    monkeypatch.setattr(settings, "mastodon_access_token", "tok")
    monkeypatch.setattr(settings, "devto_api_key", "tok")
    monkeypatch.setattr(settings, "bluesky_handle", "test.bsky.social")
    monkeypatch.setattr(settings, "bluesky_app_password", "tok")


def _mock_all_success():
    respx.post("https://api.telegra.ph/createPage").mock(return_value=httpx.Response(200, json={"ok": True, "result": {"path": "p", "url": "https://telegra.ph/p"}}))
    respx.post("https://mastodon.example/api/v1/statuses").mock(return_value=httpx.Response(200, json={"url": "https://mastodon.example/@u/1", "visibility": "public"}))
    respx.post("https://write.as/api/posts").mock(return_value=httpx.Response(200, json={"data": {"id": "1", "slug": None}}))
    respx.post("https://dev.to/api/articles").mock(return_value=httpx.Response(201, json={"url": "https://dev.to/u/p", "published": True}))
    respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(return_value=httpx.Response(200, json={"accessJwt": "j", "did": "did:plc:1"}))
    respx.post("https://bsky.social/xrpc/com.atproto.repo.createRecord").mock(return_value=httpx.Response(200, json={"uri": "at://did:plc:1/app.bsky.feed.post/r"}))


@respx.mock
async def test_all_platforms_succeed():
    _mock_all_success()
    response = await publish_everywhere(MESSAGE)
    assert response.success is True
    assert len(response.results) == 5
    assert all(r.status == "success" for r in response.results)


@respx.mock
async def test_one_platform_fails_rest_still_attempted():
    _mock_all_success()
    # Override Telegra.ph's mock to fail; the other four mocks above remain successful.
    respx.post("https://api.telegra.ph/createPage").mock(return_value=httpx.Response(200, json={"ok": False, "error": "FLOOD_WAIT"}))

    response = await publish_everywhere(MESSAGE)
    assert response.success is False
    by_platform = {r.platform: r for r in response.results}
    assert by_platform["Telegra.ph"].status == "failed"
    assert by_platform["Mastodon"].status == "success"
    assert by_platform["Write.as"].status == "success"
    assert by_platform["Dev.to"].status == "success"
    assert by_platform["Bluesky"].status == "success"


@respx.mock
async def test_multiple_platforms_fail_partial_success():
    _mock_all_success()
    respx.post("https://api.telegra.ph/createPage").mock(return_value=httpx.Response(500))
    respx.post("https://mastodon.example/api/v1/statuses").mock(side_effect=httpx.TimeoutException("timeout"))

    response = await publish_everywhere(MESSAGE)
    assert response.success is False
    statuses = {r.platform: r.status for r in response.results}
    assert statuses["Telegra.ph"] == "failed"
    assert statuses["Mastodon"] == "failed"
    assert statuses["Write.as"] == "success"
    assert statuses["Dev.to"] == "success"
    assert statuses["Bluesky"] == "success"


@respx.mock
async def test_all_platforms_fail():
    respx.post("https://api.telegra.ph/createPage").mock(return_value=httpx.Response(500))
    respx.post("https://mastodon.example/api/v1/statuses").mock(return_value=httpx.Response(500))
    respx.post("https://write.as/api/posts").mock(return_value=httpx.Response(500))
    respx.post("https://dev.to/api/articles").mock(return_value=httpx.Response(500))
    respx.post("https://bsky.social/xrpc/com.atproto.server.createSession").mock(return_value=httpx.Response(500))

    response = await publish_everywhere(MESSAGE)
    assert response.success is False
    assert all(r.status == "failed" for r in response.results)
    assert len(response.results) == 5


@respx.mock
def test_not_configured_platforms_report_failed_not_crash(monkeypatch):
    # Simulate an unconfigured platform (Mastodon, which does require a token unlike
    # Telegra.ph/Write.as) and confirm the API never 500s because of it. Every other
    # platform is still mocked below so this test makes no real network calls at all.
    monkeypatch.setattr(settings, "mastodon_access_token", None)
    _mock_all_success()

    with TestClient(app) as test_client:
        resp = test_client.post("/posting", json={"message": MESSAGE})
    assert resp.status_code == 200
    assert resp.json()["results"][1]["platform"] == "Mastodon"
    assert resp.json()["results"][1]["status"] == "failed"


# ---------------------------------------------------------------------------
# Real HTTP-level validation tests against the FastAPI route
# ---------------------------------------------------------------------------

client = TestClient(app)


def test_route_rejects_empty_message():
    resp = client.post("/posting", json={"message": ""})
    assert resp.status_code == 422


def test_route_rejects_message_over_200_chars():
    resp = client.post("/posting", json={"message": "a" * 195 + " https://example.com"})
    assert resp.status_code == 422


def test_route_rejects_missing_cta():
    resp = client.post("/posting", json={"message": "no link here at all"})
    assert resp.status_code == 422


def test_route_rejects_multiple_ctas():
    resp = client.post("/posting", json={"message": "https://a.com and https://b.com"})
    assert resp.status_code == 422


def test_docs_endpoint_is_available():
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_openapi_schema_is_available():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"] == "NEXORA — Connected Publishing Infrastructure"
