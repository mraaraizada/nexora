from __future__ import annotations

from fastapi import APIRouter

from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import publish_everywhere

router = APIRouter()


@router.post(
    "/posting",
    response_model=PostingResponse,
    summary="Publish a message across all configured platforms",
    description=(
        "Accepts a message (max 200 characters, containing exactly one http/https CTA URL) "
        "and publishes it to every configured platform concurrently. Platform selection is "
        "handled entirely by the server — the caller never specifies which platforms to use. "
        "Each platform is attempted independently: one platform failing (missing credentials, "
        "auth failure, rate limit, network error, ...) never prevents the others from being "
        "attempted. `success` is true only if every attempted platform succeeded."
    ),
)
async def create_posting(payload: PostingRequest) -> PostingResponse:
    return await publish_everywhere(payload.message)
