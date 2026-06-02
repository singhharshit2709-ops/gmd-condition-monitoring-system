import os
import logging
from datetime import datetime
from typing import Dict, Any

import gspread
from google.oauth2.service_account import Credentials

# Set up standard logging for the service
logger = logging.getLogger("gmd_monitoring")
logging.basicConfig(level=logging.INFO)


class GMDGoogleSheetsService:
    def __init__(self):
        spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE")

        if not spreadsheet_id:
            raise RuntimeError("GOOGLE_SPREADSHEET_ID not configured")

        if not credentials_file:
            raise RuntimeError("GOOGLE_CREDENTIALS_FILE not configured")

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_file(
            credentials_file,
            scopes=scopes
        )

        client = gspread.authorize(creds)

        # Corrected Indentation & Scoping: All initialization now lives inside __init__
        logger.info(f"Connecting to Spreadsheet ID: {spreadsheet_id}")
        logger.info(f"Spreadsheet ID RAW = '{spreadsheet_id}'") 
        spreadsheet = client.open_by_key(spreadsheet_id)

        logger.info("Spreadsheet opened successfully")
        logger.info(f"Spreadsheet title: {spreadsheet.title}")

        # Debugging loop for worksheets
        for ws in spreadsheet.worksheets():
            logger.info(f"Available Worksheet: {ws.title}")

        # Target sheet correctly assigned to the instance
        self.sheet = spreadsheet.worksheet("Sheet1")
        logger.info("Successfully targeted 'Sheet1'")

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