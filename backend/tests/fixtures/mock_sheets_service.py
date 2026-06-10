"""
In-memory mock for GMDGoogleSheetsService — no live Google Sheets connection.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.sheets_config import GMD_SHEET_HEADERS


class MockGMDGoogleSheetsService:
    """Returns predetermined sheet rows from get_all_values()."""

    def __init__(
        self,
        data_rows: List[List[str]],
        *,
        append_v2_raises: Optional[Exception] = None,
    ) -> None:
        self._data_rows = [list(row) for row in data_rows]
        self._append_v2_raises = append_v2_raises
        self.append_v2_calls: List[Dict[str, Any]] = []

    def get_all_values(self) -> List[List[str]]:
        return [list(GMD_SHEET_HEADERS)] + self._data_rows

    def get_all_records(self) -> List[dict]:
        header = GMD_SHEET_HEADERS
        records = []
        for row in self._data_rows:
            padded = row + [""] * (len(header) - len(row))
            records.append(dict(zip(header, padded)))
        return records

    def clear_cache(self) -> None:
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
            }
        )
        return {
            "success": True,
            "rows_appended": len(readings),
            "timestamp": "2026-06-10 12:00:00",
        }
