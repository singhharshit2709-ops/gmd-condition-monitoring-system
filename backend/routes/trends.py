from fastapi import APIRouter, Depends
from services.google_sheets_service import GMDGoogleSheetsService
from routes.dashboard import get_sheets_service

router = APIRouter(
    prefix="/trends",
    tags=["Trends & Analytics"]
)

@router.get("/readings")
def get_trend_readings(
    service: GMDGoogleSheetsService = Depends(get_sheets_service)
):
    rows = service.sheet.get_all_records()

    trend_data = []

    for row in rows:
        trend_data.append({
            "timestamp": row.get("Timestamp", ""),
            "parameter": row.get("Parameter", ""),
            "value": float(row.get("Value", 0)),
            "equipment": row.get("Equipment", "")
        })

    return trend_data 