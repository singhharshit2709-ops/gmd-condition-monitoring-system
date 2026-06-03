import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from gspread.exceptions import APIError

from services.google_sheets_service import GMDGoogleSheetsService

logger = logging.getLogger("gmd_condition_monitoring.dashboard")

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

# Dependency provider function matching your architecture
@lru_cache(maxsize=1)
def get_sheets_service() -> GMDGoogleSheetsService:
    return GMDGoogleSheetsService()

# Column Index Mapping (0-indexed matching columns A through J)
COL_TIMESTAMP = 0
COL_CATEGORY = 1
COL_EQUIPMENT = 2
COL_PARAMETER = 3
COL_LOCATION = 4
COL_VALUE = 5
COL_STATUS = 6
COL_VERIFIED_BY = 7
COL_REMARKS = 8
COL_ENTRY_SOURCE = 9

# Fixed configured equipment count for dashboard summary
TOTAL_EQUIPMENT = 25
CACHE_TTL_SECONDS = int(os.getenv("DASHBOARD_CACHE_TTL_SECONDS", "45"))
CACHE_TTL_SECONDS = max(30, min(CACHE_TTL_SECONDS, 60))

_dashboard_cache = {
    "summary": {"data": None, "expires_at": datetime.min},
    "active_alarms": {"data": None, "expires_at": datetime.min},
    "equipment_health": {"data": None, "expires_at": datetime.min},
}


def _cache_valid(key: str) -> bool:
    entry = _dashboard_cache[key]
    return entry["data"] is not None and datetime.now() < entry["expires_at"]


def _cache_store(key: str, payload: Any) -> None:
    _dashboard_cache[key]["data"] = payload
    _dashboard_cache[key]["expires_at"] = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)


def _cache_get(key: str) -> Any:
    return _dashboard_cache[key]["data"]


def _get_cached_dashboard_payload(key: str, loader, fallback):
    if _cache_valid(key):
        return _cache_get(key)

    try:
        payload = loader()
        _cache_store(key, payload)
        return payload
    except APIError as exc:
        logger.warning("Google Sheets APIError on %s: %s", key, exc)
        if _cache_get(key) is not None:
            return _cache_get(key)
        return fallback()
    except HTTPException:
        if _cache_get(key) is not None:
            return _cache_get(key)
        raise
    except Exception as exc:
        logger.error("Unexpected dashboard cache loader failure for %s: %s", key, exc, exc_info=True)
        if _cache_get(key) is not None:
            return _cache_get(key)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch dashboard data from Google Sheets."
        )


def parse_timestamp(value: str) -> Optional[datetime]:
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value.replace(" ", "T"))
    except Exception:
        return None


def format_last_updated(timestamp: Optional[datetime]) -> str:
    if not timestamp:
        return "Updated Unknown"

    now = datetime.now()
    delta = now - timestamp
    days = max(0, delta.days)

    if days == 0:
        return "Updated Today"
    if days == 1:
        return "Updated Yesterday"

    return f"Updated {days} Days Ago"


def fetch_and_clean_data(service: GMDGoogleSheetsService) -> List[List[str]]:
    """
    Fetches raw values using the injected service, drops the header row,
    and filters out completely blank rows. Handles empty sheets gracefully.
    """
    try:
        raw_rows = service.get_all_values()

        if not raw_rows or len(raw_rows) <= 1:
            logger.warning("Google Sheet contains no data or only the header row.")
            return []

        return [row for row in raw_rows[1:] if row and any(cell.strip() for cell in row)]
    except APIError as e:
        logger.warning("Google Sheets API error while reading dashboard sheet: %s", e)
        raise
    except Exception as e:
        logger.error(f"Error reading dataset via GMDGoogleSheetsService: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch telemetry data from the Google Sheets backend."
        )


def parse_row(row: List[str]) -> Dict[str, Any]:
    """
    Safely converts a raw row list into a structured dictionary.
    Includes guard checks against shortened arrays due to trailing blank columns.
    """
    return {
        "timestamp": row[COL_TIMESTAMP].strip() if len(row) > COL_TIMESTAMP else "",
        "category": row[COL_CATEGORY].strip() if len(row) > COL_CATEGORY else "",
        "equipment": row[COL_EQUIPMENT].strip() if len(row) > COL_EQUIPMENT else "",
        "parameter": row[COL_PARAMETER].strip() if len(row) > COL_PARAMETER else "",
        "location": row[COL_LOCATION].strip() if len(row) > COL_LOCATION else "",
        "value": row[COL_VALUE].strip() if len(row) > COL_VALUE else "",
        "status": row[COL_STATUS].strip().upper() if len(row) > COL_STATUS else "NORMAL",
        "verified_by": row[COL_VERIFIED_BY].strip() if len(row) > COL_VERIFIED_BY else "",
        "remarks": row[COL_REMARKS].strip() if len(row) > COL_REMARKS else "",
        "entry_source": row[COL_ENTRY_SOURCE].strip() if len(row) > COL_ENTRY_SOURCE else ""
    }


def get_latest_equipment_rows(rows: List[List[str]]) -> Dict[str, Dict[str, Any]]:
    latest_equipment: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        parsed = parse_row(row)
        equipment = parsed["equipment"]
        if not equipment:
            continue

        timestamp = parse_timestamp(parsed["timestamp"])
        existing = latest_equipment.get(equipment)

        if existing is None:
            latest_equipment[equipment] = {**parsed, "_parsed_timestamp": timestamp}
            continue

        existing_ts = existing.get("_parsed_timestamp")
        if timestamp is None:
            continue

        if existing_ts is None or timestamp > existing_ts:
            latest_equipment[equipment] = {**parsed, "_parsed_timestamp": timestamp}

    return latest_equipment


def _load_summary(service: GMDGoogleSheetsService) -> Dict[str, int]:
    logger.info("Computing metrics for dashboard summary.")
    rows = fetch_and_clean_data(service)
    latest_equipment = get_latest_equipment_rows(rows)

    warning = 0
    alarm = 0

    for record in latest_equipment.values():
        status = record.get("status", "NORMAL")
        if status == "WARNING":
            warning += 1
        elif status == "ALARM":
            alarm += 1

    ok = max(0, TOTAL_EQUIPMENT - warning - alarm)

    return {
        "total": TOTAL_EQUIPMENT,
        "ok": ok,
        "warning": warning,
        "alarm": alarm
    }


def _fallback_summary() -> Dict[str, int]:
    return {
        "total": TOTAL_EQUIPMENT,
        "ok": 0,
        "warning": 0,
        "alarm": 0,
    }


@router.get("/summary")
def get_summary(service: GMDGoogleSheetsService = Depends(get_sheets_service)):
    return _get_cached_dashboard_payload(
        "summary",
        lambda: _load_summary(service),
        _fallback_summary,
    )


@router.get("/recent-readings")
def get_recent_readings(
    limit: int = Query(100, ge=1, le=1000),
    service: GMDGoogleSheetsService = Depends(get_sheets_service)
):
    logger.info("Retrieving recent logs.")
    rows = fetch_and_clean_data(service)
    parsed_rows = [parse_row(row) for row in rows]

    parsed_rows.sort(
        key=lambda x: parse_timestamp(x.get("timestamp", "")) or datetime.min,
        reverse=True
    )

    return parsed_rows[:limit]


def _load_active_alarms(service: GMDGoogleSheetsService) -> List[Dict[str, Any]]:
    logger.info("Retrieving active system alarms.")
    rows = fetch_and_clean_data(service)
    latest_equipment = get_latest_equipment_rows(rows)

    active_alarms = [
        record
        for record in latest_equipment.values()
        if record.get("status") in ["WARNING", "ALARM"]
    ]

    active_alarms.sort(
        key=lambda x: x.get("_parsed_timestamp") or datetime.min,
        reverse=True
    )

    for record in active_alarms:
        record.pop("_parsed_timestamp", None)

    return active_alarms


def _fallback_active_alarms() -> List[Dict[str, Any]]:
    return []


@router.get("/active-alarms")
def get_active_alarms(service: GMDGoogleSheetsService = Depends(get_sheets_service)):
    return _get_cached_dashboard_payload(
        "active_alarms",
        lambda: _load_active_alarms(service),
        _fallback_active_alarms,
    )


def _load_equipment_health(service: GMDGoogleSheetsService) -> List[Dict[str, Any]]:
    logger.info("Calculating asset health statistics.")
    rows = fetch_and_clean_data(service)
    equipment_metrics: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        parsed = parse_row(row)
        equip = parsed["equipment"]
        if not equip:
            continue

        if equip not in equipment_metrics:
            equipment_metrics[equip] = {
                "equipment": equip,
                "category": parsed.get("category", ""),
                "location": parsed.get("location", ""),
                "total_readings": 0,
                "normal_count": 0,
                "warning_count": 0,
                "alarm_count": 0,
                "latest_status": parsed.get("status", "NORMAL"),
                "latest_parameter": parsed.get("parameter", ""),
                "latest_value": parsed.get("value", ""),
                "latest_verified_by": parsed.get("verified_by", ""),
                "latest_remarks": parsed.get("remarks", ""),
                "latest_timestamp": None,
            }

        metrics = equipment_metrics[equip]
        metrics["total_readings"] += 1

        status = parsed.get("status", "NORMAL")
        if status == "NORMAL":
            metrics["normal_count"] += 1
        elif status == "WARNING":
            metrics["warning_count"] += 1
        elif status == "ALARM":
            metrics["alarm_count"] += 1
        else:
            metrics["normal_count"] += 1

        timestamp = parse_timestamp(parsed.get("timestamp", ""))
        current_latest = metrics.get("latest_timestamp")

        if timestamp is not None and (current_latest is None or timestamp > current_latest):
            metrics.update(
                {
                    "latest_status": status,
                    "latest_parameter": parsed.get("parameter", ""),
                    "latest_value": parsed.get("value", ""),
                    "latest_verified_by": parsed.get("verified_by", ""),
                    "latest_remarks": parsed.get("remarks", ""),
                    "latest_timestamp": timestamp,
                }
            )

    health_report = []
    for metrics in equipment_metrics.values():
        latest_timestamp = metrics.get("latest_timestamp")
        metrics["last_reading_time"] = (
            latest_timestamp.strftime("%Y-%m-%d %H:%M:%S") if latest_timestamp else ""
        )
        metrics["latest_timestamp"] = (
            latest_timestamp.strftime("%Y-%m-%d %H:%M:%S") if latest_timestamp else ""
        )
        metrics["last_updated"] = format_last_updated(latest_timestamp)
        metrics["health_percentage"] = 100.0 if metrics.get("latest_status") == "NORMAL" else 0.0
        health_report.append(metrics)

    health_report.sort(key=lambda x: x.get("equipment", ""))
    return health_report


def _fallback_equipment_health() -> List[Dict[str, Any]]:
    return []


@router.get("/equipment-health")
def get_equipment_health(service: GMDGoogleSheetsService = Depends(get_sheets_service)):
    return _get_cached_dashboard_payload(
        "equipment_health",
        lambda: _load_equipment_health(service),
        _fallback_equipment_health,
    )
