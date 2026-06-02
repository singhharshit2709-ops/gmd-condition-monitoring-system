"""
Repair the Readings Google Sheet layout:
- single canonical header on row 1
- duplicate header rows removed from data
- valid readings normalized to 22 columns, newest-first below header

Usage:
  cd backend
  set GOOGLE_SHEETS_ENABLED=true
  set GOOGLE_SHEET_ID=...
  set GOOGLE_SERVICE_ACCOUNT_JSON=...
  python scripts/cleanup_sheets_layout.py

Optional:
  set GOOGLE_SHEETS_REPAIR_LAYOUT=true   # force full rebuild even if sheet looks OK
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND.parent / ".env")
load_dotenv(BACKEND / ".env")

import server  # noqa: E402


def main() -> int:
    force = os.environ.get("GOOGLE_SHEETS_REPAIR_LAYOUT", "").lower() == "true"
    print("Initializing Google Sheets...")
    server.init_google_sheets()

    if not server._sheets_enabled or server._sheets_worksheet is None:
        print("ERROR: Google Sheets is not enabled or worksheet unavailable.")
        print("Set GOOGLE_SHEETS_ENABLED=true, GOOGLE_SHEET_ID, and service account credentials.")
        return 1

    ws = server._sheets_worksheet
    row1 = ws.row_values(1)
    print(f"Row 1 columns: {len(row1)}")
    print(f"Canonical header match: {server._normalize_sheet_row(row1) == server._SHEETS_HEADERS}")

    all_values = ws.get_all_values()
    dupes = sum(1 for row in all_values[1:] if server._header_row_matches(row))
    print(f"Duplicate header rows in data area: {dupes}")

    needs = server._sheet_needs_repair(ws)
    print(f"Sheet needs repair: {needs}")

    if not needs and not force:
        print("Sheet layout OK — no repair required.")
        return 0

    print("Running full layout repair...")
    stats = server.repair_readings_worksheet_layout(ws)
    print(json.dumps(stats, indent=2))

    row1_after = ws.row_values(1)
    all_after = ws.get_all_values()
    dupes_after = sum(1 for row in all_after[1:] if server._header_row_matches(row))
    print(f"After repair: row1 cols={len(row1_after)}, dup headers={dupes_after}, total rows={len(all_after)}")
    print(f"Header exact match: {server._normalize_sheet_row(row1_after) == server._SHEETS_HEADERS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
