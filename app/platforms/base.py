"""Common interface every platform adapter implements.

Each adapter owns its own authentication, request construction, response parsing and
error handling — the FastAPI route and the posting service never touch a platform's
HTTP/auth details directly (see services/posting_service.py)."""
from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.schemas import PlatformResult
from app.utils.time_utils import now_utc, split_date_time


class PlatformAdapter(ABC):
    #: Human-readable platform name used in the response's "platform" field.
    name: str

    def is_configured(self) -> bool:
        """Whether this adapter has the credentials it needs. Overridden per adapter."""
        return True

    def missing_config_error(self) -> str:
        """Human-readable reason this adapter isn't configured, used verbatim as the
        PlatformResult.error when is_configured() is False."""
        return "Not configured"

    @abstractmethod
    async def _do_publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> tuple[str, bool]:
        """Performs the real publish call. Must return (posted_url, public_access) on
        success, or raise PlatformPublishError (or let httpx raise) on failure."""
        raise NotImplementedError

    async def publish(self, client: httpx.AsyncClient, message: str, cta_url: str) -> PlatformResult:
        """Template method: every adapter's publish() funnels through here so the
        success/failure result shape, timestamps and error handling are consistent
        across all five platforms, while each adapter only implements _do_publish()."""
        if not self.is_configured():
            return PlatformResult(platform=self.name, status="failed", error=self.missing_config_error())

        try:
            posted_url, public_access = await self._do_publish(client, message, cta_url)
        except PlatformPublishError as exc:
            return PlatformResult(platform=self.name, status="failed", error=str(exc))
        except httpx.TimeoutException:
            return PlatformResult(platform=self.name, status="failed", error="Request timed out")
        except httpx.HTTPStatusError as exc:
            return PlatformResult(platform=self.name, status="failed", error=self._describe_http_error(exc))
        except httpx.HTTPError as exc:
            return PlatformResult(platform=self.name, status="failed", error=f"Network error: {exc}")

        d, t = split_date_time(now_utc())
        return PlatformResult(platform=self.name, status="success", posted_url=posted_url, public_access=public_access, date=d, time=t)

    @staticmethod
    def _describe_http_error(exc: httpx.HTTPStatusError) -> str:
        status = exc.response.status_code
        if status in (401, 403):
            return "Authentication failed"
        if status == 429:
            return "Rate limited by platform"
        try:
            body = exc.response.json()
        except ValueError:
            body = exc.response.text[:200]
        return f"HTTP {status}: {body}"


class PlatformPublishError(Exception):
    """Raised by an adapter's _do_publish() for a platform-specific failure that isn't
    already a well-known httpx exception (e.g. the platform returned 200 with an
    error payload, or a response field the adapter needs was missing)."""
