"""
Diagnostic logging for Google Sheets / gspread API calls.

Logs every operation with worksheet name, prints full tracebacks on failure,
and identifies the exact failing call. Does not alter API results or control flow.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Callable, TypeVar

logger = logging.getLogger("gmd_condition_monitoring.sheets_api")

T = TypeVar("T")


def worksheet_name(worksheet: Any | None, fallback: str = "<unknown>") -> str:
    """Resolve a worksheet title for log messages."""
    if worksheet is None:
        return fallback
    try:
        title = getattr(worksheet, "title", None)
        if title:
            return str(title)
    except Exception:
        pass
    return fallback


def log_api_call_start(
    worksheet_name: str,
    operation: str,
    *,
    spreadsheet_id: str | None = None,
    **details: Any,
) -> None:
    parts = [
        f"worksheet={worksheet_name!r}",
        f"operation={operation}",
    ]
    if spreadsheet_id:
        parts.append(f"spreadsheet_id={spreadsheet_id!r}")
    for key, value in details.items():
        parts.append(f"{key}={value!r}")
    logger.info("Google Sheets API call starting: %s", ", ".join(parts))


def log_api_call_success(
    worksheet_name: str,
    operation: str,
    **details: Any,
) -> None:
    parts = [f"worksheet={worksheet_name!r}", f"operation={operation}"]
    for key, value in details.items():
        parts.append(f"{key}={value!r}")
    logger.info("Google Sheets API call succeeded: %s", ", ".join(parts))


def log_api_call_failure(
    worksheet_name: str,
    operation: str,
    exc: BaseException,
    *,
    spreadsheet_id: str | None = None,
    **details: Any,
) -> None:
    parts = [f"worksheet={worksheet_name!r}", f"operation={operation}"]
    if spreadsheet_id:
        parts.append(f"spreadsheet_id={spreadsheet_id!r}")
    for key, value in details.items():
        parts.append(f"{key}={value!r}")
    logger.error(
        "Google Sheets API call FAILED: %s | error=%s\n%s",
        ", ".join(parts),
        exc,
        traceback.format_exc(),
    )


def run_sheets_api(
    worksheet_name: str,
    operation: str,
    fn: Callable[[], T],
    *,
    spreadsheet_id: str | None = None,
    **details: Any,
) -> T:
    """
    Execute a gspread/Sheets API callable with diagnostic logging.

    Re-raises the original exception after logging traceback.
    """
    log_api_call_start(
        worksheet_name,
        operation,
        spreadsheet_id=spreadsheet_id,
        **details,
    )
    try:
        result = fn()
    except Exception as exc:
        log_api_call_failure(
            worksheet_name,
            operation,
            exc,
            spreadsheet_id=spreadsheet_id,
            **details,
        )
        raise
    log_api_call_success(worksheet_name, operation, **details)
    return result
