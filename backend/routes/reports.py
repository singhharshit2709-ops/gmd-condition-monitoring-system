from fastapi import APIRouter, Depends

from routes.dashboard import (
    fetch_and_clean_data,
    parse_row,
    get_sheets_service
)

from services.google_sheets_service import GMDGoogleSheetsService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)

@router.get("/readings")
def get_report_readings(
    service: GMDGoogleSheetsService = Depends(get_sheets_service)
):
    rows = fetch_and_clean_data(service)
    parsed_rows = [parse_row(row) for row in rows]

    try:
        parsed_rows.sort(
            key=lambda x: x["timestamp"],
            reverse=True
        )
    except Exception:
        pass

    return parsed_rows 