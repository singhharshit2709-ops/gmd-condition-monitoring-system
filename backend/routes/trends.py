from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from routes.dashboard import get_sheets_service, parse_timestamp
from services.google_sheets_service import GMDGoogleSheetsService

router = APIRouter(
    prefix="/trends",
    tags=["Trends & Analytics"]
)


def parse_date_string(value: str) -> datetime:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format for '{value}'. Use YYYY-MM-DD."
        ) from exc


@router.get("/readings")
def get_trend_readings(
    service: GMDGoogleSheetsService = Depends(get_sheets_service),
    equipment: Optional[str] = Query(None),
    parameter: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    window: Optional[int] = Query(None, ge=1),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    trend_data: List[Dict[str, Any]] = []

    start_ts = parse_date_string(start_date) if start_date else None
    end_ts = parse_date_string(end_date) if end_date else None

    if end_ts is not None:
        end_ts = end_ts + timedelta(hours=23, minutes=59, seconds=59, microseconds=999999)

    if start_ts and end_ts and end_ts < start_ts:
        raise HTTPException(status_code=400, detail="end_date must be the same or later than start_date.")

    if start_ts is None and end_ts is None and window is not None:
        end_ts = datetime.now()
        start_ts = end_ts - timedelta(days=window)

    lower_equipment = equipment.strip().lower() if equipment else None
    lower_parameter = parameter.strip().lower() if parameter else None
    lower_category = category.strip().lower() if category else None

    rows = service.get_all_records()

    for row in rows:
        timestamp = row.get("Timestamp", "")
        parsed_timestamp = parse_timestamp(timestamp)

        if parsed_timestamp is None:
            continue

        if start_ts and parsed_timestamp < start_ts:
            continue
        if end_ts and parsed_timestamp > end_ts:
            continue

        equipment_value = (row.get("Equipment") or "").strip()
        parameter_value = (row.get("Parameter") or "").strip()
        category_value = (row.get("Category") or "").strip()

        if lower_equipment and equipment_value.lower() != lower_equipment:
            continue
        if lower_parameter and parameter_value.lower() != lower_parameter:
            continue
        if lower_category and category_value.lower() != lower_category:
            continue

        value_raw = row.get("Value", "")
        try:
            value = float(value_raw)
        except (TypeError, ValueError):
            continue

        trend_data.append({
            "timestamp": parsed_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "parameter": parameter_value,
            "equipment": equipment_value,
            "category": category_value,
            "value": value,
        })

    trend_data.sort(
        key=lambda item: parse_timestamp(item.get("timestamp", "")) or datetime.min
    )

    return trend_data 