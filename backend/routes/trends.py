from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from routes.dashboard import fetch_and_clean_data, get_sheets_service, parse_row, parse_timestamp
from services.gmd_datetime import parse_plant_date, plant_datetime_min, plant_now
from services.google_sheets_service import GMDGoogleSheetsService

router = APIRouter(
    prefix="/trends",
    tags=["Trends & Analytics"]
)


def parse_date_string(value: str) -> datetime:
    try:
        return parse_plant_date(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format for '{value}'. Use YYYY-MM-DD."
        ) from exc


def _parse_numeric_value(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@router.get("/readings")
def get_trend_readings(
    service: GMDGoogleSheetsService = Depends(get_sheets_service),
    area_tank: Optional[str] = Query(None),
    equipment: Optional[str] = Query(None),
    tag_no: Optional[str] = Query(None),
    parameter: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    window: Optional[int] = Query(None, ge=1),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Historical numeric readings for trend charts (canonical Google Sheets schema)."""
    trend_data: List[Dict[str, Any]] = []

    start_ts = parse_date_string(start_date) if start_date else None
    end_ts = parse_date_string(end_date) if end_date else None

    if end_ts is not None:
        end_ts = end_ts + timedelta(hours=23, minutes=59, seconds=59, microseconds=999999)

    if start_ts and end_ts and end_ts < start_ts:
        raise HTTPException(status_code=400, detail="end_date must be the same or later than start_date.")

    if start_ts is None and end_ts is None and window is not None:
        end_ts = plant_now()
        start_ts = end_ts - timedelta(days=window)

    lower_area = area_tank.strip().lower() if area_tank else None
    lower_equipment = equipment.strip().lower() if equipment else None
    lower_tag = tag_no.strip().lower() if tag_no else None
    lower_parameter = parameter.strip().lower() if parameter else None
    lower_category = category.strip().lower() if category else None

    headers, rows = fetch_and_clean_data(service)

    for row in rows:
        parsed = parse_row(row, headers)
        parsed_timestamp = parse_timestamp(parsed.get("timestamp", ""))
        if parsed_timestamp is None:
            continue

        if start_ts and parsed_timestamp < start_ts:
            continue
        if end_ts and parsed_timestamp > end_ts:
            continue

        area_value = (parsed.get("area_tank") or "").strip()
        equipment_value = (parsed.get("equipment") or "").strip()
        tag_value = (parsed.get("tag_no") or "").strip()
        category_value = (parsed.get("category") or "").strip()
        parameter_key = (parsed.get("parameter") or parsed.get("parameter_key") or "").strip()
        parameter_display = (parsed.get("parameter_display_name") or parsed.get("location") or "").strip()

        if lower_area and area_value.lower() != lower_area:
            continue
        if lower_category and category_value.lower() != lower_category:
            continue
        if lower_equipment:
            equipment_match = equipment_value.lower() == lower_equipment
            tag_match = tag_value.lower() == lower_equipment
            if not equipment_match and not tag_match:
                continue
        if lower_tag and tag_value.lower() != lower_tag:
            continue
        if lower_parameter:
            param_match = parameter_key.lower() == lower_parameter
            display_match = parameter_display.lower() == lower_parameter
            if not param_match and not display_match:
                continue

        numeric_value = _parse_numeric_value(parsed.get("value"))
        if numeric_value is None:
            continue

        trend_data.append({
            "timestamp": parsed_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "parameter": parameter_key,
            "parameter_key": parameter_key,
            "parameter_display_name": parameter_display or parameter_key,
            "equipment": equipment_value,
            "category": category_value,
            "area_tank": area_value,
            "tag_no": tag_value,
            "unit": parsed.get("unit") or "",
            "value": numeric_value,
            "status": parsed.get("status") or "NORMAL",
            "verified_by": parsed.get("verified_by") or "",
        })

    trend_data.sort(
        key=lambda item: parse_timestamp(item.get("timestamp", "")) or plant_datetime_min(),
    )

    return trend_data
