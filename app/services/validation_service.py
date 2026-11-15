"""Message validation, independent of both FastAPI/pydantic and the publishing
pipeline — callable and testable on its own (see tests/test_validation.py)."""
from __future__ import annotations

from app.schemas import MAX_MESSAGE_LENGTH
from app.utils.url_validator import URLValidationError, extract_single_url


def validate_message(message: str) -> str:
    """Returns the single CTA URL in `message` if it's valid, or raises ValueError
    (URLValidationError is a ValueError subclass) with a specific, human-readable reason."""
    stripped = message.strip()
    if not stripped:
        raise ValueError("message must not be empty")
    if len(stripped) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"message must be at most {MAX_MESSAGE_LENGTH} characters, got {len(stripped)}")
    return extract_single_url(stripped)


__all__ = ["validate_message", "URLValidationError"]
