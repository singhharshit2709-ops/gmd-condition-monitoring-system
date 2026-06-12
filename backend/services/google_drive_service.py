"""Upload round sheet media attachments to Google Drive."""

from __future__ import annotations

import io
import logging
import os
from typing import Optional

from services.sheets_config import load_service_account_credentials

logger = logging.getLogger("gmd_drive")


class GoogleDriveMediaService:
    """Upload submission media and return a shareable Google Drive URL."""

    def __init__(self) -> None:
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseUpload
        except ImportError as exc:
            raise RuntimeError(
                "google-api-python-client is required for media uploads. "
                "Run: pip install google-api-python-client"
            ) from exc

        creds, credential_source = load_service_account_credentials()
        self._drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        self._MediaIoBaseUpload = MediaIoBaseUpload
        self._folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "").strip()
        logger.info(
            "Google Drive media service initialized (credentials=%s, folder_id=%s)",
            credential_source,
            self._folder_id or "root",
        )

    def upload_submission_media(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        *,
        category: str = "",
        equipment: str = "",
    ) -> str:
        """Upload bytes to Drive, grant link access, and return webViewLink."""
        safe_name = filename.strip() or f"{equipment or 'round'}-media"
        metadata: dict[str, object] = {"name": safe_name}
        if self._folder_id:
            metadata["parents"] = [self._folder_id]

        media = self._MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype=mime_type,
            resumable=False,
        )

        logger.info(
            "Uploading submission media filename=%r mime=%r bytes=%d category=%r equipment=%r",
            safe_name,
            mime_type,
            len(file_bytes),
            category,
            equipment,
        )

        created = (
            self._drive.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id, webViewLink, webContentLink",
                supportsAllDrives=True,
            )
            .execute()
        )

        file_id = created["id"]
        self._drive.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            supportsAllDrives=True,
        ).execute()

        url: Optional[str] = created.get("webViewLink")
        if not url:
            url = f"https://drive.google.com/file/d/{file_id}/view"

        logger.info(
            "Media upload success file_id=%s drive_url=%s filename=%r mime=%r",
            file_id,
            url,
            safe_name,
            mime_type,
        )
        return url
