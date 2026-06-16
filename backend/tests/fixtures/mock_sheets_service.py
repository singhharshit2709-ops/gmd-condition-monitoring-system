"""
In-memory mock for GMDGoogleSheetsService — no live Google Sheets connection.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from services.sheets_row_model import (
    GMD_SHEET_HEADERS_LEGACY,
    ReadingRowRecord,
    build_reading_row,
)


class MockGMDGoogleSheetsService:
    """Returns predetermined sheet rows from get_all_values()."""

    def __init__(
        self,
        data_rows: List[List[str]],
        *,
        append_v2_raises: Optional[Exception] = None,
        header_row: List[str] | None = None,
    ) -> None:
        self._data_rows = [list(row) for row in data_rows]
        self._header_row = list(header_row or GMD_SHEET_HEADERS_LEGACY)
        self._append_v2_raises = append_v2_raises
        self.append_v2_calls: List[Dict[str, Any]] = []

    def get_all_values(self) -> List[List[str]]:
        return [list(self._header_row)] + self._data_rows

    def get_all_records(self) -> List[dict]:
        header = self._header_row
        records = []
        for row in self._data_rows:
            padded = row + [""] * (len(header) - len(row))
            records.append(dict(zip(header, padded)))
        return records

    def clear_cache(self) -> None:
        return None

    @staticmethod
    def cache_clear() -> None:
        return None

    def append_v2_readings(
        self,
        category: str,
        equipment: str,
        readings: Dict[str, float],
        parameter_locations: Dict[str, str],
        verified_by: str = "",
        remarks: str = "",
        entry_source: str = "Web",
        media_name: str = "",
        media_type: str = "",
        media_url: str = "",
        area_tank: str = "",
        tag_no: str = "",
        parameter_units: Dict[str, str] | None = None,
        submission_id: str = "",
    ) -> Dict[str, Any]:
        if self._append_v2_raises is not None:
            raise self._append_v2_raises

        self.append_v2_calls.append(
            {
                "category": category,
                "equipment": equipment,
                "readings": dict(readings),
                "parameter_locations": dict(parameter_locations),
                "verified_by": verified_by,
                "remarks": remarks,
                "entry_source": entry_source,
                "media_name": media_name,
                "media_type": media_type,
                "media_url": media_url,
                "area_tank": area_tank,
                "tag_no": tag_no,
                "parameter_units": dict(parameter_units or {}),
                "submission_id": submission_id,
            }
        )

        timestamp = "2026-06-10 12:00:00"
        resolved_submission_id = submission_id.strip() or str(uuid.uuid4())
        units = parameter_units or {}

        for parameter_key, value in readings.items():
            record = ReadingRowRecord(
                submission_id=resolved_submission_id,
                timestamp=timestamp,
                area_tank=area_tank,
                category=category,
                equipment=equipment,
                tag_no=tag_no,
                parameter_key=str(parameter_key),
                parameter_display_name=parameter_locations.get(parameter_key, ""),
                unit=units.get(parameter_key, ""),
                value=float(value),
                status="NORMAL",
                verified_by=verified_by,
                remarks=remarks,
                media_name=media_name,
                media_type=media_type,
                media_url=media_url,
                entry_source=entry_source,
            )
            self._data_rows.append(build_reading_row(record, self._header_row))

        return {
            "success": True,
            "rows_appended": len(readings),
            "timestamp": timestamp,
            "submission_id": resolved_submission_id,
        }


class MockGoogleDriveMediaService:
    """Mock Drive uploader for V2 submit tests."""

    def __init__(
        self,
        *,
        upload_raises: Optional[Exception] = None,
        media_url: str = "https://drive.google.com/file/d/mock-file-id/view",
    ) -> None:
        self._upload_raises = upload_raises
        self.media_url = media_url
        self.upload_calls: List[Dict[str, Any]] = []

    def upload_submission_media(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        *,
        category: str = "",
        equipment: str = "",
    ) -> str:
        self.upload_calls.append(
            {
                "file_bytes": file_bytes,
                "filename": filename,
                "mime_type": mime_type,
                "category": category,
                "equipment": equipment,
            }
        )
        if self._upload_raises is not None:
            raise self._upload_raises
        return self.media_url
