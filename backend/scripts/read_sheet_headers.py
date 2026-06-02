"""Fetch row 1 from the configured Google Sheet and compare to _SHEETS_HEADERS."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Import after path setup — loads server module constants only
import server  # noqa: E402

EXPECTED = list(server._SHEETS_HEADERS)


def main() -> int:
    print("Backend _SHEETS_HEADERS ({} columns):".format(len(EXPECTED)))
    for i, col in enumerate(EXPECTED, start=1):
        print(f"  {i:2}. {col}")

    enabled = os.environ.get("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not enabled or not sheet_id:
        print("\nGoogle Sheets not configured in environment (cannot fetch live row 1).")
        return 0

    try:
        server.init_google_sheets()
    except Exception as exc:
        print(f"\ninit_google_sheets failed: {exc}")
        return 1

    if not server._sheets_enabled or server._sheets_worksheet is None:
        print("\nGoogle Sheets init did not enable worksheet.")
        return 1

    actual = server._sheets_worksheet.row_values(1)
    print("\nLive Google Sheets row 1 ({} columns):".format(len(actual)))
    for i, col in enumerate(actual, start=1):
        print(f"  {i:2}. {col}")

    missing = [c for c in EXPECTED if c not in actual]
    extra = [c for c in actual if c not in EXPECTED]
    print("\nMissing from sheet:", missing or "(none)")
    print("Extra on sheet:", extra or "(none)")
    print("Exact match:", actual == EXPECTED)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
