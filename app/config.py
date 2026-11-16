"""Environment-based configuration. Every value defaults to None/empty so a missing
credential degrades that one platform to a "not configured" failure instead of crashing
the whole application (see services/posting_service.py)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # Optional — a persistent Telegra.ph author identity; a fresh one is created
    # automatically on every publish if this is left unset.
    telegraph_access_token: str | None = os.getenv("TELEGRAPH_ACCESS_TOKEN") or None

    mastodon_instance_url: str = (os.getenv("MASTODON_INSTANCE_URL") or "https://mastodon.social").rstrip("/")
    mastodon_access_token: str | None = os.getenv("MASTODON_ACCESS_TOKEN") or None

    devto_api_key: str | None = os.getenv("DEVTO_API_KEY") or None

    # Optional — Write.as supports fully anonymous posting with no token at all.
    writeas_access_token: str | None = os.getenv("WRITEAS_ACCESS_TOKEN") or None

    bluesky_handle: str | None = os.getenv("BLUESKY_HANDLE") or None
    bluesky_app_password: str | None = os.getenv("BLUESKY_APP_PASSWORD") or None

    request_timeout_seconds: float = float(os.getenv("NEXORA_REQUEST_TIMEOUT", "10"))


settings = Settings()
