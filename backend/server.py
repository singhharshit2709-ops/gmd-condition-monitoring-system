"""
server.py  –  Electrical Condition Monitoring  |  FastAPI Backend
=================================================================
Architecture
------------
* Thresholds are loaded EXCLUSIVELY from machine_config.json at startup.
* No thresholds are hardcoded anywhere in this file.
* Status classification: Normal → Warning → Alarm is driven purely by
  the config values, making the system fully data-driven.
* Designed to be drop-in ready for future PLC / OPC-UA streaming by
  replacing the /readings endpoint with a WebSocket or MQTT subscriber.

Dependencies
------------
    pip install fastapi uvicorn pydantic gspread google-auth python-dotenv

Run
---
    uvicorn server:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from routes.gmd_monitoring import router as gmd_router
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, model_validator

from config_resolve import (
    get_motor_thresholds_resolved,
    resolve_machine_id,
    resolve_motor_name,
)

# Load environment variables early
load_dotenv()

# ── Google Sheets (optional dependency) ──────────────────────────────────────
try:
    import gspread
    from google.oauth2.service_account import Credentials as GServiceCredentials
    _GSPREAD_AVAILABLE = True
except ImportError:
    _GSPREAD_AVAILABLE = False

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "machine_config.json"
STATIC_DIR = Path(__file__).parent / "static"

STATUS_NORMAL  = "Normal"
STATUS_WARNING = "Warning"
STATUS_ALARM   = "Alarm"

readings_cache: list[dict[str, Any]] = []
# Latest reading per (plant, machine, motor) — used for health + active alarms (Hybrid B).
_motor_latest: dict[tuple[str, str, str], dict[str, Any]] = {}
acknowledged_alarm_ids: set[str] = set()

_RECENT_HISTORY_TAIL = 1000

# ── Google Sheets runtime state ───────────────────────────────────────────────
_sheets_enabled: bool = False          # flipped to True only after successful init
_sheets_worksheet = None               # gspread.Worksheet | None

# Worksheet column order — must match _row_from_doc() below
_SHEETS_HEADERS = [
    "id", "plant", "machine", "motor",
    "current", "temperature", "vibration",
    "normal_current", "warning_current",
    "normal_temperature", "warning_temperature",
    "normal_vibration", "warning_vibration",
    "status", "timestamp",
    "entry_source", "verified_by", "notes",
    "photo_filename", "photo", "has_photo", "bulk_entry",
]
_SHEETS_MAX_CELL_CHARS = 49_000  # Google Sheets cell limit is 50,000 characters
_SHEETS_HEADER_ROW = 1
_SHEETS_DATA_START_ROW = 2  # Newest readings insert here (below header)


# ════════════════════════════════════════════════════════════════��[...]
# Config Loader
# ════════════════════════════════════════════════════════════════��[...]

def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load and return the raw machine_config.json as a dict."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        config = json.load(fh)
    logger.info("Loaded config v%s from %s", config.get("schema_version", "?"), path)
    return config


def get_motor_thresholds(
    config: dict[str, Any],
    plant_id: str,
    machine_id: str,
    motor_name: str,
) -> dict[str, float]:
    """Return threshold dict for a motor (canonical names resolved)."""
    _, _, thresholds = get_motor_thresholds_resolved(
        config, plant_id, machine_id, motor_name
    )
    return thresholds


def get_machine_parameters(
    config: dict[str, Any],
    plant_id: str,
    machine_id: str,
) -> list[str]:
    """Return the active parameter list for a machine."""
    canonical_machine = resolve_machine_id(config, plant_id, machine_id)
    try:
        return config["plants"][plant_id]["machines"][canonical_machine]["parameters"]
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Machine config not found: {exc}",
        ) from exc


# ════════════════════════════════════════════════════════════════�[...]
# Status Classification Helpers
# ════════════════════════════════════════════════════════════════�[...]

def classify_value(
    value: float,
    normal_limit: float,
    warning_limit: float,
) -> str:
    """
    Three-zone classification:
        value < normal_limit                 → Normal
        normal_limit ≤ value ≤ warning_limit → Warning
        value > warning_limit             → Alarm
    """
    if value < normal_limit:
        return STATUS_NORMAL
    if value <= warning_limit:
        return STATUS_WARNING
    return STATUS_ALARM


def classify_motor_reading(
    reading: MotorReading,
    thresholds: dict[str, float],
    active_params: list[str],
) -> MotorResult:
    """
    Apply threshold classification to every active parameter of a reading.
    The overall motor status is the most severe status across all parameters.
    """
    param_statuses: dict[str, ParameterStatus] = {}
    severity_rank = {STATUS_NORMAL: 0, STATUS_WARNING: 1, STATUS_ALARM: 2}
    worst_status = STATUS_NORMAL

    param_map = {
        "current":     ("current",     "normal_current",     "warning_current"),
        "temperature": ("temperature", "normal_temperature", "warning_temperature"),
        "vibration":   ("vibration",   "normal_vibration",   "warning_vibration"),
    }

    for param in active_params:
        if param not in param_map:
            continue

        reading_attr, normal_key, warning_key = param_map[param]
        value: float | None = getattr(reading, reading_attr, None)

        if value is None:
            # Parameter not supplied in this reading – skip silently
            continue

        if normal_key not in thresholds or warning_key not in thresholds:
            # Parameter not configured for this motor – skip
            continue

        status = classify_value(
            value=value,
            normal_limit=thresholds[normal_key],
            warning_limit=thresholds[warning_key],
        )
        param_statuses[param] = ParameterStatus(
            value=value,
            normal_limit=thresholds[normal_key],
            warning_limit=thresholds[warning_key],
            status=status,
        )
        if severity_rank[status] > severity_rank[worst_status]:
            worst_status = status

    return MotorResult(
        motor=reading.motor,
        overall_status=worst_status,
        parameters=param_statuses,
        timestamp=reading.timestamp or datetime.now(timezone.utc).isoformat(),
    )


def severity_order(result: MotorResult) -> int:
    """Sort key: Alarm first, then Warning, then Normal."""
    return {STATUS_ALARM: 0, STATUS_WARNING: 1, STATUS_NORMAL: 2}.get(
        result.overall_status, 3
    )


def status_rank(status: str) -> int:
    return {STATUS_NORMAL: 0, STATUS_WARNING: 1, STATUS_ALARM: 2}.get(status, 0)


def health_percent_for_status(status: str) -> int:
    if status == STATUS_ALARM:
        return 0
    if status == STATUS_WARNING:
        return 70
    return 100


# ════════════════════════════════════════════════════════════════�[...]
# Google Sheets Persistence Layer
# ════════════════════════════════════════════════════════════════�[...]

def _sheet_end_col() -> str:
    """Return the A1 column letter for the last _SHEETS_HEADERS column."""
    n = len(_SHEETS_HEADERS)
    letters = ""
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _normalize_sheet_row(row: list[Any]) -> list[str]:
    """Pad or trim a worksheet row to exactly len(_SHEETS_HEADERS) cells."""
    cells = ["" if cell is None else str(cell) for cell in row]
    if len(cells) < len(_SHEETS_HEADERS):
        cells.extend([""] * (len(_SHEETS_HEADERS) - len(cells)))
    return cells[: len(_SHEETS_HEADERS)]


def _header_row_matches(row: list[Any]) -> bool:
    """True when a row is a worksheet header (canonical or legacy partial)."""
    if not row:
        return False
    normalized = _normalize_sheet_row(row)
    if normalized == _SHEETS_HEADERS:
        return True
    first = [str(cell).strip().lower() for cell in row[:4]]
    return first == ["id", "plant", "machine", "motor"]


def _ensure_canonical_header_row(worksheet: Any) -> None:
    """
    Guarantee row 1 contains the canonical header.
    Updates in place — never inserts a header row into the data area.
    """
    row1 = worksheet.row_values(1)
    if _header_row_matches(row1) and _normalize_sheet_row(row1) == _SHEETS_HEADERS:
        return
    end_col = _sheet_end_col()
    worksheet.update(
        [_SHEETS_HEADERS],
        range_name=f"A1:{end_col}1",
        value_input_option="RAW",
    )
    logger.info("Google Sheets — canonical header written to row 1 (in-place update)")


def _remove_duplicate_header_rows(worksheet: Any) -> int:
    """Delete header rows found below row 1. Returns number of rows removed."""
    all_values = worksheet.get_all_values()
    rows_to_delete = [
        idx
        for idx, row in enumerate(all_values[1:], start=2)
        if _header_row_matches(row)
    ]
    for row_num in reversed(rows_to_delete):
        worksheet.delete_rows(row_num)
    return len(rows_to_delete)


def _sheet_needs_repair(worksheet: Any) -> bool:
    """Detect duplicate headers or a non-canonical row 1 header."""
    all_values = worksheet.get_all_values()
    if not all_values:
        return True
    if not _header_row_matches(all_values[0]):
        return True
    if _normalize_sheet_row(all_values[0]) != _SHEETS_HEADERS:
        return True
    return any(_header_row_matches(row) for row in all_values[1:])


def repair_readings_worksheet_layout(worksheet: Any) -> dict[str, int]:
    """
    Rebuild the Readings worksheet:
    row 1 = canonical header, rows 2+ = valid readings newest-first.
    Preserves all parseable readings and normalizes to 22 columns.
    """
    all_values = worksheet.get_all_values()
    docs: list[dict[str, Any]] = []
    duplicate_headers = 0
    skipped = 0

    for row in all_values:
        if _header_row_matches(row):
            duplicate_headers += 1
            continue
        doc = _doc_from_row(row)
        if doc:
            docs.append(doc)
        elif row and any(str(cell).strip() for cell in row):
            skipped += 1

    docs.sort(key=lambda doc: doc.get("timestamp") or "", reverse=True)
    data_rows = [_row_from_doc(doc) for doc in docs]
    all_rows = [_SHEETS_HEADERS] + data_rows
    end_col = _sheet_end_col()
    total_rows = len(all_rows)

    worksheet.resize(rows=max(total_rows + 50, 1000), cols=len(_SHEETS_HEADERS))
    worksheet.update(
        all_rows,
        range_name=f"A1:{end_col}{total_rows}",
        value_input_option="RAW",
    )

    current_rows = worksheet.row_count
    if current_rows > total_rows:
        worksheet.delete_rows(total_rows + 1, current_rows)

    return {
        "duplicate_headers_found": duplicate_headers,
        "valid_rows_written": len(docs),
        "skipped_rows": skipped,
        "total_rows": total_rows,
    }


def _row_from_doc(doc: dict[str, Any]) -> list:
    """Convert a reading document dict into an ordered list matching _SHEETS_HEADERS."""
    row: list[str] = []
    for col in _SHEETS_HEADERS:
        val = doc.get(col)
        if val is None or val == "" or val == "None":
            row.append("")
        elif col in _BOOL_SHEET_COLS:
            row.append("TRUE" if val else "FALSE")
        else:
            row.append(str(val))
    return row


def _merge_reading_source(
    motor_item: dict[str, Any] | None,
    batch_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge batch-level metadata (photo, verified_by) with per-motor reading fields."""
    merged: dict[str, Any] = {}
    if batch_meta:
        merged.update(batch_meta)
    if motor_item:
        merged.update(motor_item)
    return merged


def _photo_for_storage(source: dict[str, Any]) -> str | None:
    """Return photo payload for persistence; truncate if over Google Sheets cell limit."""
    raw = source.get("photo_base64") or source.get("photo")
    if not raw:
        return None
    text = str(raw)
    if len(text) > _SHEETS_MAX_CELL_CHARS:
        logger.warning(
            "Photo data truncated for Google Sheets (motor=%r, len=%d)",
            source.get("motor"),
            len(text),
        )
        return text[:_SHEETS_MAX_CELL_CHARS]
    return text


def _batch_meta_from_request(data: dict[str, Any]) -> dict[str, Any]:
    """Extract submission-level metadata applied to every motor in a bulk/single request."""
    return {
        key: value
        for key, value in {
            "verified_by": data.get("verified_by"),
            "technician": data.get("technician"),
            "photo_base64": data.get("photo_base64"),
            "photo_filename": data.get("photo_filename"),
            "entry_source": data.get("entry_source"),
            "notes": data.get("notes"),
        }.items()
        if value not in (None, "")
    }


_NUMERIC_SHEET_COLS = frozenset(
    {
        "current",
        "temperature",
        "vibration",
        "normal_current",
        "warning_current",
        "normal_temperature",
        "warning_temperature",
        "normal_vibration",
        "warning_vibration",
    }
)
_BOOL_SHEET_COLS = frozenset({"has_photo", "bulk_entry"})


def _parse_sheet_cell(column: str, raw: str) -> Any:
    """Convert a worksheet cell string back into a cache document field."""
    if raw is None:
        raw = ""
    text = str(raw).strip()
    if text == "":
        return None
    if column in _BOOL_SHEET_COLS:
        return text.lower() in ("true", "1", "yes")
    if column in _NUMERIC_SHEET_COLS:
        try:
            return float(text)
        except ValueError:
            return text
    return text


def _doc_from_row(row: list[str]) -> dict[str, Any] | None:
    """Convert a Readings worksheet row into a readings_cache document."""
    if not row or all(str(cell).strip() == "" for cell in row):
        return None
    if _header_row_matches(row):
        return None
    padded = _normalize_sheet_row(row)
    doc: dict[str, Any] = {
        col: _parse_sheet_cell(col, padded[idx])
        for idx, col in enumerate(_SHEETS_HEADERS)
    }
    plant = str(doc.get("plant") or "").strip()
    motor = str(doc.get("motor") or "").strip()
    if not plant or not motor:
        return None
    if plant.lower() == "plant" and motor.lower() == "motor":
        return None
    return doc


def _motor_key(doc: dict[str, Any]) -> tuple[str, str, str]:
    return (str(doc["plant"]), str(doc["machine"]), str(doc["motor"]))


def _set_motor_latest(doc: dict[str, Any]) -> None:
    """Record the newest known reading for a motor (live submit or sheet row)."""
    _motor_latest[_motor_key(doc)] = doc


def hydrate_readings_cache_from_sheets(recent_tail: int = _RECENT_HISTORY_TAIL) -> None:
    """
    Hybrid B+A hydration from Google Sheets on startup.

    Sheet layout is newest-first: row 2 is the latest submission.

    B — Build _motor_latest from the full Readings tab (first row per motor wins).
    A — Load readings_cache with the first ``recent_tail`` rows (newest) for /recent.
    """
    global readings_cache, _motor_latest

    if not _sheets_enabled or _sheets_worksheet is None:
        logger.info("Cache hydration skipped — Google Sheets not enabled")
        return

    try:
        logger.info(
            "Cache hydration starting (hybrid B+A, recent_tail=%d)...",
            recent_tail,
        )
        all_values = _sheets_worksheet.get_all_values()
        if len(all_values) <= 1:
            readings_cache = []
            _motor_latest = {}
            logger.info(
                "Cache hydration succeeded — 0 sheet row(s); recent=0, motor_latest=0"
            )
            return

        all_docs: list[dict[str, Any]] = []
        skipped = 0
        for row in all_values[1:]:
            if _header_row_matches(row):
                skipped += 1
                continue
            doc = _doc_from_row(row)
            if doc:
                all_docs.append(doc)
            else:
                skipped += 1

        # B: latest per motor — prefer newest timestamp (robust across legacy append rows)
        motor_latest: dict[tuple[str, str, str], dict[str, Any]] = {}
        for doc in all_docs:
            key = _motor_key(doc)
            existing = motor_latest.get(key)
            if existing is None or (doc.get("timestamp") or "") >= (existing.get("timestamp") or ""):
                motor_latest[key] = doc

        # A: newest-first head for Recent Readings API
        readings_cache = all_docs[:recent_tail]
        _motor_latest = motor_latest

        logger.info(
            "Cache hydration succeeded — sheet_rows=%d, skipped=%d, "
            "recent_tail=%d, motor_latest=%d",
            len(all_docs),
            skipped,
            len(readings_cache),
            len(_motor_latest),
        )
    except Exception as exc:
        logger.error("Cache hydration failed — cache unchanged: %s", exc)


def init_google_sheets() -> None:
    """
    Initialise the Google Sheets connection at startup.
    Supports two authentication methods:
    1. GOOGLE_SERVICE_ACCOUNT_JSON (Priority 1) - JSON string in env var
    2. GOOGLE_SERVICE_ACCOUNT_FILE (Priority 2, fallback) - File path to service account
    """
    global _sheets_enabled, _sheets_worksheet

    logger.info("Google Sheets init starting...")

    google_sheets_enabled = os.environ.get("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
    logger.info("GOOGLE_SHEETS_ENABLED=%s", google_sheets_enabled)

    if not google_sheets_enabled:
        logger.info("Google Sheets disabled (GOOGLE_SHEETS_ENABLED != true)")
        return

    if not _GSPREAD_AVAILABLE:
        logger.warning(
            "Google Sheets disabled — gspread / google-auth not installed. "
            "Run: pip install gspread google-auth"
        )
        return

    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    logger.info("GOOGLE_SHEET_ID=%r", sheet_id)

    if not sheet_id:
        logger.warning("Google Sheets disabled — GOOGLE_SHEET_ID is not set")
        return

    # Priority 1: Check for GOOGLE_SERVICE_ACCOUNT_JSON env var
    service_account_json = os.environ.get(
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        ""
    ).strip()

    creds = None
    credential_source = None

    if service_account_json:
        try:
            creds_dict = json.loads(service_account_json)
            creds = GServiceCredentials.from_service_account_info(
                creds_dict,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
            credential_source = "GOOGLE_SERVICE_ACCOUNT_JSON env var"
            logger.info("Credential source: %s", credential_source)
        except json.JSONDecodeError as exc:
            logger.error(
                "GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON, falling back to file-based auth: %s",
                exc
            )
        except Exception as exc:
            logger.error(
                "Failed to create credentials from GOOGLE_SERVICE_ACCOUNT_JSON, falling back to file-based auth: %s",
                exc
            )

    # Priority 2: Fallback to GOOGLE_SERVICE_ACCOUNT_FILE
    if creds is None:
        service_account_file = os.environ.get(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            "ecm-project-497106-afa1bd2f0801.json"
        ).strip()

        # Verify and resolve relative paths correctly relative to server.py location
        file_path = Path(service_account_file)
        if not file_path.is_absolute() and not file_path.exists():
            resolved_path = Path(__file__).parent / file_path.name
            if resolved_path.exists():
                service_account_file = str(resolved_path)
                logger.info("Resolved service account file to absolute path: %s", service_account_file)

        if not os.path.exists(service_account_file):
            logger.warning(
                "Google Sheets disabled — service account file not found: %s",
                service_account_file,
            )
            return

        logger.info("Credential source: GOOGLE_SERVICE_ACCOUNT_FILE (%s)", service_account_file)

        try:
            creds = GServiceCredentials.from_service_account_file(
                service_account_file,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ]
            )
            credential_source = "GOOGLE_SERVICE_ACCOUNT_FILE"
        except Exception as exc:
            logger.error("Google Sheets disabled — failed to load credentials from file: %s", exc)
            return

    # Authenticate and initialize Google Sheets
    try:
        client      = gspread.authorize(creds)
        logger.info("Authentication successful")
        
        spreadsheet = client.open_by_key(sheet_id)
        logger.info("Spreadsheet opened successfully")

        worksheet_title = os.environ.get("GOOGLE_SHEET_WORKSHEET", "Readings").strip() or "Readings"
        # Get or create the Readings worksheet
        try:
            worksheet = spreadsheet.worksheet(worksheet_title)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_title, rows=10000, cols=len(_SHEETS_HEADERS)
            )
            worksheet.update(
                [_SHEETS_HEADERS],
                range_name=f"A1:{_sheet_end_col()}1",
                value_input_option="RAW",
            )
            logger.info("Google Sheets — created %r worksheet with headers", worksheet_title)

        _sheets_worksheet = worksheet
        _sheets_enabled   = True

        _ensure_canonical_header_row(worksheet)
        removed_dupes = _remove_duplicate_header_rows(worksheet)
        if removed_dupes:
            logger.warning(
                "Google Sheets — removed %d duplicate header row(s) from data area",
                removed_dupes,
            )

        repair_on_start = os.environ.get(
            "GOOGLE_SHEETS_REPAIR_LAYOUT", "auto"
        ).lower()
        if repair_on_start == "true" or (
            repair_on_start == "auto" and _sheet_needs_repair(worksheet)
        ):
            stats = repair_readings_worksheet_layout(worksheet)
            logger.info("Google Sheets layout repair complete: %s", stats)

        logger.info(
            "Google Sheets ready (sheet_id=%s, worksheet=%r, credential_source=%s)",
            sheet_id,
            worksheet_title,
            credential_source,
        )

    except json.JSONDecodeError as exc:
        logger.error("Google Sheets disabled — JSON validation error: %s", exc)
    except gspread.exceptions.SpreadsheetNotFound as exc:
        logger.error("Google Sheets disabled — Spreadsheet not found (404) for ID %r: %s", sheet_id, exc)
    except gspread.exceptions.APIError as exc:
        logger.error("Google Sheets disabled — API error during init: %s", exc)
    except Exception as exc:
        logger.error("Google Sheets disabled — unexpected error during init: %s", exc)


def save_reading_to_sheets(doc: dict[str, Any]) -> None:
    """
    Persist a single reading document to the Readings worksheet.
    Inserts at row 2 so the newest entry appears directly below the header.
    Called by /condition-monitoring (single-entry path).
    """
    if not _sheets_enabled or _sheets_worksheet is None:
        return
    try:
        _sheets_worksheet.insert_row(
            _row_from_doc(doc),
            index=_SHEETS_DATA_START_ROW,
            value_input_option="RAW",
        )
        logger.info(
            "Saved 1 reading to Google Sheets at row %d (motor=%s, plant=%s, machine=%s)",
            _SHEETS_DATA_START_ROW,
            doc.get("motor"), doc.get("plant"), doc.get("machine"),
        )
    except gspread.exceptions.APIError as exc:
        logger.error("Google Sheets write failed (APIError): %s", exc)
    except Exception as exc:
        logger.error("Google Sheets write failed: %s", exc)


def save_bulk_readings_to_sheets(docs: list[dict[str, Any]]) -> None:
    """
    Persist multiple reading documents to the Readings worksheet.
    Inserts starting at row 2 so the batch appears at the top (newest first).
    Called by /condition-monitoring/bulk.
    """
    if not _sheets_enabled or _sheets_worksheet is None:
        return
    if not docs:
        return
    try:
        rows = [_row_from_doc(doc) for doc in docs]
        _sheets_worksheet.insert_rows(
            rows,
            row=_SHEETS_DATA_START_ROW,
            value_input_option="RAW",
        )
        motors = ", ".join(f"{d.get('motor')}" for d in docs)
        logger.info(
            "Saved %d reading(s) to Google Sheets at row %d (bulk, plant=%s, machine=%s, motors=[%s])",
            len(rows),
            _SHEETS_DATA_START_ROW,
            docs[0].get("plant") if docs else "",
            docs[0].get("machine") if docs else "",
            motors,
        )
    except gspread.exceptions.APIError as exc:
        logger.error("Google Sheets bulk write failed (APIError): %s", exc)
    except Exception as exc:
        logger.error("Google Sheets bulk write failed: %s", exc)


def _optional_measurement(value: Any) -> float | None:
    if value in ("", None):
        return None
    return value


def _vibration_from_payload(payload: dict[str, Any]) -> float | None:
    """
    TODO: Remove after frontend Change 2 — accept legacy ``i2t`` as ``vibration``.
    """
    if payload.get("vibration") not in ("", None):
        return _optional_measurement(payload.get("vibration"))
    if payload.get("i2t") not in ("", None):
        return _optional_measurement(payload.get("i2t"))
    return None


def _vibration_limit_from_payload(payload: dict[str, Any], limit_key: str, legacy_key: str) -> Any:
    """
    TODO: Remove after frontend Change 2 — accept legacy i2t limit keys on stored docs.
    """
    if payload.get(limit_key) not in ("", None):
        return payload.get(limit_key)
    return payload.get(legacy_key)


def reading_doc_from_result(
    plant_id: str,
    machine_id: str,
    result: MotorResult,
    source: dict[str, Any] | None = None,
    bulk_entry: bool = False,
) -> dict[str, Any]:
    source = source or {}
    params = result.parameters
    current = params.get("current")
    temperature = params.get("temperature")
    vibration = params.get("vibration")
    photo = _photo_for_storage(source)
    return {
        "id": str(uuid.uuid4()),
        "plant": plant_id,
        "machine": machine_id,
        "motor": result.motor,
        "current": current.value if current else source.get("current"),
        "temperature": temperature.value if temperature else source.get("temperature"),
        "vibration": vibration.value if vibration else _vibration_from_payload(source),
        "normal_current": current.normal_limit if current else source.get("normal_current"),
        "warning_current": current.warning_limit if current else source.get("warning_current"),
        "normal_temperature": temperature.normal_limit if temperature else source.get("normal_temperature"),
        "warning_temperature": temperature.warning_limit if temperature else source.get("warning_temperature"),
        "normal_vibration": (
            vibration.normal_limit
            if vibration
            else _vibration_limit_from_payload(source, "normal_vibration", "normal_i2t")
        ),
        "warning_vibration": (
            vibration.warning_limit
            if vibration
            else _vibration_limit_from_payload(source, "warning_vibration", "warning_i2t")
        ),
        "status": result.overall_status,
        "timestamp": result.timestamp,
        "entry_source": source.get("entry_source"),
        "verified_by": source.get("verified_by") or source.get("technician"),
        "notes": source.get("notes"),
        "photo_filename": source.get("photo_filename") or "",
        "photo": photo,
        "has_photo": bool(photo),
        "bulk_entry": bulk_entry,
    }


async def process_and_store_readings(
    payload: ReadingsBatchRequest,
    source_readings: list[dict[str, Any]] | None = None,
    bulk_entry: bool = False,
    strict: bool = False,
    batch_meta: dict[str, Any] | None = None,
) -> ReadingsBatchResponse:
    response = await submit_readings(payload, strict=strict)
    source_by_motor = {
        item.get("motor"): item
        for item in (source_readings or [])
        if isinstance(item, dict)
    }
    new_docs: list[dict[str, Any]] = []
    for result in response.results:
        source = _merge_reading_source(
            source_by_motor.get(result.motor, {}),
            batch_meta,
        )
        doc = reading_doc_from_result(
            payload.plant_id,
            payload.machine_id,
            result,
            source,
            bulk_entry=bulk_entry,
        )
        new_docs.append(doc)
    if new_docs:
        readings_cache[0:0] = new_docs
        for doc in new_docs:
            _set_motor_latest(doc)
    if len(readings_cache) > 1000:
        del readings_cache[1000:]

    # ── Persist to Google Sheets ──
    if bulk_entry:
        save_bulk_readings_to_sheets(new_docs)
    else:
        for doc in new_docs:
            save_reading_to_sheets(doc)
    return response


def latest_readings() -> list[dict[str, Any]]:
    """
    Return the most recent reading for each unique (plant, machine, motor) tuple.

    Uses _motor_latest (full-sheet latest on startup + live updates on submit).
    """
    return list(_motor_latest.values())


def get_latest_health_counts(plant_id: str | None = None, machine_id: str | None = None) -> dict[str, int]:
    """
    Calculate health status counts from ONLY the most recent reading per motor.
    Optionally filter by plant_id and/or machine_id.
    
    Uses latest_readings() to ensure no historical readings are included.
    
    Returns: {"ok": int, "warning": int, "alarm": int}
    """
    latest = latest_readings()
    
    # Filter by plant/machine if specified
    filtered = [
        r for r in latest
        if (plant_id is None or r["plant"] == plant_id)
        and (machine_id is None or r["machine"] == machine_id)
    ]
    
    return {
        "ok": sum(1 for r in filtered if r["status"] == STATUS_NORMAL),
        "warning": sum(1 for r in filtered if r["status"] == STATUS_WARNING),
        "alarm": sum(1 for r in filtered if r["status"] == STATUS_ALARM),
    }


# ════════════════════════════════════════════════════════════════�[...]
# Pydantic Schemas
# ════════════════════════════════════════════════════════════════�[...]

class MotorReading(BaseModel):
    """A single sensor reading for one motor."""
    motor:       str            = Field(..., description="Motor name, must match machine_config.json")
    current:     float | None  = Field(None, ge=0.0, description="Phase current in Amperes")
    temperature: float | None  = Field(None, ge=0.0, description="Motor temperature in °C")
    vibration:   float | None  = Field(None, ge=0.0, description="Vibration in mm/s")
    timestamp:   str  | None  = Field(None, description="ISO-8601 UTC timestamp; auto-filled if absent")

    @model_validator(mode="after")
    def at_least_one_param(self) -> MotorReading:
        if self.current is None and self.temperature is None and self.vibration is None:
            raise ValueError("At least one of current / temperature / vibration must be provided.")
        return self


class ReadingsBatchRequest(BaseModel):
    """Batch of motor readings for a specific machine."""
    plant_id:   str                  = Field(..., examples=["GT"])
    machine_id: str                  = Field(..., examples=["G1 Lehr"])
    readings:   list[MotorReading]   = Field(..., min_length=1)


class ParameterStatus(BaseModel):
    """Status detail for a single parameter."""
    value:         float
    normal_limit:  float
    warning_limit: float
    status:        str   = Field(..., pattern="^(Normal|Warning|Alarm)$")


class MotorResult(BaseModel):
    """Classification result for a single motor."""
    motor:          str
    overall_status: str = Field(..., pattern="^(Normal|Warning|Alarm)$")
    parameters:     dict[str, ParameterStatus]
    timestamp:      str


class ReadingsBatchResponse(BaseModel):
    """Full response for a batch of readings."""
    plant_id:      str
    machine_id:    str
    processed_at:  str
    summary: dict[str, int] = Field(
        description="Count of motors per status level"
    )
    results:       list[MotorResult]
    skipped_count: int = Field(0, description="Motors that failed config lookup")
    errors:        list[str] = Field(default_factory=list, description="Per-motor error messages")


class MotorConfigResponse(BaseModel):
    """Thresholds returned for a single motor."""
    plant_id:   str
    machine_id: str
    motor:      str
    thresholds: dict[str, float]
    parameters: list[str]


class MachineConfigResponse(BaseModel):
    """All motor thresholds for a machine."""
    plant_id:   str
    machine_id: str
    parameters: list[str]
    motors:     dict[str, dict[str, float]]


# ════════════════════════════════════════════════════════════════�[...]
# Application Bootstrap
# ════════════════════════════════════════════════════════════════�[...]

app = FastAPI(
    title="Electrical Condition Monitoring API",
    description=(
        "Threshold-based motor health monitoring. "
        "All limits are driven by machine_config.json – zero hardcoded values."
    ),
    version="3.0.0",
)
app.include_router(gmd_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _dashboard_static_status() -> dict[str, Any]:
    """Inspect backend/static for the React build (used by /health and startup)."""
    index = STATIC_DIR / "index.html"
    entries: list[str] = []
    if STATIC_DIR.is_dir():
        try:
            entries = sorted(p.name for p in STATIC_DIR.iterdir())[:25]
        except OSError:
            entries = []
    return {
        "dashboard_ready": index.is_file(),
        "index_html": str(index),
        "static_dir": str(STATIC_DIR),
        "static_dir_exists": STATIC_DIR.is_dir(),
        "static_entry_count": len(entries),
        "static_entries": entries,
    }


@app.on_event("startup")
async def startup_event() -> None:
    app.state.config = load_config()
    init_google_sheets()
    hydrate_readings_cache_from_sheets(recent_tail=_RECENT_HISTORY_TAIL)
    ui = _dashboard_static_status()
    if ui["dashboard_ready"]:
        logger.info("Dashboard UI ready (%s)", ui["index_html"])
    else:
        logger.warning(
            "Dashboard UI not deployed — %s not found (static entries: %s). "
            "Render build must run ./build.sh to copy frontend/build into backend/static.",
            ui["index_html"],
            ui["static_entries"] or "(empty)",
        )
    logger.info("Condition monitoring server ready.")


# ════════════════════════════════════════════════════════════════�[...]
# Routes – Configuration Inspection
# ════════════════════════════════════════════════════════════════�[...]

@app.get(
    "/config/{plant_id}/{machine_id}",
    response_model=MachineConfigResponse,
    tags=["Configuration"],
    summary="Get all motor thresholds for a machine",
)
async def get_machine_config(plant_id: str, machine_id: str) -> MachineConfigResponse:
    config: dict[str, Any] = app.state.config
    canonical_machine = resolve_machine_id(config, plant_id, machine_id)
    machine = config["plants"][plant_id]["machines"][canonical_machine]
    return MachineConfigResponse(
        plant_id=plant_id,
        machine_id=canonical_machine,
        parameters=machine["parameters"],
        motors=machine["motors"],
    )


@app.get(
    "/config/{plant_id}/{machine_id}/{motor_name}",
    response_model=MotorConfigResponse,
    tags=["Configuration"],
    summary="Get thresholds for a single motor",
)
async def get_motor_config(
    plant_id: str, machine_id: str, motor_name: str
) -> MotorConfigResponse:
    config: dict[str, Any] = app.state.config
    thresholds = get_motor_thresholds(config, plant_id, machine_id, motor_name)
    params = get_machine_parameters(config, plant_id, machine_id)
    return MotorConfigResponse(
        plant_id=plant_id,
        machine_id=machine_id,
        motor=motor_name,
        thresholds=thresholds,
        parameters=params,
    )


@app.get(
    "/config/plants",
    tags=["Configuration"],
    summary="List all configured plants and machines",
)
async def list_plants() -> dict[str, Any]:
    config: dict[str, Any] = app.state.config
    result = {}
    for plant_id, plant_data in config["plants"].items():
        result[plant_id] = {
            "name": plant_data.get("name"),
            "machines": {
                mid: {
                    "parameters": mdata.get("parameters", []),
                    "motor_count": len(mdata.get("motors", {})),
                }
                for mid, mdata in plant_data["machines"].items()
            },
        }
    return result


# ════════════════════════════════════════════════════════════════�[...]
# Routes – Readings & Status
# ════════════════════════════════════════════════════════════════�[...]

@app.post(
    "/readings",
    response_model=ReadingsBatchResponse,
    tags=["Readings"],
    summary="Submit motor readings and receive status classification",
)
async def submit_readings(
    payload: ReadingsBatchRequest,
    *,
    strict: bool = False,
) -> ReadingsBatchResponse:
    config: dict[str, Any] = app.state.config
    canonical_machine = resolve_machine_id(
        config, payload.plant_id, payload.machine_id
    )
    active_params = get_machine_parameters(
        config, payload.plant_id, canonical_machine
    )

    results: list[MotorResult] = []
    errors: list[str] = []

    for reading in payload.readings:
        try:
            _, canonical_motor, thresholds = get_motor_thresholds_resolved(
                config,
                payload.plant_id,
                canonical_machine,
                reading.motor,
            )
            resolved = reading.model_copy(update={"motor": canonical_motor})
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            errors.append(detail)
            continue

        result = classify_motor_reading(resolved, thresholds, active_params)
        results.append(result)

    if errors:
        logger.warning("Skipped %d unrecognised motors: %s", len(errors), errors)
        if strict:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": (
                        f"Could not process {len(errors)} of {len(payload.readings)} "
                        f"equipment reading(s) for area {canonical_machine!r}"
                    ),
                    "skipped_count": len(errors),
                    "inserted_count": len(results),
                    "errors": errors,
                },
            )

    if strict and len(results) != len(payload.readings):
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Not all equipment readings were processed",
                "skipped_count": len(payload.readings) - len(results),
                "inserted_count": len(results),
                "errors": errors,
            },
        )

    results.sort(key=severity_order)

    summary = {STATUS_NORMAL: 0, STATUS_WARNING: 0, STATUS_ALARM: 0}
    for r in results:
        summary[r.overall_status] += 1

    return ReadingsBatchResponse(
        plant_id=payload.plant_id,
        machine_id=canonical_machine,
        processed_at=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        results=results,
        skipped_count=len(errors),
        errors=errors,
    )


@app.post(
    "/readings/single",
    response_model=MotorResult,
    tags=["Readings"],
    summary="Submit a single motor reading",
)
async def submit_single_reading(
    plant_id: str,
    machine_id: str,
    reading: MotorReading,
) -> MotorResult:
    config: dict[str, Any] = app.state.config
    active_params = get_machine_parameters(config, plant_id, machine_id)
    thresholds    = get_motor_thresholds(config, plant_id, machine_id, reading.motor)
    return classify_motor_reading(reading, thresholds, active_params)


@app.post("/condition-monitoring/bulk", tags=["Compatibility"])
@app.post("/api/condition-monitoring/bulk", tags=["Compatibility"])
async def add_bulk_condition_data(data: dict[str, Any]) -> dict[str, Any]:
    plant_id = data.get("plant_id") or data.get("plant")
    machine_id = data.get("machine_id") or data.get("machine")
    readings = data.get("readings") or []
    if not plant_id or not machine_id or not readings:
        raise HTTPException(status_code=422, detail="plant, machine and readings are required")

    config: dict[str, Any] = app.state.config
    canonical_machine = resolve_machine_id(config, plant_id, machine_id)

    motor_readings: list[MotorReading] = []
    for item in readings:
        if not isinstance(item, dict):
            raise HTTPException(status_code=422, detail="Each reading must be an object")
        motor_name = item.get("motor") or item.get("equipment")
        if not motor_name:
            raise HTTPException(
                status_code=422,
                detail="Each reading requires a motor (equipment) name",
            )
        motor_readings.append(
            MotorReading(
                motor=str(motor_name).strip(),
                current=_optional_measurement(item.get("current")),
                temperature=_optional_measurement(item.get("temperature")),
                vibration=_vibration_from_payload(item),
                timestamp=item.get("timestamp"),
            )
        )

    payload = ReadingsBatchRequest(
        plant_id=plant_id,
        machine_id=canonical_machine,
        readings=motor_readings,
    )
    batch_meta = _batch_meta_from_request(data)
    response = await process_and_store_readings(
        payload, readings, bulk_entry=True, strict=True, batch_meta=batch_meta
    )
    inserted = len(response.results)
    if inserted == 0:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "No readings were stored",
                "inserted_count": 0,
                "skipped_count": response.skipped_count,
                "errors": response.errors,
            },
        )
    return {
        "message": "Bulk readings submitted successfully",
        "plant": payload.plant_id,
        "machine": response.machine_id,
        "inserted_count": inserted,
        "skipped_count": response.skipped_count,
        "expected_count": len(motor_readings),
        "summary": response.summary,
        "errors": response.errors,
        "results": [result.model_dump() for result in response.results],
    }


@app.post("/condition-monitoring", tags=["Compatibility"])
@app.post("/api/condition-monitoring", tags=["Compatibility"])
async def add_condition_data(data: dict[str, Any]) -> dict[str, Any]:
    plant_id = data.get("plant_id") or data.get("plant")
    machine_id = data.get("machine_id") or data.get("machine")
    if not plant_id or not machine_id or not data.get("motor"):
        raise HTTPException(status_code=422, detail="plant, machine and motor are required")

    payload = ReadingsBatchRequest(
        plant_id=plant_id,
        machine_id=machine_id,
        readings=[
            MotorReading(
                motor=data.get("motor"),
                current=_optional_measurement(data.get("current")),
                temperature=_optional_measurement(data.get("temperature")),
                vibration=_vibration_from_payload(data),
                timestamp=data.get("timestamp"),
            )
        ],
    )
    batch_meta = _batch_meta_from_request(data)
    response = await process_and_store_readings(
        payload, [data], bulk_entry=False, strict=True, batch_meta=batch_meta
    )
    if not response.results:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Reading was not stored",
                "errors": response.errors,
            },
        )
    result = response.results[0]
    return {
        "message": "Reading submitted successfully",
        "bulk_entry_flag": False,
        "inserted_count": 1,
        "status": result.overall_status,
        "result": result.model_dump(),
    }


@app.get("/condition-monitoring/machine/{plant_id}/{machine_id}", tags=["Compatibility"])
@app.get("/api/condition-monitoring/machine/{plant_id}/{machine_id}", tags=["Compatibility"])
async def get_machine_readings(plant_id: str, machine_id: str) -> list[dict[str, Any]]:
    return [
        reading
        for reading in readings_cache
        if reading["plant"] == plant_id and reading["machine"] == machine_id
    ]


@app.get("/condition-monitoring/plant/{plant_id}", tags=["Compatibility"])
@app.get("/api/condition-monitoring/plant/{plant_id}", tags=["Compatibility"])
async def get_plant_readings(plant_id: str) -> list[dict[str, Any]]:
    return [reading for reading in readings_cache if reading["plant"] == plant_id]


@app.get("/condition-monitoring/recent", tags=["Compatibility"])
@app.get("/api/condition-monitoring/recent", tags=["Compatibility"])
async def get_recent_readings(limit: int = 25) -> list[dict[str, Any]]:
    return readings_cache[:limit]


@app.get("/active-alarms", tags=["Compatibility"])
@app.get("/api/active-alarms", tags=["Compatibility"])
async def get_active_alarms() -> list[dict[str, Any]]:
    """
    Return only unacknowledged alarms from the most recent reading of each motor.
    If the latest reading for a motor has status='Normal' or 'Warning', 
    it will NOT appear in this list regardless of prior alarm history.
    """
    latest = latest_readings()
    return [
        reading
        for reading in latest
        if reading["status"] == STATUS_ALARM and reading["id"] not in acknowledged_alarm_ids
    ]


@app.post("/acknowledge-alarm/{alarm_id}", tags=["Compatibility"])
@app.post("/api/acknowledge-alarm/{alarm_id}", tags=["Compatibility"])
async def acknowledge_alarm(alarm_id: str) -> dict[str, str]:
    acknowledged_alarm_ids.add(alarm_id)
    return {"status": "ok", "id": alarm_id}


@app.get("/machine-health/{plant_id}", tags=["Compatibility"])
@app.get("/api/machine-health/{plant_id}", tags=["Compatibility"])
async def get_machine_health(plant_id: str) -> list[dict[str, Any]]:
    """
    Return health status for each machine in a plant.
    Calculations use ONLY the latest reading per motor via get_latest_health_counts().
    """
    config: dict[str, Any] = app.state.config
    machines = config["plants"].get(plant_id, {}).get("machines", {})
    result = []
    
    for machine_id, machine_data in machines.items():
        # Use helper function to get counts from latest readings only
        counts = get_latest_health_counts(plant_id=plant_id, machine_id=machine_id)
        configured_total = len(machine_data.get("motors", {}))
        monitored_total = counts["ok"] + counts["warning"] + counts["alarm"]

        # Determine worst status from readings; unmonitored equipment defaults to Normal
        statuses = []
        if counts["alarm"] > 0:
            statuses.append(STATUS_ALARM)
        if counts["warning"] > 0:
            statuses.append(STATUS_WARNING)
        if counts["ok"] > 0 or monitored_total < configured_total:
            statuses.append(STATUS_NORMAL)

        worst_status = max(statuses, key=status_rank) if statuses else STATUS_NORMAL

        result.append(
            {
                "plant": plant_id,
                "machine": machine_id,
                "status": worst_status,
                "ok": counts["ok"],
                "warning": counts["warning"],
                "alarm": counts["alarm"],
                "total": configured_total,
                "monitored": monitored_total,
                "unmonitored": max(0, configured_total - monitored_total),
                "health_percent": health_percent_for_status(worst_status),
            }
        )
    return result


@app.get("/plant-health", tags=["Compatibility"])
@app.get("/api/plant-health", tags=["Compatibility"])
async def get_plant_health() -> list[dict[str, Any]]:
    """
    Return health status for all plants.
    Calculations use ONLY the latest reading per motor via get_latest_health_counts().
    """
    config: dict[str, Any] = app.state.config
    result = []
    
    for plant_id, plant_data in config["plants"].items():
        # Use helper function to get counts from latest readings only
        counts = get_latest_health_counts(plant_id=plant_id)
        
        # Determine worst status
        statuses = []
        if counts["alarm"] > 0:
            statuses.append(STATUS_ALARM)
        if counts["warning"] > 0:
            statuses.append(STATUS_WARNING)
        if counts["ok"] > 0:
            statuses.append(STATUS_NORMAL)
        
        worst_status = max(statuses, key=status_rank) if statuses else STATUS_NORMAL
        total = counts["ok"] + counts["warning"] + counts["alarm"]
        
        result.append(
            {
                "plant": plant_id,
                "status": worst_status,
                "ok": counts["ok"],
                "warning": counts["warning"],
                "alarm": counts["alarm"],
                "total": total,
                "health_percent": health_percent_for_status(worst_status),
            }
        )
    return result


@app.post("/api/query", tags=["Compatibility"])
async def expert_query(data: dict[str, Any]) -> dict[str, Any]:
    query = data.get("query", "")
    return {"status": "success", "query_received": query, "response": "Query tracking placeholder."}


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """
    Liveness/readiness probe.

    ``dashboard_ready`` is True only when ``backend/static/index.html`` exists
  (produced by ``./build.sh`` on deploy). If False while you see a UI in the
  browser, you are likely on ``localhost:3000`` (dev server), not this host.
    """
    ui = _dashboard_static_status()
    return {
        "status": "ok",
        "version": app.version,
        "sheets_enabled": str(_sheets_enabled),
        "dashboard_ready": str(ui["dashboard_ready"]),
        "static_dir": ui["static_dir"],
        "static_dir_exists": str(ui["static_dir_exists"]),
        "static_entry_count": ui["static_entry_count"],
        "static_entries": ui["static_entries"],
    }


# ── React dashboard (built into backend/static at deploy time) ─────────────────
_SPA_API_PREFIXES = (
    "api/",
    "config/",
    "docs",
    "openapi.json",
    "health",
    "readings",
    "condition-monitoring",
    "machine-health",
    "plant-health",
    "active-alarms",
    "acknowledge-alarm",
)


def _dashboard_index() -> Path:
    return STATIC_DIR / "index.html"


def _serve_dashboard_index() -> FileResponse | JSONResponse:
    index = _dashboard_index()
    if index.is_file():
        return FileResponse(index)
    return JSONResponse(
        status_code=503,
        content={
            "service": "Electrical Condition Monitoring API",
            "dashboard_ready": False,
            "docs": "/docs",
            "health": "/health",
            "hint": "Run build.sh (or Render buildCommand) to compile frontend into backend/static",
        },
    )


@app.get("/", include_in_schema=False, response_model=None)
async def dashboard_root():
    return _serve_dashboard_index()


@app.get("/{spa_path:path}", include_in_schema=False, response_model=None)
async def dashboard_spa_or_asset(spa_path: str):
    if spa_path.startswith(_SPA_API_PREFIXES):
        raise HTTPException(status_code=404, detail="Not Found")
    asset = STATIC_DIR / spa_path
    if asset.is_file():
        return FileResponse(asset)
    return _serve_dashboard_index()
