import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import gspread

from gmd_config import validate_gmd_submission
from services.sheets_config import (
    ensure_gmd_header_row,
    get_cache_ttl_seconds,
    get_or_create_worksheet,
    get_spreadsheet_id,
    get_worksheet_name,
    is_sheets_enabled,
    load_service_account_credentials,
    open_spreadsheet,
)

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

        rows = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for parameter, value in readings.items():
            rows.append([
                timestamp,
                category,
                equipment,
                parameter,
                "",
                float(value),
                "NORMAL",
                verified_by,
                remarks,
                entry_source,
            ])

        if rows:
            self.sheet.append_rows(
                rows,
                value_input_option="USER_ENTERED",
            )
            self.clear_cache()
            logger.info("Successfully appended %d rows to Google Sheets.", len(rows))

        return {
            "success": True,
            "rows_appended": len(rows),
        }
