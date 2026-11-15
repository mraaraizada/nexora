from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import PostingRequest
from app.services.validation_service import validate_message


def test_valid_message_passes():
    req = PostingRequest(message="Check out our platform https://example.com")
    assert req.message == "Check out our platform https://example.com"


def test_empty_message_rejected():
    with pytest.raises(ValidationError):
        PostingRequest(message="")


def test_whitespace_only_message_rejected():
    with pytest.raises(ValidationError):
        PostingRequest(message="     ")


def test_message_over_200_chars_rejected():
    long_message = "a" * 195 + " https://example.com"
    assert len(long_message) > 200
    with pytest.raises(ValidationError):
        PostingRequest(message=long_message)


def test_message_at_exactly_200_chars_is_allowed():
    url = " https://example.com"
    padding = "a" * (200 - len(url))
    message = padding + url
    assert len(message) == 200
    req = PostingRequest(message=message)
    assert len(req.message) == 200


def test_missing_cta_rejected():
    with pytest.raises(ValidationError):
        PostingRequest(message="Check out our platform, no link here")


def test_multiple_cta_urls_rejected():
    with pytest.raises(ValidationError):
        PostingRequest(message="See https://example.com and also https://other.com")


def test_invalid_url_scheme_rejected():
    with pytest.raises(ValidationError):
        PostingRequest(message="Check this out ftp://example.com/file")


def test_url_without_scheme_is_not_recognised_as_cta():
    # "example.com" with no scheme should not count as a valid CTA URL.
    with pytest.raises(ValidationError):
        PostingRequest(message="Check out example.com today")


def test_validation_service_returns_the_cta_url_directly():
    url = validate_message("Visit us at https://example.com/promo")
    assert url == "https://example.com/promo"


def test_validation_service_raises_value_error_with_reason():
    with pytest.raises(ValueError, match="exactly one CTA URL"):
        validate_message("No link in this message at all")
