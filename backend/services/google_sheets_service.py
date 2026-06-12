import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

import gspread

from gmd_config import validate_gmd_submission
from services.sheets_config import (
    ReadingRowRecord,
    build_reading_row,
    ensure_gmd_header_row,
    get_cache_ttl_seconds,
    get_or_create_worksheet,
    get_spreadsheet_id,
    get_worksheet_name,
    is_sheets_enabled,
    load_service_account_credentials,
    normalize_readings_worksheet,
    open_spreadsheet,
    worksheet_has_horizontal_drift,
)
from services.sheets_row_model import GMD_SHEET_HEADERS

logger = logging.getLogger("gmd_monitoring")
logging.basicConfig(level=logging.INFO)


class GMDGoogleSheetsService:
    _singleton_lock = threading.Lock()
    _singleton_instance: Optional["GMDGoogleSheetsService"] = None

    def __new__(cls, *args, **kwargs):
        if cls._singleton_instance is None:
            with cls._singleton_lock:
                if cls._singleton_instance is None:
                    cls._singleton_instance = super().__new__(cls)
        return cls._singleton_instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        if not is_sheets_enabled():
            raise RuntimeError(
                "Google Sheets is disabled. Set GOOGLE_SHEETS_ENABLED=true."
            )

        spreadsheet_id = get_spreadsheet_id()
        if not spreadsheet_id:
            raise RuntimeError(
                "Spreadsheet ID not configured. Set GOOGLE_SHEET_ID."
            )

        creds, credential_source = load_service_account_credentials()
        worksheet_name = get_worksheet_name()

        client = gspread.authorize(creds)
        logger.info(
            "Connecting to spreadsheet id=%s worksheet=%r credentials=%s",
            spreadsheet_id,
            worksheet_name,
            credential_source,
        )

        spreadsheet = open_spreadsheet(client, spreadsheet_id)
        logger.info("Spreadsheet opened successfully: %s", spreadsheet.title)

        self.sheet = get_or_create_worksheet(spreadsheet, worksheet_name)
        ensure_gmd_header_row(self.sheet)

        existing_values = self.sheet.get_all_values()
        if worksheet_has_horizontal_drift(existing_values):
            stats = normalize_readings_worksheet(self.sheet)
            logger.warning(
                "Repaired horizontally drifted Readings worksheet: %s",
                stats,
            )
        elif self.sheet.col_count > len(GMD_SHEET_HEADERS):
            self.sheet.resize(cols=len(GMD_SHEET_HEADERS))
            logger.info(
                "GMD worksheet column width trimmed to %d canonical columns",
                len(GMD_SHEET_HEADERS),
            )

        logger.info("Successfully targeted worksheet %r", worksheet_name)

        self._cache_lock = threading.Lock()
        self._cache_ttl_seconds = get_cache_ttl_seconds()
        self._cached_sheet_timestamp = 0.0
        self._cached_sheet_values: Optional[List[List[str]]] = None
        self._cached_sheet_records: Optional[List[Dict[str, Any]]] = None
        self._initialized = True

    def _cache_valid(self) -> bool:
        return (
            self._cached_sheet_timestamp > 0
            and (time.monotonic() - self._cached_sheet_timestamp) < self._cache_ttl_seconds
        )

    def get_all_values(self) -> List[List[str]]:
        with self._cache_lock:
            if self._cached_sheet_values is not None and self._cache_valid():
                logger.debug("Using cached Google Sheets values")
                return self._cached_sheet_values

            values = self.sheet.get_all_values()
            self._cached_sheet_values = values
            self._cached_sheet_records = None
            self._cached_sheet_timestamp = time.monotonic()
            return values

    def get_all_records(self) -> List[Dict[str, Any]]:
        with self._cache_lock:
            if self._cached_sheet_records is not None and self._cache_valid():
                logger.debug("Using cached Google Sheets records")
                return self._cached_sheet_records

            records = self.sheet.get_all_records()
            self._cached_sheet_records = records
            self._cached_sheet_values = None
            self._cached_sheet_timestamp = time.monotonic()
            return records

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._cached_sheet_timestamp = 0.0
            self._cached_sheet_values = None
            self._cached_sheet_records = None

    def _append_reading_records(self, records: list[ReadingRowRecord]) -> int:
        if not records:
            logger.warning("Google Sheets append skipped — no records to write")
            return 0

        try:
            headers = list(GMD_SHEET_HEADERS)
            rows = [build_reading_row(record, headers) for record in records]
            spreadsheet_id = get_spreadsheet_id()
            worksheet_name = get_worksheet_name()
            end_col = chr(ord("A") + len(headers) - 1)

            logger.info(
                "Google Sheets insert started spreadsheet_id=%s worksheet=%r row_count=%d "
                "insert_at=A2:%s%d sample_area=%r sample_equipment=%r sample_parameter=%r "
                "sample_value=%r verified_by=%r timestamp=%r",
                spreadsheet_id,
                worksheet_name,
                len(rows),
                end_col,
                1 + len(rows),
                records[0].area_tank if records else "",
                records[0].equipment if records else "",
                records[0].parameter_key if records else "",
                records[0].value if records else "",
                records[0].verified_by if records else "",
                records[0].timestamp if records else "",
            )

            # Insert directly below the header so newest readings stay in column A
            # and appear at the top of the dashboard (avoids gspread table-range drift).
            self.sheet.insert_rows(rows, row=2, value_input_option="USER_ENTERED")
            self.clear_cache()

            logger.info(
                "Google Sheets insert completed spreadsheet_id=%s worksheet=%r rows_inserted=%d",
                spreadsheet_id,
                worksheet_name,
                len(rows),
            )
            return len(rows)
        except Exception as exc:
            logger.error(
                "Google Sheets append failed spreadsheet_id=%s worksheet=%r: %s",
                get_spreadsheet_id(),
                get_worksheet_name(),
                exc,
                exc_info=True,
            )
            raise RuntimeError(
                f"Failed to append {len(records)} row(s) to Google Sheets: {exc}"
            ) from exc

    def append_readings(
        self,
        category: str,
        equipment: str,
        readings: Dict[str, Any],
        verified_by: str,
        remarks: str = "",
        entry_source: str = "Field",
    ) -> Dict[str, Any]:
        validate_gmd_submission(
            category=category,
            equipment=equipment,
            readings=readings,
            verified_by=verified_by,
        )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        submission_id = str(uuid.uuid4())
        records: list[ReadingRowRecord] = []

        for parameter_key, value in readings.items():
            record = ReadingRowRecord(
                submission_id=submission_id,
                timestamp=timestamp,
                category=category,
                equipment=equipment,
                parameter_key=str(parameter_key),
                parameter_display_name=str(parameter_key),
                value=float(value),
                status="NORMAL",
                verified_by=verified_by,
                remarks=remarks,
                entry_source=entry_source,
            )
            logger.info("V1 reading row: %s", record.log_context())
            records.append(record)

        rows_appended = self._append_reading_records(records)
        if rows_appended:
            logger.info(
                "V1 sheet append result: rows_appended=%d submission_id=%s category=%r equipment=%r",
                rows_appended,
                submission_id,
                category,
                equipment,
            )

        return {
            "success": True,
            "rows_appended": rows_appended,
            "submission_id": submission_id,
        }

    def append_v2_readings(
        self,
        category: str,
        equipment: str,
        readings: Dict[str, float],
        parameter_locations: Dict[str, str],
        verified_by: str = "",
        remarks: str = "",
        entry_source: str = "Web",
        media_name: str = "",
        media_type: str = "",
        media_url: str = "",
        area_tank: str = "",
        tag_no: str = "",
        parameter_units: Dict[str, str] | None = None,
        submission_id: str = "",
    ) -> Dict[str, Any]:
        """Persist V2 round sheet readings using the canonical row model."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        units = parameter_units or {}
        resolved_submission_id = submission_id.strip() or str(uuid.uuid4())

        logger.info(
            "V2 sheet append batch: submission_id=%s timestamp=%s area_tank=%r "
            "category=%r equipment=%r tag_no=%r reading_count=%d "
            "media_name=%r media_type=%r media_url=%r",
            resolved_submission_id,
            timestamp,
            area_tank,
            category,
            equipment,
            tag_no,
            len(readings),
            media_name,
            media_type,
            media_url,
        )

        records: list[ReadingRowRecord] = []
        for parameter_key, value in readings.items():
            record = ReadingRowRecord(
                submission_id=resolved_submission_id,
                timestamp=timestamp,
                area_tank=area_tank,
                category=category,
                equipment=equipment,
                tag_no=tag_no,
                parameter_key=parameter_key,
                parameter_display_name=parameter_locations.get(parameter_key, ""),
                unit=units.get(parameter_key, ""),
                value=float(value),
                status="NORMAL",
                verified_by=verified_by,
                remarks=remarks,
                media_name=media_name,
                media_type=media_type,
                media_url=media_url,
                entry_source=entry_source,
            )
            logger.info("V2 reading row: %s", record.log_context())
            records.append(record)

        rows_appended = self._append_reading_records(records)
        logger.info(
            "V2 sheet append result: rows_appended=%d submission_id=%s area_tank=%r "
            "equipment=%r tag_no=%r timestamp=%s",
            rows_appended,
            resolved_submission_id,
            area_tank,
            equipment,
            tag_no,
            timestamp,
        )

        return {
            "success": True,
            "rows_appended": rows_appended,
            "timestamp": timestamp,
            "submission_id": resolved_submission_id,
        }
