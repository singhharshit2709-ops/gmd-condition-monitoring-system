"""
Shared Google Sheets configuration for GMD Dashboard and legacy GT compatibility.

Row schema, building, and parsing live in services.sheets_row_model.
This module handles credentials, worksheet access, and header initialization.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Tuple

from gspread.exceptions import WorksheetNotFound

from services.sheets_row_model import (
    GMD_SHEET_HEADERS,
    GMD_SHEET_HEADERS_LEGACY,
    GMD_SHEET_HEADERS_LEGACY_V2,
    GMD_SHEET_MEDIA_HEADERS,
    ReadingRowRecord,
    build_gmd_row,
    build_reading_row,
    detect_sheet_schema,
    extract_reading_rows_from_worksheet,
    is_canonical_reading_slice,
    is_modern_gmd_header,
    parse_gmd_sheet_row,
    parse_reading_row,
    to_dashboard_api_row,
)
from services.sheets_api_diagnostics import run_sheets_api, worksheet_name
from services.sheets_row_model import SheetSchema  # noqa: F401 — re-export

logger = logging.getLogger("gmd_condition_monitoring.sheets_config")

_BACKEND_DIR = Path(__file__).resolve().parent.parent

# Re-export legacy names used across the codebase
GMD_SHEET_HEADERS_MEDIA_EXTENDED = GMD_SHEET_HEADERS_LEGACY + GMD_SHEET_MEDIA_HEADERS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

__all__ = [
    "GMD_SHEET_HEADERS",
    "GMD_SHEET_HEADERS_LEGACY",
    "GMD_SHEET_HEADERS_LEGACY_V2",
    "GMD_SHEET_HEADERS_MEDIA_EXTENDED",
    "GMD_SHEET_MEDIA_HEADERS",
    "ReadingRowRecord",
    "SheetSchema",
    "build_gmd_row",
    "build_reading_row",
    "detect_sheet_schema",
    "ensure_gmd_header_row",
    "header_column_map",
    "is_modern_gmd_header",
    "parse_gmd_sheet_row",
    "parse_reading_row",
    "to_dashboard_api_row",
]


def header_column_map(headers: list[str]) -> dict[str, int]:
    from services.sheets_row_model import header_column_map as _map

    return _map(headers)


def is_sheets_enabled() -> bool:
    return os.environ.get("GOOGLE_SHEETS_ENABLED", "false").strip().lower() == "true"


def get_spreadsheet_id() -> str:
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        sheet_id = os.environ.get("GOOGLE_SPREADSHEET_ID", "").strip()
    return sheet_id


def get_worksheet_name(default: str = "Readings") -> str:
    worksheet = os.environ.get("GOOGLE_SHEET_WORKSHEET", "").strip()
    if not worksheet:
        worksheet = os.environ.get("GOOGLE_WORKSHEET", "").strip()
    return worksheet or default


def get_cache_ttl_seconds(default: int = 45) -> int:
    raw = os.environ.get("GOOGLE_SHEETS_CACHE_TTL_SECONDS", str(default)).strip()
    try:
        return max(30, min(int(raw), 300))
    except ValueError:
        return default


def _resolve_credentials_file_path(raw_path: str) -> str:
    file_path = Path(raw_path)
    if file_path.is_absolute() and file_path.exists():
        return str(file_path)

    candidates = [
        file_path,
        _BACKEND_DIR / file_path,
        _BACKEND_DIR / file_path.name,
        Path.cwd() / file_path,
        Path.cwd() / file_path.name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return raw_path


def load_service_account_credentials() -> Tuple[Any, str]:
    try:
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise RuntimeError(
            "google-auth is not installed. Run: pip install google-auth gspread"
        ) from exc

    json_blob = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if json_blob:
        try:
            creds_dict = json.loads(json_blob)
            # Render (and other cloud providers) often escape literal newlines in
            # multi-line env vars, turning the real "\n" line breaks inside the
            # RSA private_key into the two-character sequence "\\n". Google's
            # auth library cannot parse a key in that form and raises
            # "Could not deserialize key data". Normalize it back here so the
            # key is always well-formed regardless of how the host stored it.
            creds_dict["private_key"] = creds_dict["private_key"].replace(
                "\\n", "\n"
            )
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            return creds, "GOOGLE_SERVICE_ACCOUNT_JSON"
        except json.JSONDecodeError as exc:
            logger.error(
                "GOOGLE_SERVICE_ACCOUNT_JSON could not be parsed as JSON: %s", exc
            )
            raise RuntimeError(
                "GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON."
            ) from exc
        except KeyError as exc:
            logger.error(
                "GOOGLE_SERVICE_ACCOUNT_JSON is missing expected key %s. "
                "Ensure the full service account JSON (including private_key, "
                "client_email, etc.) was pasted into the env var.",
                exc,
            )
            raise RuntimeError(
                f"GOOGLE_SERVICE_ACCOUNT_JSON is missing expected key {exc}."
            ) from exc

    file_env = (
        os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
        or os.environ.get("GOOGLE_CREDENTIALS_FILE", "").strip()
    )
    if not file_env:
        raise RuntimeError(
            "Google credentials not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON "
            "(Render) or GOOGLE_SERVICE_ACCOUNT_FILE / GOOGLE_CREDENTIALS_FILE (local)."
        )

    resolved = _resolve_credentials_file_path(file_env)
    if not os.path.exists(resolved):
        raise RuntimeError(
            f"Service account file not found: {file_env} (resolved: {resolved})"
        )

    creds = Credentials.from_service_account_file(resolved, scopes=SCOPES)
    return creds, f"service account file ({resolved})"


def open_spreadsheet(client: Any, spreadsheet_id: str | None = None) -> Any:
    sheet_id = spreadsheet_id or get_spreadsheet_id()
    if not sheet_id:
        raise RuntimeError(
            "Spreadsheet ID not configured. Set GOOGLE_SHEET_ID."
        )
    return client.open_by_key(sheet_id)


def get_or_create_worksheet(
    spreadsheet: Any,
    worksheet_name: str | None = None,
    *,
    rows: int = 10000,
    cols: int | None = None,
) -> Any:
    title = worksheet_name or get_worksheet_name()
    column_count = cols or len(GMD_SHEET_HEADERS)
    sheet_id = get_spreadsheet_id()
    try:
        return run_sheets_api(
            title,
            "spreadsheet.worksheet",
            lambda: spreadsheet.worksheet(title),
            spreadsheet_id=sheet_id,
        )
    except WorksheetNotFound:
        logger.info(
            "Worksheet %r not found — creating it (spreadsheet_id=%r)",
            title,
            sheet_id,
        )
        return run_sheets_api(
            title,
            "spreadsheet.add_worksheet",
            lambda: spreadsheet.add_worksheet(
                title=title, rows=rows, cols=column_count
            ),
            spreadsheet_id=sheet_id,
            rows=rows,
            cols=column_count,
        )


def _column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def ensure_gmd_header_row(worksheet: Any) -> None:
    """Ensure row 1 uses the canonical snake_case GMD header layout."""
    ws_name = worksheet_name(worksheet)
    sheet_id = get_spreadsheet_id()
    row1 = run_sheets_api(
        ws_name,
        "worksheet.row_values",
        lambda: worksheet.row_values(1),
        spreadsheet_id=sheet_id,
        row=1,
    )
    normalized = [str(cell).strip() for cell in row1]
    target_len = len(GMD_SHEET_HEADERS)

    prefix = normalized[:target_len]
    while len(prefix) < target_len:
        prefix.append("")

    if prefix != GMD_SHEET_HEADERS:
        schema = detect_sheet_schema(normalized)
        end_col = _column_letter(target_len)
        range_name = f"A1:{end_col}1"
        run_sheets_api(
            ws_name,
            "worksheet.update",
            lambda: worksheet.update(
                [GMD_SHEET_HEADERS],
                range_name=range_name,
                value_input_option="RAW",
            ),
            spreadsheet_id=sheet_id,
            range_name=range_name,
        )
        logger.info(
            "GMD worksheet %r header row upgraded from %s to canonical layout A1:%s1 (%d columns)",
            ws_name,
            schema.value,
            end_col,
            target_len,
        )


def worksheet_has_horizontal_drift(all_values: list[list[str]]) -> bool:
    """Detect rows written outside column A due to widened worksheet tables."""
    if len(all_values) <= 1:
        return False

    width = len(GMD_SHEET_HEADERS)
    for row in all_values[1:]:
        if not row or not any(str(cell).strip() for cell in row):
            continue

        if is_canonical_reading_slice(row):
            continue

        max_start = max(0, len(row) - width)
        for start in range(1, max_start + 1):
            window = list(row[start : start + width])
            if len(window) < width:
                window.extend([""] * (width - len(window)))
            if is_canonical_reading_slice(window):
                return True
    return False


def normalize_readings_worksheet(worksheet: Any) -> dict[str, int]:
    """
    Rebuild the Readings worksheet with canonical A:Q layout.

    Recovers horizontally drifted rows and trims excess worksheet columns so
    future inserts always start at column A.
    """
    ws_name = worksheet_name(worksheet)
    sheet_id = get_spreadsheet_id()
    all_values = run_sheets_api(
        ws_name,
        "worksheet.get_all_values",
        lambda: worksheet.get_all_values(),
        spreadsheet_id=sheet_id,
    )
    canonical_rows = extract_reading_rows_from_worksheet(all_values)
    target_len = len(GMD_SHEET_HEADERS)
    end_col = _column_letter(target_len)
    all_rows = [list(GMD_SHEET_HEADERS)] + canonical_rows
    total_rows = len(all_rows)

    run_sheets_api(
        ws_name,
        "worksheet.resize",
        lambda: worksheet.resize(
            rows=max(total_rows + 100, 1000),
            cols=target_len,
        ),
        spreadsheet_id=sheet_id,
        rows=max(total_rows + 100, 1000),
        cols=target_len,
    )
    update_range = f"A1:{end_col}{total_rows}"
    run_sheets_api(
        ws_name,
        "worksheet.update",
        lambda: worksheet.update(
            all_rows,
            range_name=update_range,
            value_input_option="RAW",
        ),
        spreadsheet_id=sheet_id,
        range_name=update_range,
        row_count=total_rows,
    )

    current_rows = worksheet.row_count
    if current_rows > total_rows:
        run_sheets_api(
            ws_name,
            "worksheet.delete_rows",
            lambda: worksheet.delete_rows(total_rows + 1, current_rows),
            spreadsheet_id=sheet_id,
            start_row=total_rows + 1,
            end_row=current_rows,
        )

    logger.info(
        "GMD worksheet %r normalized: recovered_rows=%d total_rows=%d columns=%d",
        ws_name,
        len(canonical_rows),
        total_rows,
        target_len,
    )
    return {
        "recovered_rows": len(canonical_rows),
        "total_rows": total_rows,
        "columns": target_len,
    }


def sheets_config_summary() -> dict[str, str]:
    creds_source = "not loaded"
    try:
        _, creds_source = load_service_account_credentials()
    except RuntimeError:
        creds_source = "missing"

    from services.sheets_area_registry import (
        get_area_worksheet_names,
        is_multi_area_layout_enabled,
    )

    return {
        "enabled": str(is_sheets_enabled()),
        "spreadsheet_id_set": str(bool(get_spreadsheet_id())),
        "worksheet": get_worksheet_name(),
        "multi_area_layout": str(is_multi_area_layout_enabled()),
        "area_worksheets": ", ".join(get_area_worksheet_names()),
        "credentials_source": creds_source,
    }
