"""
Reusable Google Sheets row fixtures for QA test data sets (DATA-SET-A through G).

Rows match the 10-column GMD schema used by routes/dashboard.py.
These are data-only rows (no header); conftest prepends GMD_SHEET_HEADERS.
"""

from __future__ import annotations

from typing import List

DEFAULT_EQUIPMENT = "MCB-1"
DEFAULT_CATEGORY = "Blowers"
DEFAULT_LOCATION = "Plant"
DEFAULT_VERIFIED_BY = "QA Tester"
DEFAULT_ENTRY_SOURCE = "QA"

TS_PRIMARY = "2026-06-08 10:00:00"
TS_EARLIER = "2026-06-08 09:00:00"


def make_sheet_row(
    timestamp: str,
    parameter: str,
    value: str | float,
    status: str,
    *,
    equipment: str = DEFAULT_EQUIPMENT,
    category: str = DEFAULT_CATEGORY,
    remarks: str = "",
) -> List[str]:
    """Build one GMD sheet data row (columns A–J, 0-indexed)."""
    return [
        timestamp,
        category,
        equipment,
        parameter,
        DEFAULT_LOCATION,
        str(value),
        status.upper(),
        DEFAULT_VERIFIED_BY,
        remarks,
        DEFAULT_ENTRY_SOURCE,
    ]


def build_data_set_a() -> List[List[str]]:
    """DATA-SET-A — all parameters NORMAL (TC-AGG-01 baseline)."""
    return [
        make_sheet_row(TS_PRIMARY, "temperature", 42, "NORMAL", remarks="DATA-SET-A"),
        make_sheet_row(TS_PRIMARY, "current", 8.5, "NORMAL", remarks="DATA-SET-A"),
        make_sheet_row(TS_PRIMARY, "vertical_vibration", 1.2, "NORMAL", remarks="DATA-SET-A"),
    ]


def build_data_set_b() -> List[List[str]]:
    """DATA-SET-B — one WARNING on current (TC-AGG-02)."""
    return [
        make_sheet_row(TS_PRIMARY, "temperature", 42, "NORMAL", remarks="DATA-SET-B"),
        make_sheet_row(TS_PRIMARY, "current", 12, "WARNING", remarks="DATA-SET-B"),
        make_sheet_row(TS_PRIMARY, "vertical_vibration", 1.2, "NORMAL", remarks="DATA-SET-B"),
    ]


def build_data_set_c() -> List[List[str]]:
    """DATA-SET-C — one ALARM on vertical_vibration (TC-AGG-03)."""
    return [
        make_sheet_row(TS_PRIMARY, "temperature", 42, "NORMAL", remarks="DATA-SET-C"),
        make_sheet_row(TS_PRIMARY, "current", 8.5, "NORMAL", remarks="DATA-SET-C"),
        make_sheet_row(TS_PRIMARY, "vertical_vibration", 8.0, "ALARM", remarks="DATA-SET-C"),
    ]


def build_data_set_d() -> List[List[str]]:
    """DATA-SET-D — WARNING on current + ALARM on vertical_vibration (TC-AGG-04)."""
    return [
        make_sheet_row(TS_PRIMARY, "temperature", 42, "NORMAL", remarks="DATA-SET-D"),
        make_sheet_row(TS_PRIMARY, "current", 12, "WARNING", remarks="DATA-SET-D"),
        make_sheet_row(TS_PRIMARY, "vertical_vibration", 8.0, "ALARM", remarks="DATA-SET-D"),
    ]


def build_data_set_e() -> List[List[str]]:
    """DATA-SET-E — three ALARM parameters (TC-AGG-05)."""
    return [
        make_sheet_row(TS_PRIMARY, "temperature", 90, "ALARM", remarks="DATA-SET-E"),
        make_sheet_row(TS_PRIMARY, "current", 20, "ALARM", remarks="DATA-SET-E"),
        make_sheet_row(TS_PRIMARY, "vertical_vibration", 9.0, "ALARM", remarks="DATA-SET-E"),
    ]


def build_data_set_f() -> List[List[str]]:
    """DATA-SET-F — missing vertical_vibration row (TC-AGG-06)."""
    return [
        make_sheet_row(TS_PRIMARY, "temperature", 42, "NORMAL", remarks="DATA-SET-F"),
        make_sheet_row(TS_PRIMARY, "current", 12, "WARNING", remarks="DATA-SET-F"),
    ]


def build_data_set_g() -> List[List[str]]:
    """DATA-SET-G — older ALARM vibration + newer NORMAL params (TC-AGG-07)."""
    return [
        make_sheet_row(TS_EARLIER, "vertical_vibration", 8.0, "ALARM", remarks="DATA-SET-G"),
        make_sheet_row(TS_PRIMARY, "temperature", 42, "NORMAL", remarks="DATA-SET-G"),
        make_sheet_row(TS_PRIMARY, "current", 8.5, "NORMAL", remarks="DATA-SET-G"),
    ]


# Module-level constants for direct import in tests
DATA_SET_A = build_data_set_a()
DATA_SET_B = build_data_set_b()
DATA_SET_C = build_data_set_c()
DATA_SET_D = build_data_set_d()
DATA_SET_E = build_data_set_e()
DATA_SET_F = build_data_set_f()
DATA_SET_G = build_data_set_g()
