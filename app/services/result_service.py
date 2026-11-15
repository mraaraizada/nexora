"""Aggregates individual PlatformResult objects into the final PostingResponse."""
from __future__ import annotations

from app.schemas import PlatformResult, PostingResponse


def aggregate(results: list[PlatformResult]) -> PostingResponse:
    # success is true only if every configured/attempted platform succeeded.
    overall_success = len(results) > 0 and all(r.status == "success" for r in results)
    return PostingResponse(success=overall_success, results=results)
