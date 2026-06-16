"""
Centralized Google Sheets data access layer for GMD readings.

Handles per-area worksheet routing, merged reads, and canonical row inserts.
All modules (dashboard, reports, trends, submit) consume data through
GMDGoogleSheetsService which delegates to this layer.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from typing import Any

from services.sheets_api_diagnostics import log_api_call_failure, run_sheets_api
from services.sheets_area_registry import (
    get_area_worksheet_names,
    include_legacy_readings_worksheet,
    is_multi_area_layout_enabled,
    iter_area_worksheets_for_read,
    resolve_area_worksheet,
)
from services.sheets_config import (
    ReadingRowRecord,
    build_reading_row,
    ensure_gmd_header_row,
    get_or_create_worksheet,
    get_spreadsheet_id,
    get_worksheet_name,
    normalize_readings_worksheet,
    worksheet_has_horizontal_drift,
)
from services.gmd_datetime import reading_timestamp_sort_key
from services.sheets_row_model import GMD_SHEET_HEADERS

logger = logging.getLogger("gmd_condition_monitoring.sheets_data_access")


class SheetsDataAccess:
    """Thread-safe worksheet manager for multi-area GMD Google Sheets layout."""

    def __init__(self, client: Any, spreadsheet: Any) -> None:
        self._client = client
        self._spreadsheet = spreadsheet
        self._multi_area = is_multi_area_layout_enabled()
        self._cache_lock = threading.Lock()
        self._cache_timestamp = 0.0
        self._cache_ttl_seconds = 45
        self._cached_values: list[list[str]] | None = None
        self._worksheets: dict[str, Any] = {}
        self._legacy_worksheet_name = get_worksheet_name()

        if self._multi_area:
            self._initialize_area_worksheets()
        else:
            self._initialize_legacy_worksheet()

    @property
    def multi_area_enabled(self) -> bool:
        return self._multi_area

    def set_cache_ttl(self, seconds: int) -> None:
        self._cache_ttl_seconds = max(30, min(int(seconds), 300))

    def _initialize_area_worksheets(self) -> None:
        sheet_id = get_spreadsheet_id()
        for area_name in get_area_worksheet_names():
            logger.info(
                "Initializing area worksheet access: worksheet=%r spreadsheet_id=%r",
                area_name,
                sheet_id,
            )
            worksheet = get_or_create_worksheet(self._spreadsheet, area_name)
            ensure_gmd_header_row(worksheet)
            self._repair_if_needed(worksheet, area_name)
            self._worksheets[area_name] = worksheet
            logger.info("Area worksheet ready: %r", area_name)

        if include_legacy_readings_worksheet():
            legacy_name = self._legacy_worksheet_name
            if legacy_name not in self._worksheets:
                try:
                    legacy_ws = run_sheets_api(
                        legacy_name,
                        "spreadsheet.worksheet",
                        lambda: self._spreadsheet.worksheet(legacy_name),
                        spreadsheet_id=sheet_id,
                    )
                    ensure_gmd_header_row(legacy_ws)
                    self._worksheets[f"__legacy__:{legacy_name}"] = legacy_ws
                    logger.info(
                        "Legacy readings worksheet registered for merge: %r",
                        legacy_name,
                    )
                except Exception as exc:
                    log_api_call_failure(
                        legacy_name,
                        "spreadsheet.worksheet (legacy merge registration)",
                        exc,
                        spreadsheet_id=sheet_id,
                    )
                    logger.warning(
                        "No legacy worksheet %r to merge: %s",
                        legacy_name,
                        exc,
                    )

    def _initialize_legacy_worksheet(self) -> None:
        worksheet = get_or_create_worksheet(
            self._spreadsheet,
            self._legacy_worksheet_name,
        )
        ensure_gmd_header_row(worksheet)
        self._repair_if_needed(worksheet, self._legacy_worksheet_name)
        self._worksheets[self._legacy_worksheet_name] = worksheet

    def _repair_if_needed(self, worksheet: Any, label: str) -> None:
        sheet_id = get_spreadsheet_id()
        existing_values = run_sheets_api(
            label,
            "worksheet.get_all_values",
            lambda: worksheet.get_all_values(),
            spreadsheet_id=sheet_id,
            context="repair_check",
        )
        if worksheet_has_horizontal_drift(existing_values):
            stats = normalize_readings_worksheet(worksheet)
            logger.warning(
                "Repaired horizontally drifted worksheet %r: %s",
                label,
                stats,
            )
        elif worksheet.col_count > len(GMD_SHEET_HEADERS):
            run_sheets_api(
                label,
                "worksheet.resize",
                lambda: worksheet.resize(cols=len(GMD_SHEET_HEADERS)),
                spreadsheet_id=sheet_id,
                cols=len(GMD_SHEET_HEADERS),
                context="trim_columns",
            )
            logger.info(
                "Worksheet %r column width trimmed to %d canonical columns",
                label,
                len(GMD_SHEET_HEADERS),
            )

    @property
    def primary_worksheet(self) -> Any:
        """Backward-compatible primary worksheet handle."""
        if self._multi_area:
            first_area = get_area_worksheet_names()[0]
            return self._worksheets[first_area]
        return self._worksheets[self._legacy_worksheet_name]

    def _cache_valid(self) -> bool:
        return (
            self._cached_values is not None
            and (time.monotonic() - self._cache_timestamp) < self._cache_ttl_seconds
        )

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._cache_timestamp = 0.0
            self._cached_values = None

    def _worksheets_for_read(self) -> list[tuple[str, Any]]:
        pairs: list[tuple[str, Any]] = []
        if self._multi_area:
            for area_name in get_area_worksheet_names():
                worksheet = self._worksheets.get(area_name)
                if worksheet is not None:
                    pairs.append((area_name, worksheet))
            if include_legacy_readings_worksheet():
                legacy_key = f"__legacy__:{self._legacy_worksheet_name}"
                legacy_ws = self._worksheets.get(legacy_key)
                if legacy_ws is not None:
                    pairs.append((self._legacy_worksheet_name, legacy_ws))
            return pairs

        worksheet = self._worksheets.get(self._legacy_worksheet_name)
        if worksheet is not None:
            pairs.append((self._legacy_worksheet_name, worksheet))
        return pairs

    def get_all_values(self) -> list[list[str]]:
        with self._cache_lock:
            if self._cached_values is not None and self._cache_valid():
                return self._cached_values

            merged_rows: list[list[str]] = []
            sheet_id = get_spreadsheet_id()
            for label, worksheet in self._worksheets_for_read():
                try:
                    values = run_sheets_api(
                        label,
                        "worksheet.get_all_values",
                        lambda ws=worksheet: ws.get_all_values(),
                        spreadsheet_id=sheet_id,
                        context="merged_read",
                    )
                except Exception as exc:
                    log_api_call_failure(
                        label,
                        "worksheet.get_all_values",
                        exc,
                        spreadsheet_id=sheet_id,
                        context="merged_read",
                    )
                    logger.warning("Failed reading worksheet %r: %s", label, exc)
                    continue
                if not values or len(values) <= 1:
                    continue
                headers = values[0]
                for row in values[1:]:
                    if not row or not any(str(cell).strip() for cell in row):
                        continue
                    merged_rows.append((row, headers))

            if not merged_rows:
                self._cached_values = [list(GMD_SHEET_HEADERS)]
                self._cache_timestamp = time.monotonic()
                return self._cached_values

            from services.sheets_row_model import parse_reading_row

            parsed_rows: list[tuple[str, list[str]]] = []
            for row, headers in merged_rows:
                parsed = parse_reading_row(row, headers)
                timestamp = parsed.get("timestamp", "")
                canonical = build_reading_row(
                    ReadingRowRecord(**parsed),
                    GMD_SHEET_HEADERS,
                )
                parsed_rows.append((timestamp, canonical))

            parsed_rows.sort(
                key=lambda item: reading_timestamp_sort_key(item[0]),
                reverse=True,
            )
            result = [list(GMD_SHEET_HEADERS)] + [row for _, row in parsed_rows]
            self._cached_values = result
            self._cache_timestamp = time.monotonic()
            return result

    def append_reading_records(self, records: list[ReadingRowRecord]) -> int:
        if not records:
            logger.warning("Google Sheets append skipped — no records to write")
            return 0

        grouped: dict[str, list[ReadingRowRecord]] = defaultdict(list)
        for record in records:
            worksheet_name = resolve_area_worksheet(
                area_tank=record.area_tank,
                category=record.category,
                equipment=record.equipment,
            )
            grouped[worksheet_name].append(record)

        headers = list(GMD_SHEET_HEADERS)
        end_col = chr(ord("A") + len(headers) - 1)
        total_inserted = 0
        spreadsheet_id = get_spreadsheet_id()

        for worksheet_name, batch in grouped.items():
            worksheet = self._resolve_write_worksheet(worksheet_name)
            rows = [build_reading_row(record, headers) for record in batch]

            logger.info(
                "Google Sheets insert started spreadsheet_id=%s worksheet=%r row_count=%d "
                "insert_at=A2:%s%d sample_area=%r sample_equipment=%r",
                spreadsheet_id,
                worksheet_name,
                len(rows),
                end_col,
                1 + len(rows),
                batch[0].area_tank if batch else "",
                batch[0].equipment if batch else "",
            )

            run_sheets_api(
                worksheet_name,
                "worksheet.insert_rows",
                lambda: worksheet.insert_rows(
                    rows, row=2, value_input_option="USER_ENTERED"
                ),
                spreadsheet_id=spreadsheet_id,
                row=2,
                row_count=len(rows),
            )
            total_inserted += len(rows)

            logger.info(
                "Google Sheets insert completed spreadsheet_id=%s worksheet=%r rows_inserted=%d",
                spreadsheet_id,
                worksheet_name,
                len(rows),
            )

        self.clear_cache()
        return total_inserted

    def _resolve_write_worksheet(self, worksheet_name: str) -> Any:
        if not self._multi_area:
            return self._worksheets[self._legacy_worksheet_name]

        worksheet = self._worksheets.get(worksheet_name)
        if worksheet is not None:
            return worksheet

        worksheet = get_or_create_worksheet(self._spreadsheet, worksheet_name)
        ensure_gmd_header_row(worksheet)
        self._worksheets[worksheet_name] = worksheet
        logger.info("Created area worksheet on demand: %r", worksheet_name)
        return worksheet

    def layout_summary(self) -> dict[str, Any]:
        return {
            "multi_area_enabled": self._multi_area,
            "area_worksheets": list(get_area_worksheet_names()),
            "legacy_worksheet": self._legacy_worksheet_name,
            "include_legacy_on_read": include_legacy_readings_worksheet(),
            "worksheets_registered": [
                name for name in self._worksheets if not name.startswith("__legacy__:")
            ],
        }
