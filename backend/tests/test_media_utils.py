"""Tests for submission media parsing."""

from __future__ import annotations

import base64

import pytest

from services.media_utils import has_media_attachment, parse_submission_media

SAMPLE_BYTES = b"fake-image-content"
SAMPLE_DATA_URL = (
    "data:image/jpeg;base64," + base64.b64encode(SAMPLE_BYTES).decode("ascii")
)


class TestMediaUtils:
    def test_has_media_attachment(self):
        assert has_media_attachment("") is False
        assert has_media_attachment("   ") is False
        assert has_media_attachment(SAMPLE_DATA_URL) is True

    def test_parse_data_url(self):
        file_bytes, mime_type, filename = parse_submission_media(
            SAMPLE_DATA_URL,
            media_name="verify.jpg",
        )
        assert file_bytes == SAMPLE_BYTES
        assert mime_type == "image/jpeg"
        assert filename == "verify.jpg"

    def test_parse_invalid_base64_raises(self):
        with pytest.raises(ValueError, match="valid base64"):
            parse_submission_media("not-valid-base64!!!")
