"""Finds and validates the single CTA URL required inside a posting message.

Deliberately independent of FastAPI/pydantic specifics so it can be unit-tested and
reused in isolation (see services/validation_service.py and tests/test_validation.py).
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

# Matches http(s) URLs up to the next whitespace character — good enough for a short,
# single-sentence CTA message rather than a general-purpose URL extractor.
_URL_PATTERN = re.compile(r"(?:https?://)\S+", re.IGNORECASE)


class URLValidationError(ValueError):
    """Raised with a human-readable reason for why the message's CTA URL is invalid."""


def find_urls(text: str) -> list[str]:
    return _URL_PATTERN.findall(text)


def is_valid_http_url(candidate: str) -> bool:
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def extract_single_url(text: str) -> str:
    """Returns the one CTA URL in `text`, or raises URLValidationError explaining why
    the message doesn't qualify (none found, more than one, or scheme/format invalid)."""
    candidates = find_urls(text)

    if len(candidates) == 0:
        raise URLValidationError("message must contain exactly one CTA URL, found none")
    if len(candidates) > 1:
        raise URLValidationError(f"message must contain exactly one CTA URL, found {len(candidates)}")

    url = candidates[0]
    if not is_valid_http_url(url):
        raise URLValidationError(f"CTA URL is not a valid http/https URL: {url!r}")
    return url
