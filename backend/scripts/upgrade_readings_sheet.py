"""
Upgrade the Readings worksheet to the canonical 17-column GMD schema.

Fixes sheets that still show legacy GT headers (id/plant/machine/motor) or older
GMD Title Case headers. Optionally rewrites existing data rows into canonical columns.

Usage:
  cd backend
  python scripts/upgrade_readings_sheet.py --dry-run
  python scripts/upgrade_readings_sheet.py
  python scripts/upgrade_readings_sheet.py --header-only

Requires GOOGLE_SHEETS_ENABLED=true and Google credentials (see .env.example).
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND.parent / ".env")
load_dotenv(BACKEND / ".env")

import gspread

from services.sheets_config import (
    ensure_gmd_header_row,
    get_spreadsheet_id,
    get_worksheet_name,
    is_sheets_enabled,
    load_service_account_credentials,
    open_spreadsheet,
)
from services.sheets_row_model import (
    GMD_SHEET_HEADERS,
    SheetSchema,
    detect_sheet_schema,
    legacy_row_to_canonical_row,
)


def _column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _row_is_blank(row: list[str]) -> bool:
    return not any(str(cell).strip() for cell in row)


def upgrade_readings_sheet(*, dry_run: bool, header_only: bool) -> int:
    if not is_sheets_enabled():
        print("ERROR: GOOGLE_SHEETS_ENABLED is not true")
        return 1

    sheet_id = get_spreadsheet_id()
    if not sheet_id:
        print("ERROR: GOOGLE_SHEET_ID is not set")
        return 1

    creds, creds_source = load_service_account_credentials()
    client = gspread.authorize(creds)
    spreadsheet = open_spreadsheet(client, sheet_id)
    worksheet_name = get_worksheet_name()
    worksheet = spreadsheet.worksheet(worksheet_name)

    all_values = worksheet.get_all_values()
    if not all_values:
        print(f"Worksheet {worksheet_name!r} is empty — writing canonical headers only")
        if not dry_run:
            end_col = _column_letter(len(GMD_SHEET_HEADERS))
            worksheet.update(
                [GMD_SHEET_HEADERS],
                range_name=f"A1:{end_col}1",
                value_input_option="RAW",
            )
        return 0

    headers = [str(cell).strip() for cell in all_values[0]]
    schema = detect_sheet_schema(headers)
    data_rows = all_values[1:]

    print(f"Spreadsheet: {spreadsheet.title}")
    print(f"Worksheet:   {worksheet_name!r}")
    print(f"Credentials: {creds_source}")
    print(f"Schema:      {schema.value}")
    print(f"Data rows:   {len(data_rows)}")
    print(f"Mode:        {'header-only' if header_only else 'header + migrate rows'}")
    print(f"Dry run:     {dry_run}")

    if schema == SheetSchema.CANONICAL and not header_only:
        non_blank = [row for row in data_rows if not _row_is_blank(row)]
        if non_blank and len(non_blank[0]) <= len(GMD_SHEET_HEADERS):
            first = non_blank[0]
            if first and first[0] and " " in str(first[0]) and len(first) >= 4:
                print(
                    "NOTE: Headers are canonical but some rows may still use legacy "
                    "column positions — run without --header-only to migrate data."
                )
            else:
                print("Headers already canonical; data rows look aligned — nothing to do.")
                return 0

    if header_only:
        if schema == SheetSchema.CANONICAL:
            print("Headers already canonical.")
            return 0
        if dry_run:
            print("Would upgrade row 1 to:")
            print(", ".join(GMD_SHEET_HEADERS))
            return 0
        ensure_gmd_header_row(worksheet)
        print("Header row upgraded to canonical layout.")
        return 0

    migrated: list[list[str]] = []
    skipped = 0
    for row in data_rows:
        if _row_is_blank(row):
            skipped += 1
            continue
        submission_id = str(uuid.uuid4())
        migrated.append(
            legacy_row_to_canonical_row(row, headers, submission_id=submission_id)
        )

    print(f"Rows to migrate: {len(migrated)} (skipped blank: {skipped})")
    if migrated:
        sample = migrated[0]
        print("Sample migrated row:")
        for header, value in zip(GMD_SHEET_HEADERS, sample):
            if value:
                print(f"  {header}: {value}")

    if dry_run:
        print("Dry run complete — no changes written.")
        return 0

    end_col = _column_letter(len(GMD_SHEET_HEADERS))
    total_rows = 1 + len(migrated)
    worksheet.resize(rows=max(total_rows + 50, 1000), cols=len(GMD_SHEET_HEADERS))
    worksheet.clear()
    worksheet.update(
        [GMD_SHEET_HEADERS] + migrated,
        range_name=f"A1:{end_col}{total_rows}",
        value_input_option="RAW",
    )
    print(f"Wrote canonical header + {len(migrated)} migrated rows.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing to Google Sheets",
    )
    parser.add_argument(
        "--header-only",
        action="store_true",
        help="Upgrade row 1 only; leave existing data rows unchanged",
    )
    args = parser.parse_args()
    raise SystemExit(upgrade_readings_sheet(dry_run=args.dry_run, header_only=args.header_only))


if __name__ == "__main__":
    main()
