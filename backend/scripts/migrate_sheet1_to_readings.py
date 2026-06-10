"""
One-time migration utility: copy valid GMD rows from Sheet1 to Readings.

Reads the source tab (default: Sheet1), validates each row against the GMD
10-column schema, and appends non-duplicate rows to the official Readings tab.
Timestamps and all column values are preserved as-is.

Usage:
  cd backend
  python scripts/migrate_sheet1_to_readings.py
  python scripts/migrate_sheet1_to_readings.py --dry-run
  python scripts/migrate_sheet1_to_readings.py --source Sheet1

Requires environment (see backend/.env.example):
  GOOGLE_SHEETS_ENABLED=true
  GOOGLE_SHEET_ID=...
  GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND.parent / ".env")
load_dotenv(BACKEND / ".env")

import gspread
from gspread.exceptions import WorksheetNotFound

from gmd_config import get_equipment_for_category, get_valid_categories
from services.sheets_config import (
    GMD_SHEET_HEADERS,
    ensure_gmd_header_row,
    get_spreadsheet_id,
    get_worksheet_name,
    is_sheets_enabled,
    load_service_account_credentials,
    open_spreadsheet,
)

SOURCE_WORKSHEET_DEFAULT = "Sheet1"
ALLOWED_STATUSES = {"NORMAL", "WARNING", "ALARM"}
COLUMN_COUNT = len(GMD_SHEET_HEADERS)


@dataclass
class MigrationSummary:
    source_worksheet: str = ""
    target_worksheet: str = ""
    source_rows_scanned: int = 0
    rows_copied: int = 0
    duplicates_skipped: int = 0
    errors_found: int = 0
    blank_rows_skipped: int = 0
    header_rows_skipped: int = 0
    dry_run: bool = False
    error_details: List[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_worksheet": self.source_worksheet,
            "target_worksheet": self.target_worksheet,
            "dry_run": self.dry_run,
            "source_rows_scanned": self.source_rows_scanned,
            "rows_copied": self.rows_copied,
            "duplicates_skipped": self.duplicates_skipped,
            "errors_found": self.errors_found,
            "blank_rows_skipped": self.blank_rows_skipped,
            "header_rows_skipped": self.header_rows_skipped,
            "error_details": self.error_details,
        }


def normalize_row_cells(row: List[Any]) -> List[str]:
    """Pad or trim a raw sheet row to exactly 10 GMD columns."""
    cells = [str(cell).strip() if cell is not None else "" for cell in row]
    if len(cells) < COLUMN_COUNT:
        cells.extend([""] * (COLUMN_COUNT - len(cells)))
    return cells[:COLUMN_COUNT]


def is_blank_row(row: List[str]) -> bool:
    return not any(cell for cell in row)


def is_gmd_header_row(row: List[str]) -> bool:
    return normalize_row_cells(row) == GMD_SHEET_HEADERS


def row_fingerprint(row: List[str]) -> Tuple[str, ...]:
    """Stable identity for duplicate detection across worksheets."""
    return tuple(normalize_row_cells(row))


def validate_numeric_value(value: str, field_name: str) -> Optional[str]:
    if not value:
        return f"{field_name} is required and cannot be empty."
    try:
        numeric = float(value)
    except ValueError:
        return f"{field_name} must be numeric; received '{value}'."
    if numeric < 0:
        return f"{field_name} cannot be negative; received {numeric}."
    return None


def validate_gmd_row(row: List[str]) -> Optional[str]:
    """
    Validate a normalized 10-column GMD row.
    Returns an error message when invalid, otherwise None.
    """
    normalized = normalize_row_cells(row)

    timestamp = normalized[0]
    category = normalized[1]
    equipment = normalized[2]
    parameter = normalized[3]
    value = normalized[5]
    status = normalized[6].upper() if normalized[6] else ""

    if not timestamp:
        return "Timestamp is required."

    if not category:
        return "Category is required."

    if not equipment:
        return "Equipment is required."

    if not parameter:
        return "Parameter is required."

    value_error = validate_numeric_value(value, "Value")
    if value_error:
        return value_error

    if status and status not in ALLOWED_STATUSES:
        return (
            f"Status must be one of {sorted(ALLOWED_STATUSES)}; received '{normalized[6]}'."
        )

    valid_categories = get_valid_categories()
    if category not in valid_categories:
        allowed = ", ".join(sorted(valid_categories))
        return f"Invalid category '{category}'. Allowed: {allowed}."

    allowed_equipment = get_equipment_for_category(category)
    if equipment not in allowed_equipment:
        return (
            f"Invalid equipment '{equipment}' for category '{category}'."
        )

    return None


def connect_spreadsheet() -> Any:
    if not is_sheets_enabled():
        raise RuntimeError(
            "Google Sheets is disabled. Set GOOGLE_SHEETS_ENABLED=true."
        )

    spreadsheet_id = get_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID is not configured.")

    creds, source = load_service_account_credentials()
    client = gspread.authorize(creds)
    spreadsheet = open_spreadsheet(client, spreadsheet_id)
    return spreadsheet


def load_worksheet(spreadsheet: Any, title: str) -> Any:
    try:
        return spreadsheet.worksheet(title)
    except WorksheetNotFound as exc:
        raise RuntimeError(f"Worksheet '{title}' was not found in the spreadsheet.") from exc


def collect_existing_fingerprints(rows: List[List[Any]]) -> Set[Tuple[str, ...]]:
    fingerprints: Set[Tuple[str, ...]] = set()
    for row in rows:
        if is_blank_row(normalize_row_cells(row)):
            continue
        if is_gmd_header_row(row):
            continue
        fingerprints.add(row_fingerprint(row))
    return fingerprints


def migrate(
    *,
    source_title: str,
    target_title: str,
    dry_run: bool,
) -> MigrationSummary:
    summary = MigrationSummary(
        source_worksheet=source_title,
        target_worksheet=target_title,
        dry_run=dry_run,
    )

    spreadsheet = connect_spreadsheet()
    source_ws = load_worksheet(spreadsheet, source_title)
    target_ws = load_worksheet(spreadsheet, target_title)

    if not dry_run:
        ensure_gmd_header_row(target_ws)

    source_values = source_ws.get_all_values()
    target_values = target_ws.get_all_values()

    existing = collect_existing_fingerprints(target_values[1:] if len(target_values) > 1 else [])
    pending: List[List[str]] = []
    seen_source: Set[Tuple[str, ...]] = set()

    for index, raw_row in enumerate(source_values[1:], start=2):
        summary.source_rows_scanned += 1
        normalized = normalize_row_cells(raw_row)

        if is_blank_row(normalized):
            summary.blank_rows_skipped += 1
            continue

        if is_gmd_header_row(normalized):
            summary.header_rows_skipped += 1
            continue

        error = validate_gmd_row(normalized)
        if error:
            summary.errors_found += 1
            summary.error_details.append(
                {
                    "worksheet": source_title,
                    "row": index,
                    "error": error,
                    "preview": {
                        "timestamp": normalized[0],
                        "category": normalized[1],
                        "equipment": normalized[2],
                        "parameter": normalized[3],
                        "value": normalized[5],
                        "status": normalized[6],
                    },
                }
            )
            continue

        fingerprint = row_fingerprint(normalized)

        if fingerprint in existing:
            summary.duplicates_skipped += 1
            continue

        if fingerprint in seen_source:
            summary.duplicates_skipped += 1
            continue

        seen_source.add(fingerprint)
        pending.append(normalized)

    if pending and not dry_run:
        target_ws.append_rows(pending, value_input_option="USER_ENTERED")

    summary.rows_copied = len(pending)
    return summary


def print_summary(summary: MigrationSummary) -> None:
    print("\n" + "=" * 60)
    print("GMD Sheet Migration Summary")
    print("=" * 60)
    print(f"Source worksheet:      {summary.source_worksheet}")
    print(f"Target worksheet:      {summary.target_worksheet}")
    print(f"Dry run:               {summary.dry_run}")
    print(f"Source rows scanned:   {summary.source_rows_scanned}")
    print(f"Rows copied:           {summary.rows_copied}")
    print(f"Duplicates skipped:    {summary.duplicates_skipped}")
    print(f"Errors found:          {summary.errors_found}")
    print(f"Blank rows skipped:    {summary.blank_rows_skipped}")
    print(f"Header rows skipped:   {summary.header_rows_skipped}")
    print("=" * 60)

    if summary.error_details:
        print("\nError details (first 20):")
        for item in summary.error_details[:20]:
            preview = item.get("preview", {})
            print(
                f"  Row {item['row']}: {item['error']} "
                f"[{preview.get('equipment', '?')}/{preview.get('parameter', '?')}]"
            )
        if len(summary.error_details) > 20:
            print(f"  ... and {len(summary.error_details) - 20} more")

    print("\nJSON summary:")
    print(json.dumps(summary.to_dict(), indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy valid GMD rows from Sheet1 into the Readings worksheet."
    )
    parser.add_argument(
        "--source",
        default=SOURCE_WORKSHEET_DEFAULT,
        help=f"Source worksheet name (default: {SOURCE_WORKSHEET_DEFAULT})",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Target worksheet name (default: GOOGLE_SHEET_WORKSHEET or Readings)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report without writing to Readings",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_title = args.target or get_worksheet_name("Readings")

    if args.source.strip().lower() == target_title.strip().lower():
        print("ERROR: Source and target worksheets must be different.")
        return 1

    try:
        summary = migrate(
            source_title=args.source.strip(),
            target_title=target_title.strip(),
            dry_run=args.dry_run,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1
    except Exception as exc:
        print(f"ERROR: Migration failed: {exc}")
        raise

    print_summary(summary)

    if summary.errors_found > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
