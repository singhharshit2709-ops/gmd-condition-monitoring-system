"""
Validate verified_by / photo metadata flow: request → doc → Sheets row.
Run: python backend/scripts/test_reading_metadata_flow.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from server import (  # noqa: E402
    MotorResult,
    ParameterStatus,
    _SHEETS_HEADERS,
    _batch_meta_from_request,
    _merge_reading_source,
    _row_from_doc,
    reading_doc_from_result,
)


def _motor_result(motor: str = "Lehr Fan 1") -> MotorResult:
    return MotorResult(
        motor=motor,
        overall_status="Normal",
        parameters={
            "current": ParameterStatus(
                value=10.0,
                normal_limit=12.0,
                warning_limit=15.0,
                status="Normal",
            )
        },
        timestamp="2026-05-26T12:00:00+00:00",
    )


def test_bulk_metadata_flow() -> None:
    """Simulate BulkEntry POST body → doc → Sheets row."""
    request_body = {
        "plant": "GT",
        "machine": "G1 Lehr",
        "technician": "Rajesh Kumar",
        "verified_by": "Rajesh Kumar",
        "photo_base64": "data:image/jpeg;base64,/9j/test",
        "photo_filename": "field-photo.jpg",
        "entry_source": "Field",
        "notes": "Routine inspection",
        "readings": [{"motor": "Lehr Fan 1", "current": 10.0}],
    }

    batch_meta = _batch_meta_from_request(request_body)
    assert batch_meta["technician"] == "Rajesh Kumar"
    assert batch_meta["photo_filename"] == "field-photo.jpg"
    assert batch_meta["notes"] == "Routine inspection"

    motor_item = request_body["readings"][0]
    source = _merge_reading_source(motor_item, batch_meta)
    doc = reading_doc_from_result("GT", "G1 Lehr", _motor_result(), source, bulk_entry=True)

    assert doc["verified_by"] == "Rajesh Kumar", f"verified_by={doc['verified_by']!r}"
    assert doc["has_photo"] is True, f"has_photo={doc['has_photo']!r}"
    assert doc["photo_filename"] == "field-photo.jpg"
    assert doc["photo"] == "data:image/jpeg;base64,/9j/test"
    assert doc["notes"] == "Routine inspection"
    assert doc["entry_source"] == "Field"

    row = _row_from_doc(doc)
    assert len(row) == len(_SHEETS_HEADERS)
    header_index = {name: idx for idx, name in enumerate(_SHEETS_HEADERS)}

    assert row[header_index["verified_by"]] == "Rajesh Kumar"
    assert row[header_index["has_photo"]] == "TRUE"
    assert row[header_index["photo_filename"]] == "field-photo.jpg"
    assert row[header_index["notes"]] == "Routine inspection"
    assert "None" not in row, f"literal None in row: {row}"
    assert "False" not in row, f"literal False in row: {row}"

    print("PASS bulk metadata flow")


def test_single_entry_metadata_flow() -> None:
    """Simulate ConditionMonitoring POST body with batch_meta fallback."""
    request_body = {
        "plant": "GT",
        "machine": "G1 Lehr",
        "motor": "Lehr Fan 1",
        "current": 10.0,
        "verified_by": "Priya S",
        "notes": "Single reading note",
        "photo_base64": "data:image/png;base64,abc",
        "photo_filename": "snap.png",
        "entry_source": "Field",
    }

    batch_meta = _batch_meta_from_request(request_body)
    source = _merge_reading_source(request_body, batch_meta)
    doc = reading_doc_from_result("GT", "G1 Lehr", _motor_result(), source, bulk_entry=False)

    assert doc["verified_by"] == "Priya S"
    assert doc["has_photo"] is True
    assert doc["photo_filename"] == "snap.png"
    assert doc["notes"] == "Single reading note"

    row = _row_from_doc(doc)
    assert row[_SHEETS_HEADERS.index("verified_by")] == "Priya S"
    assert row[_SHEETS_HEADERS.index("has_photo")] == "TRUE"
    print("PASS single-entry metadata flow")


def test_empty_metadata_no_none_literals() -> None:
    """No photo / no verified_by must not write literal None or False strings."""
    source = _merge_reading_source({"motor": "Lehr Fan 1"}, {})
    doc = reading_doc_from_result("GT", "G1 Lehr", _motor_result(), source, bulk_entry=True)

    assert doc["verified_by"] is None
    assert doc["has_photo"] is False

    row = _row_from_doc(doc)
    assert row[_SHEETS_HEADERS.index("verified_by")] == ""
    assert row[_SHEETS_HEADERS.index("has_photo")] == "FALSE"
    assert "None" not in row
    print("PASS empty metadata (no None literals in row)")


def test_sheets_headers_complete() -> None:
    required = {
        "verified_by",
        "notes",
        "photo_filename",
        "photo",
        "has_photo",
        "entry_source",
        "bulk_entry",
    }
    missing = required - set(_SHEETS_HEADERS)
    assert not missing, f"Missing headers: {missing}"
    print(f"PASS _SHEETS_HEADERS ({len(_SHEETS_HEADERS)} columns)")


def main() -> int:
    test_sheets_headers_complete()
    test_bulk_metadata_flow()
    test_single_entry_metadata_flow()
    test_empty_metadata_no_none_literals()
    print("\nAll metadata flow checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
