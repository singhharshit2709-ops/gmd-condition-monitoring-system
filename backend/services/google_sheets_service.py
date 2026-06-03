import os
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import gspread
from google.oauth2.service_account import Credentials

# Set up standard logging for the service
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

        spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE")

        if not spreadsheet_id:
            raise RuntimeError("GOOGLE_SPREADSHEET_ID not configured")

        if not credentials_file:
            raise RuntimeError("GOOGLE_CREDENTIALS_FILE not configured")

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        creds = Credentials.from_service_account_file(
            credentials_file,
            scopes=scopes,
        )

        client = gspread.authorize(creds)
        logger.info(f"Connecting to Spreadsheet ID: {spreadsheet_id}")

        spreadsheet = client.open_by_key(spreadsheet_id)
        logger.info("Spreadsheet opened successfully")
        logger.info(f"Spreadsheet title: {spreadsheet.title}")

        self.sheet = spreadsheet.worksheet("Sheet1")
        logger.info("Successfully targeted 'Sheet1'")

        self._cache_lock = threading.Lock()
        self._cache_ttl_seconds = int(os.getenv("GOOGLE_SHEETS_CACHE_TTL_SECONDS", "45"))
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
        entry_source: str = "Field"
    ) -> Dict[str, Any]:

        rows = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for parameter, value in readings.items():
            rows.append([
                timestamp,
                category,
                equipment,
                parameter,
                "",  # Intentional placeholder based on original business logic
                value,
                "NORMAL",
                verified_by,
                remarks,
                entry_source
            ])

        if rows:
            self.sheet.append_rows(
                rows,
                value_input_option="USER_ENTERED"
            )
            logger.info(f"Successfully appended {len(rows)} rows to Google Sheets.")

        return {
            "success": True,
            "rows_appended": len(rows)
        }