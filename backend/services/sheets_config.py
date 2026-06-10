"""
Shared Google Sheets configuration for GMD Dashboard and legacy GT compatibility.

Canonical environment variables (use these everywhere):
  GOOGLE_SHEETS_ENABLED          - "true" to enable Sheets integration
  GOOGLE_SHEET_ID                - Spreadsheet ID
  GOOGLE_SHEET_WORKSHEET         - Worksheet tab name (default: Readings)
  GOOGLE_SERVICE_ACCOUNT_JSON    - Service account JSON string (preferred on Render)
  GOOGLE_SERVICE_ACCOUNT_FILE    - Path to service account JSON file (local dev)

Legacy aliases (read-only fallbacks — do not use in new deployments):
  GOOGLE_SPREADSHEET_ID          - alias for GOOGLE_SHEET_ID
  GOOGLE_WORKSHEET               - alias for GOOGLE_SHEET_WORKSHEET
  GOOGLE_CREDENTIALS_FILE        - alias for GOOGLE_SERVICE_ACCOUNT_FILE
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Tuple

from gspread.exceptions import WorksheetNotFound

logger = logging.getLogger("gmd_condition_monitoring.sheets_config")

_BACKEND_DIR = Path(__file__).resolve().parent.parent

GMD_SHEET_HEADERS = [
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

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def is_sheets_enabled() -> bool:
    return os.environ.get("GOOGLE_SHEETS_ENABLED", "false").strip().lower() == "true"


def get_spreadsheet_id() -> str:
    """Return spreadsheet ID from canonical or legacy env var."""
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        sheet_id = os.environ.get("GOOGLE_SPREADSHEET_ID", "").strip()
    return sheet_id


def get_worksheet_name(default: str = "Readings") -> str:
    """Return worksheet tab name from canonical or legacy env var."""
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
    """
    Load Google service account credentials.
    Returns (credentials, source_description).
    Raises RuntimeError when credentials cannot be resolved.
    """
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
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            return creds, "GOOGLE_SERVICE_ACCOUNT_JSON"
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON."
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
    """Open worksheet by name, creating it if missing."""
    title = worksheet_name or get_worksheet_name()
    column_count = cols or len(GMD_SHEET_HEADERS)
    try:
        return spreadsheet.worksheet(title)
    except WorksheetNotFound:
        logger.info("Worksheet %r not found — creating it", title)
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=column_count)


def ensure_gmd_header_row(worksheet: Any) -> None:
    """Ensure row 1 contains the GMD 10-column header."""
    row1 = worksheet.row_values(1)
    normalized = [str(cell).strip() for cell in row1[: len(GMD_SHEET_HEADERS)]]
    if normalized == GMD_SHEET_HEADERS:
        return

    end_col = chr(ord("A") + len(GMD_SHEET_HEADERS) - 1)
    worksheet.update(
        [GMD_SHEET_HEADERS],
        range_name=f"A1:{end_col}1",
        value_input_option="RAW",
    )
    logger.info("GMD worksheet header row written to A1:%s1", end_col)


def sheets_config_summary() -> dict[str, str]:
    """Non-secret snapshot of resolved Sheets configuration (for health/debug)."""
    creds_source = "not loaded"
    try:
        _, creds_source = load_service_account_credentials()
    except RuntimeError:
        creds_source = "missing"

    return {
        "enabled": str(is_sheets_enabled()),
        "spreadsheet_id_set": str(bool(get_spreadsheet_id())),
        "worksheet": get_worksheet_name(),
        "credentials_source": creds_source,
    }
