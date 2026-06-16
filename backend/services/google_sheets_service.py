import logging
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

import gspread

from gmd_config import validate_gmd_submission
from services.sheets_config import (
    ReadingRowRecord,
    get_cache_ttl_seconds,
    get_spreadsheet_id,
    is_sheets_enabled,
    load_service_account_credentials,
    open_spreadsheet,
)
from services.sheets_data_access import SheetsDataAccess
from services.threshold_service import classify_v2_parameter_status

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

        client = gspread.authorize(creds)
        logger.info(
            "Connecting to spreadsheet id=%s credentials=%s",
            spreadsheet_id,
            credential_source,
        )

        spreadsheet = open_spreadsheet(client, spreadsheet_id)
        logger.info("Spreadsheet opened successfully: %s", spreadsheet.title)

        self._data_access = SheetsDataAccess(client, spreadsheet)
        self._data_access.set_cache_ttl(get_cache_ttl_seconds())
        self.sheet = self._data_access.primary_worksheet

        layout = self._data_access.layout_summary()
        logger.info(
            "Google Sheets data access initialized: multi_area=%s worksheets=%s",
            layout["multi_area_enabled"],
            layout["worksheets_registered"],
        )

        self._initialized = True

    def get_all_values(self) -> List[List[str]]:
        return self._data_access.get_all_values()

    def get_all_records(self) -> List[Dict[str, Any]]:
        values = self.get_all_values()
        if not values or len(values) <= 1:
            return []

        headers = values[0]
        records: List[Dict[str, Any]] = []
        for row in values[1:]:
            padded = row + [""] * (len(headers) - len(row))
            records.append(dict(zip(headers, padded)))
        return records

    def clear_cache(self) -> None:
        self._data_access.clear_cache()

    @classmethod
    def cache_clear(cls) -> None:
        if cls._singleton_instance is not None:
            cls._singleton_instance.clear_cache()

    def _append_reading_records(self, records: list[ReadingRowRecord]) -> int:
        try:
            return self._data_access.append_reading_records(records)
        except Exception as exc:
            logger.error(
                "Google Sheets append failed spreadsheet_id=%s: %s",
                get_spreadsheet_id(),
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
            status = classify_v2_parameter_status(
                value=float(value),
                equipment=equipment,
                category=category,
                parameter_key=str(parameter_key),
            )
            record = ReadingRowRecord(
                submission_id=submission_id,
                timestamp=timestamp,
                category=category,
                equipment=equipment,
                parameter_key=str(parameter_key),
                parameter_display_name=str(parameter_key),
                value=float(value),
                status=status,
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
            status = classify_v2_parameter_status(
                value=float(value),
                equipment=equipment,
                category=category,
                parameter_key=parameter_key,
            )
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
                status=status,
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
