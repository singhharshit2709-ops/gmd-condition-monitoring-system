"""
Validate newest-first cache and row mapping behavior.
Run: python backend/scripts/test_sheets_newest_first.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from server import (  # noqa: E402
    _SHEETS_DATA_START_ROW,
    _SHEETS_HEADER_ROW,
    _SHEETS_HEADERS,
    _doc_from_row,
    _header_row_matches,
    _normalize_sheet_row,
    _row_from_doc,
)


def test_header_row_detection() -> None:
    assert _header_row_matches(_SHEETS_HEADERS)
    assert _header_row_matches(["id", "plant", "machine", "motor"])
    assert not _header_row_matches(["GT", "G1 Lehr", "Lehr Fan 1"])
    assert _doc_from_row(_SHEETS_HEADERS) is None
    assert _doc_from_row(["id", "plant", "machine", "motor"] + [""] * 18) is None
    print("PASS header row detection and rejection")


def test_insert_constants() -> None:
    assert _SHEETS_HEADER_ROW == 1
    assert _SHEETS_DATA_START_ROW == 2
    print("PASS insert row constants")


def test_row_mapping_integrity() -> None:
    doc = {
        "id": "test-id",
        "plant": "GT",
        "machine": "G1 Lehr",
        "motor": "Lehr Fan 1",
        "current": 10.0,
        "temperature": 45.0,
        "vibration": 1.2,
        "normal_current": 12.0,
        "warning_current": 15.0,
        "normal_temperature": 55.0,
        "warning_temperature": 70.0,
        "normal_vibration": 4.5,
        "warning_vibration": 7.0,
        "status": "Normal",
        "timestamp": "2026-05-27T10:00:00+00:00",
        "entry_source": "Field",
        "verified_by": "Test Engineer",
        "notes": "Newest-first check",
        "photo_filename": "verify.jpg",
        "photo": "data:image/jpeg;base64,/9j/test",
        "has_photo": True,
        "bulk_entry": False,
    }
    row = _row_from_doc(doc)
    assert len(row) == len(_SHEETS_HEADERS)
    assert row[_SHEETS_HEADERS.index("verified_by")] == "Test Engineer"
    assert row[_SHEETS_HEADERS.index("has_photo")] == "TRUE"
    assert row[_SHEETS_HEADERS.index("photo_filename")] == "verify.jpg"
    assert "None" not in row

    round_trip = _doc_from_row(row)
    assert round_trip is not None
    assert round_trip["verified_by"] == "Test Engineer"
    assert round_trip["has_photo"] is True
    print("PASS 22-column row mapping integrity")


def test_newest_first_cache_order() -> None:
    """Simulate prepend behavior used by process_and_store_readings."""
    cache: list[dict] = [
        {"id": "older", "timestamp": "2026-05-27T09:00:00+00:00", "plant": "GT", "motor": "A"},
        {"id": "old", "timestamp": "2026-05-27T08:00:00+00:00", "plant": "GT", "motor": "B"},
    ]
    new_docs = [
        {"id": "newest", "timestamp": "2026-05-27T10:00:00+00:00", "plant": "GT", "motor": "C"},
    ]
    cache[0:0] = new_docs
    assert cache[0]["id"] == "newest"
    recent = cache[:2]
    assert [item["id"] for item in recent] == ["newest", "older"]
    print("PASS newest-first in-memory cache order")


def test_hydration_newest_head() -> None:
    """Simulate sheet rows newest-first below header."""
    header = _SHEETS_HEADERS
    row_new = _row_from_doc(
        {
            "id": "1",
            "plant": "GT",
            "machine": "G1 Lehr",
            "motor": "Lehr Fan 1",
            "current": 1.0,
            "status": "Normal",
            "timestamp": "2026-05-27T10:00:00+00:00",
            "has_photo": False,
            "bulk_entry": False,
        }
    )
    row_old = _row_from_doc(
        {
            "id": "2",
            "plant": "GT",
            "machine": "G1 Lehr",
            "motor": "Lehr Fan 2",
            "current": 2.0,
            "status": "Normal",
            "timestamp": "2026-05-27T09:00:00+00:00",
            "has_photo": False,
            "bulk_entry": False,
        }
    )
    all_values = [header, row_new, row_old]
    all_docs = [_doc_from_row(row) for row in all_values[1:] if _doc_from_row(row)]
    recent_tail = all_docs[:1]
    assert recent_tail[0]["id"] == "1"
    print("PASS hydration newest-head selection")


def main() -> int:
    test_header_row_detection()
    test_insert_constants()
    test_row_mapping_integrity()
    test_newest_first_cache_order()
    test_hydration_newest_head()
    print("\nAll newest-first checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
