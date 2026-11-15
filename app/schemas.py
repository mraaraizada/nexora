import datetime as _dt

from pydantic import BaseModel, Field, field_validator

from app.utils.url_validator import extract_single_url

MAX_MESSAGE_LENGTH = 200


class PostingRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Message to publish, max 200 characters, must contain exactly one http(s) CTA URL.")

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty")
        if len(stripped) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"message must be at most {MAX_MESSAGE_LENGTH} characters, got {len(stripped)}")
        # Raises ValueError itself with a specific reason (missing / multiple / invalid URL).
        extract_single_url(stripped)
        return stripped


class PlatformResult(BaseModel):
    platform: str
    status: str  # "success" | "failed"
    posted_url: str | None = None
    public_access: bool = False
    date: _dt.date | None = None
    time: _dt.time | None = None
    error: str | None = None


class PostingResponse(BaseModel):
    success: bool
    results: list[PlatformResult]
