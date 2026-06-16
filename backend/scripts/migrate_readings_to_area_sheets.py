"""
Migrate rows from the legacy Readings worksheet into per-area worksheets.

Usage:
  cd backend
  python scripts/migrate_readings_to_area_sheets.py --dry-run
  python scripts/migrate_readings_to_area_sheets.py

Requires GOOGLE_SHEETS_ENABLED=true and spreadsheet credentials.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND.parent / ".env")
load_dotenv(BACKEND / ".env")

import gspread

from services.sheets_area_registry import resolve_area_worksheet
from services.sheets_config import (
    ensure_gmd_header_row,
    get_or_create_worksheet,
    get_spreadsheet_id,
    get_worksheet_name,
    is_sheets_enabled,
    load_service_account_credentials,
    open_spreadsheet,
)
from services.sheets_row_model import (
    GMD_SHEET_HEADERS,
    ReadingRowRecord,
    build_reading_row,
    is_meaningful_reading_row,
    parse_reading_row,
)


def migrate(*, dry_run: bool = False, source: str | None = None) -> dict:
    if not is_sheets_enabled():
        raise RuntimeError("GOOGLE_SHEETS_ENABLED must be true")

    spreadsheet_id = get_spreadsheet_id()
    source_name = source or get_worksheet_name()

    creds, _ = load_service_account_credentials()
    client = gspread.authorize(creds)
    spreadsheet = open_spreadsheet(client, spreadsheet_id)
    source_ws = spreadsheet.worksheet(source_name)
    source_values = source_ws.get_all_values()

    if len(source_values) <= 1:
        return {"source_rows": 0, "migrated_rows": 0, "by_worksheet": {}}

    headers = source_values[0]
    grouped: dict[str, list[list[str]]] = defaultdict(list)
    seen: set[str] = set()

    for row in source_values[1:]:
        if not is_meaningful_reading_row(row, headers):
            continue
        parsed = parse_reading_row(row, headers)
        record = ReadingRowRecord(**parsed)
        canonical = build_reading_row(record, GMD_SHEET_HEADERS)
        dedupe_key = "|".join(canonical)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        worksheet_name = resolve_area_worksheet(
            area_tank=record.area_tank,
            category=record.category,
            equipment=record.equipment,
        )
        grouped[worksheet_name].append(canonical)

    migrated = 0
    if not dry_run:
        for worksheet_name, rows in grouped.items():
            target = get_or_create_worksheet(spreadsheet, worksheet_name)
            ensure_gmd_header_row(target)
            if rows:
                target.insert_rows(rows, row=2, value_input_option="USER_ENTERED")
                migrated += len(rows)

    return {
        "source_worksheet": source_name,
        "source_rows": len(source_values) - 1,
        "migrated_rows": sum(len(rows) for rows in grouped.values()) if dry_run else migrated,
        "dry_run": dry_run,
        "by_worksheet": {name: len(rows) for name, rows in grouped.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Readings tab to area worksheets")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", default=None, help="Source worksheet (default: Readings)")
    args = parser.parse_args()

    summary = migrate(dry_run=args.dry_run, source=args.source)
    print(summary)


if __name__ == "__main__":
    main()
