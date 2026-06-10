"""
In-memory mock for GMDGoogleSheetsService — no live Google Sheets connection.
"""

from __future__ import annotations

from typing import List

from services.sheets_config import GMD_SHEET_HEADERS


class MockGMDGoogleSheetsService:
    """Returns predetermined sheet rows from get_all_values()."""

    def __init__(self, data_rows: List[List[str]]) -> None:
        self._data_rows = [list(row) for row in data_rows]

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
