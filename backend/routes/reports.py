from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from routes.dashboard import (
    fetch_and_clean_data,
    parse_row,
    parse_timestamp,
    get_sheets_service,
)
from services.google_sheets_service import GMDGoogleSheetsService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
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
def get_report_readings(
    service: GMDGoogleSheetsService = Depends(get_sheets_service),
    category: Optional[str] = Query(None),
    equipment: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    rows = fetch_and_clean_data(service)
    parsed_rows = [parse_row(row) for row in rows]

    try:
        parsed_rows.sort(
            key=lambda x: parse_timestamp(x.get("timestamp", "")) or datetime.min,
            reverse=True,
        )
    except Exception:
        pass

    start_ts = parse_date_string(start_date) if start_date else None
    end_ts = parse_date_string(end_date) if end_date else None

    if end_ts is not None:
        end_ts = end_ts + timedelta(hours=23, minutes=59, seconds=59, microseconds=999999)

    if start_ts and end_ts and end_ts < start_ts:
        raise HTTPException(status_code=400, detail="end_date must be the same or later than start_date.")

    filtered_rows = []
    for row in parsed_rows:
        if category and row.get("category", "").strip().lower() != category.strip().lower():
            continue
        if equipment and row.get("equipment", "").strip().lower() != equipment.strip().lower():
            continue
        if status and row.get("status", "").strip().upper() != status.strip().upper():
            continue

        if start_ts or end_ts:
            timestamp = parse_timestamp(row.get("timestamp", ""))
            if not timestamp:
                continue
            if start_ts and timestamp < start_ts:
                continue
            if end_ts and timestamp > end_ts:
                continue

        filtered_rows.append(row)

    return filtered_rows 