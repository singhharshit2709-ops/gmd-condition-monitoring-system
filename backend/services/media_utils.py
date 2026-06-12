"""Parse submission media payloads from the Add Reading frontend."""

from __future__ import annotations

import base64
import binascii
import mimetypes
import re
from typing import Tuple

_DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$", re.DOTALL)


def has_media_attachment(media_data: str | None) -> bool:
    return bool(media_data and str(media_data).strip())


def parse_submission_media(
    media_data: str,
    media_type: str = "",
    media_name: str = "",
) -> Tuple[bytes, str, str]:
    """
    Decode a data URL or raw base64 media payload from the client.
    Returns (file_bytes, mime_type, filename).
    """
    raw = str(media_data).strip()
    if not raw:
        raise ValueError("Media data is empty.")

    mime = str(media_type or "").strip()
    name = str(media_name or "").strip()

    match = _DATA_URL_RE.match(raw)
    if match:
        mime = mime or match.group("mime").strip()
        encoded = match.group("data")
    elif raw.startswith("base64,"):
        encoded = raw.split(",", 1)[1]
    else:
        encoded = raw

    try:
        file_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Media data is not valid base64.") from exc

    if not file_bytes:
        raise ValueError("Media data decoded to an empty file.")

    if not mime:
        mime = "application/octet-stream"

    if not name:
        extension = mimetypes.guess_extension(mime.split(";")[0].strip()) or ""
        name = f"submission-media{extension}"

    return file_bytes, mime, name
