"""
Canonical Google Sheets row model for GMD Readings persistence.

Single source of truth for column order, row building, and header-aware parsing.
Supports legacy Title Case layouts while writing new rows in snake_case.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, fields
from enum import Enum
from typing import Any, Mapping

logger = logging.getLogger("gmd_condition_monitoring.sheets_row_model")

_READING_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")

# ---------------------------------------------------------------------------
# Canonical column order (new writes)
# ---------------------------------------------------------------------------

GMD_SHEET_HEADERS = [
    "submission_id",
    "timestamp",
    "area_tank",
    "category",
    "equipment",
    "tag_no",
    "parameter_key",
    "parameter_display_name",
    "unit",
    "value",
    "status",
    "verified_by",
    "remarks",
    "media_name",
    "media_type",
    "media_url",
    "entry_source",
]

# ---------------------------------------------------------------------------
# Legacy layouts (read-only compatibility)
# ---------------------------------------------------------------------------

GMD_SHEET_HEADERS_LEGACY = [
    "Timestamp",
    "Category",
    "Equipment",
    "Parameter",
    "Location",
    "Value",
    "Status",
    "Verified By",
    "Remarks",
    "Entry Source",
]

GMD_SHEET_MEDIA_HEADERS = [
    "Media Name",
    "Media Type",
    "Media URL",
]

GMD_SHEET_HEADERS_LEGACY_V2 = [
    "Timestamp",
    "Area / Tank",
    "Category",
    "Equipment",
    "Tag No",
    "Parameter",
    "Location",
    "Value",
    "Unit",
    "Status",
    "Verified By",
    "Remarks",
    "Media Name",
    "Media Type",
    "Media URL",
    "Entry Source",
    "Submission ID",
]

# GT motor-monitoring headers (server.py legacy) — GMD rows were often written here by position
GMD_SHEET_HEADERS_LEGACY_GT = [
    "id",
    "plant",
    "machine",
    "motor",
    "current",
    "temperature",
    "vibration",
    "normal_current",
    "warning_current",
    "normal_temperature",
    "warning_temperature",
    "normal_vibration",
    "warning_vibration",
    "status",
    "timestamp",
    "entry_source",
    "verified_by",
    "notes",
    "photo_filename",
    "photo",
    "has_photo",
    "bulk_entry",
]

# Map worksheet header labels (any supported schema) → canonical field keys
_HEADER_FIELD_ALIASES: dict[str, str] = {
    "submission_id": "submission_id",
    "Submission ID": "submission_id",
    "timestamp": "timestamp",
    "Timestamp": "timestamp",
    "area_tank": "area_tank",
    "Area / Tank": "area_tank",
    "category": "category",
    "Category": "category",
    "equipment": "equipment",
    "Equipment": "equipment",
    "tag_no": "tag_no",
    "Tag No": "tag_no",
    "parameter_key": "parameter_key",
    "Parameter": "parameter_key",
    "parameter_display_name": "parameter_display_name",
    "Location": "parameter_display_name",
    "unit": "unit",
    "Unit": "unit",
    "value": "value",
    "Value": "value",
    "status": "status",
    "Status": "status",
    "verified_by": "verified_by",
    "Verified By": "verified_by",
    "remarks": "remarks",
    "Remarks": "remarks",
    "media_name": "media_name",
    "Media Name": "media_name",
    "media_type": "media_type",
    "Media Type": "media_type",
    "media_url": "media_url",
    "Media URL": "media_url",
    "entry_source": "entry_source",
    "Entry Source": "entry_source",
}


class SheetSchema(str, Enum):
    CANONICAL = "canonical"
    LEGACY_V2 = "legacy_v2"
    LEGACY_V1 = "legacy_v1"
    LEGACY_GT = "legacy_gt"


@dataclass(frozen=True)
class ReadingRowRecord:
    """Normalized reading row used for Google Sheets persistence."""

    submission_id: str = ""
    timestamp: str = ""
    area_tank: str = ""
    category: str = ""
    equipment: str = ""
    tag_no: str = ""
    parameter_key: str = ""
    parameter_display_name: str = ""
    unit: str = ""
    value: str | float | int = ""
    status: str = "NORMAL"
    verified_by: str = ""
    remarks: str = ""
    media_name: str = ""
    media_type: str = ""
    media_url: str = ""
    entry_source: str = "Web"

    def as_field_dict(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for field in fields(self):
            raw = getattr(self, field.name)
            if raw is None:
                result[field.name] = ""
            elif field.name == "value":
                result[field.name] = str(raw)
            else:
                result[field.name] = str(raw)
        return result

    def log_context(self) -> str:
        return (
            f"submission_id={self.submission_id} timestamp={self.timestamp} "
            f"area_tank={self.area_tank!r} category={self.category!r} "
            f"equipment={self.equipment!r} tag_no={self.tag_no!r} "
            f"parameter_key={self.parameter_key!r} verified_by={self.verified_by!r}"
        )


def _is_legacy_gt_header(headers: list[str]) -> bool:
    """True when row 1 matches the GT motor sheet layout (id/plant/machine/motor)."""
    if len(headers) < 4:
        return False
    if headers[0].lower() == "id":
        return True
    return (
        headers[1].lower() == "plant"
        and headers[2].lower() == "machine"
        and headers[3].lower() == "motor"
    )


def detect_sheet_schema(headers: list[str]) -> SheetSchema:
    normalized = [str(cell).strip() for cell in headers]
    cleaned = [cell for cell in normalized if cell]
    if not cleaned:
        return SheetSchema.LEGACY_V1

    if cleaned[0] == "submission_id":
        return SheetSchema.CANONICAL

    if len(cleaned) > 1 and cleaned[1] == "Area / Tank":
        return SheetSchema.LEGACY_V2

    if _is_legacy_gt_header(normalized):
        return SheetSchema.LEGACY_GT

    if cleaned[0] == "Timestamp":
        return SheetSchema.LEGACY_V1

    return SheetSchema.LEGACY_V1


def is_gmd_readings_schema(schema: SheetSchema) -> bool:
    """True for any GMD Readings layout (including GT-misaligned legacy)."""
    return schema in {
        SheetSchema.CANONICAL,
        SheetSchema.LEGACY_V2,
        SheetSchema.LEGACY_V1,
        SheetSchema.LEGACY_GT,
    }


def is_modern_gmd_header(headers: list[str]) -> bool:
    """True for canonical or legacy_v2 header layouts."""
    schema = detect_sheet_schema(headers)
    return schema in {SheetSchema.CANONICAL, SheetSchema.LEGACY_V2}


def header_column_map(headers: list[str]) -> dict[str, int]:
    return {
        str(name).strip(): index
        for index, name in enumerate(headers)
        if str(name).strip()
    }


def empty_reading_field_dict() -> dict[str, str]:
    return {field.name: "" for field in fields(ReadingRowRecord)}


def is_canonical_reading_slice(cells: list[str]) -> bool:
    """True when a 17-column window looks like a canonical GMD reading row."""
    width = len(GMD_SHEET_HEADERS)
    padded = list(cells[:width]) + [""] * max(0, width - len(cells))
    padded = padded[:width]
    timestamp = padded[1].strip()
    equipment = padded[4].strip()
    parameter_key = padded[6].strip()
    return bool(
        _READING_TIMESTAMP_RE.match(timestamp) and equipment and parameter_key
    )


def extract_reading_rows_from_worksheet(
    all_values: list[list[str]],
) -> list[list[str]]:
    """
    Collect canonical reading rows from worksheet data.

    Repairs horizontal drift where append_rows wrote successive batches into
    later columns instead of column A.
    """
    if not all_values:
        return []

    width = len(GMD_SHEET_HEADERS)
    recovered: list[list[str]] = []
    seen: set[str] = set()

    for row in all_values[1:]:
        if not row or not any(str(cell).strip() for cell in row):
            continue

        max_start = max(0, len(row) - width)
        for start in range(0, max_start + 1):
            window = list(row[start : start + width])
            if len(window) < width:
                window.extend([""] * (width - len(window)))
            if not is_canonical_reading_slice(window):
                continue

            dedupe_key = "|".join(window)
            if dedupe_key in seen:
                break
            seen.add(dedupe_key)
            recovered.append(window)
            break

    recovered.sort(key=lambda cells: cells[1], reverse=True)
    return recovered


def is_meaningful_reading_row(row: list[str], headers: list[str]) -> bool:
    """Return True when a row parses to equipment + parameter in canonical columns."""
    if not row or not any(str(cell).strip() for cell in row):
        return False
    parsed = parse_reading_row(row, headers)
    return bool(parsed.get("equipment", "").strip() and parsed.get("parameter_key", "").strip())


def build_reading_row(
    record: ReadingRowRecord,
    headers: list[str] | None = None,
) -> list[str]:
    """Build a worksheet row aligned to canonical or supplied headers."""
    target_headers = list(headers or GMD_SHEET_HEADERS)
    index_by_header = header_column_map(target_headers)
    field_values = record.as_field_dict()
    row = [""] * len(target_headers)

    for header_name, column_index in index_by_header.items():
        field_key = _HEADER_FIELD_ALIASES.get(header_name)
        if field_key is None:
            continue
        value = field_values.get(field_key, "")
        row[column_index] = value

    return row


# Backward-compatible alias used by older modules/tests
build_gmd_row = build_reading_row


def _cell(row: list[str], column_map: dict[str, int], header_name: str) -> str:
    index = column_map.get(header_name)
    if index is None or index >= len(row):
        return ""
    return str(row[index]).strip()


def _parse_by_header_map(row: list[str], headers: list[str]) -> dict[str, str]:
    column_map = header_column_map(headers)
    parsed = empty_reading_field_dict()

    for header_name, column_index in column_map.items():
        field_key = _HEADER_FIELD_ALIASES.get(header_name)
        if field_key is None:
            continue
        if column_index < len(row):
            parsed[field_key] = str(row[column_index]).strip()

    if parsed["status"]:
        parsed["status"] = parsed["status"].upper()
    else:
        parsed["status"] = "NORMAL"

    return parsed


def _parse_legacy_v1_row(row: list[str]) -> dict[str, str]:
    parsed = empty_reading_field_dict()
    parsed["timestamp"] = row[0].strip() if len(row) > 0 else ""
    parsed["category"] = row[1].strip() if len(row) > 1 else ""
    parsed["equipment"] = row[2].strip() if len(row) > 2 else ""
    parsed["parameter_key"] = row[3].strip() if len(row) > 3 else ""
    parsed["parameter_display_name"] = row[4].strip() if len(row) > 4 else ""
    parsed["value"] = row[5].strip() if len(row) > 5 else ""
    parsed["status"] = row[6].strip().upper() if len(row) > 6 else "NORMAL"
    parsed["verified_by"] = row[7].strip() if len(row) > 7 else ""
    parsed["remarks"] = row[8].strip() if len(row) > 8 else ""
    parsed["entry_source"] = row[9].strip() if len(row) > 9 else ""
    parsed["media_name"] = row[10].strip() if len(row) > 10 else ""
    parsed["media_type"] = row[11].strip() if len(row) > 11 else ""
    parsed["media_url"] = row[12].strip() if len(row) > 12 else ""
    return parsed


def _parse_legacy_gt_misaligned_row(row: list[str]) -> dict[str, str]:
    """
    Parse GMD legacy-v1 rows that were appended under GT motor headers by column position.

    GT columns id/plant/machine/motor/... received Timestamp/Category/Equipment/Parameter/...
    """
    parsed = empty_reading_field_dict()
    parsed["timestamp"] = row[0].strip() if len(row) > 0 else ""
    parsed["category"] = row[1].strip() if len(row) > 1 else ""
    parsed["equipment"] = row[2].strip() if len(row) > 2 else ""
    parsed["parameter_key"] = row[3].strip() if len(row) > 3 else ""
    parsed["parameter_display_name"] = row[4].strip() if len(row) > 4 else ""
    parsed["value"] = row[5].strip() if len(row) > 5 else ""
    parsed["status"] = row[6].strip().upper() if len(row) > 6 else "NORMAL"
    parsed["verified_by"] = row[7].strip() if len(row) > 7 else ""
    parsed["remarks"] = row[8].strip() if len(row) > 8 else ""
    parsed["entry_source"] = row[9].strip() if len(row) > 9 else "Web"
    if not parsed["status"]:
        parsed["status"] = "NORMAL"
    return parsed


def legacy_row_to_canonical_row(
    row: list[str],
    headers: list[str],
    *,
    submission_id: str = "",
) -> list[str]:
    """Convert a legacy worksheet row into the canonical 17-column layout."""
    schema = detect_sheet_schema(headers)
    if schema == SheetSchema.CANONICAL:
        return build_reading_row(
            ReadingRowRecord(**parse_reading_row(row, headers)),
            GMD_SHEET_HEADERS,
        )

    parsed = parse_reading_row(row, headers)
    if submission_id:
        parsed["submission_id"] = submission_id
    record = ReadingRowRecord(**parsed)
    return build_reading_row(record, GMD_SHEET_HEADERS)


def parse_reading_row(row: list[str], headers: list[str]) -> dict[str, str]:
    """Parse a worksheet data row into canonical snake_case field keys."""
    schema = detect_sheet_schema(headers)

    if schema == SheetSchema.LEGACY_V1:
        return _parse_legacy_v1_row(row)

    if schema == SheetSchema.LEGACY_GT:
        return _parse_legacy_gt_misaligned_row(row)

    return _parse_by_header_map(row, headers)


# Backward-compatible alias
parse_gmd_sheet_row = parse_reading_row


def to_dashboard_api_row(parsed: Mapping[str, str]) -> dict[str, Any]:
    """
    Map canonical reading fields to dashboard/reports API shape.

    Preserves legacy response keys (`parameter`, `location`) for frontend compatibility.
    """
    status = str(parsed.get("status") or "NORMAL").strip().upper() or "NORMAL"
    return {
        "submission_id": parsed.get("submission_id", ""),
        "timestamp": parsed.get("timestamp", ""),
        "area_tank": parsed.get("area_tank", ""),
        "category": parsed.get("category", ""),
        "equipment": parsed.get("equipment", ""),
        "tag_no": parsed.get("tag_no", ""),
        "parameter": parsed.get("parameter_key", ""),
        "parameter_key": parsed.get("parameter_key", ""),
        "parameter_display_name": parsed.get("parameter_display_name", ""),
        "location": parsed.get("parameter_display_name", ""),
        "unit": parsed.get("unit", ""),
        "value": parsed.get("value", ""),
        "status": status,
        "verified_by": parsed.get("verified_by", ""),
        "remarks": parsed.get("remarks", ""),
        "entry_source": parsed.get("entry_source", ""),
        "media_name": parsed.get("media_name", ""),
        "media_type": parsed.get("media_type", ""),
        "media_url": parsed.get("media_url", ""),
    }
