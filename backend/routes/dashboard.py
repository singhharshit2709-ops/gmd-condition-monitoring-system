import hashlib
import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Any, Optional, Set

from fastapi import APIRouter, HTTPException, Depends, Query
from gspread.exceptions import APIError

from gmd_config import get_total_equipment_count as get_v1_equipment_count
from gmd_config_v2 import get_total_equipment_count as get_v2_equipment_count
from services.gmd_datetime import parse_plant_date, parse_plant_timestamp, plant_now, plant_datetime_min
from services.google_sheets_service import GMDGoogleSheetsService
from services.sheets_config import GMD_SHEET_HEADERS_LEGACY, parse_reading_row, to_dashboard_api_row
from services.sheets_row_model import is_meaningful_reading_row

logger = logging.getLogger("gmd_condition_monitoring.dashboard")

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

# Dependency provider function matching your architecture
@lru_cache(maxsize=1)
def get_sheets_service() -> GMDGoogleSheetsService:
    return GMDGoogleSheetsService()

# Legacy column indices (10-column layout without Area / Tank)
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

STATUS_NORMAL = "NORMAL"
STATUS_WARNING = "WARNING"
STATUS_ALARM = "ALARM"

_STATUS_RANK = {
    STATUS_NORMAL: 0,
    STATUS_WARNING: 1,
    STATUS_ALARM: 2,
}

CACHE_TTL_SECONDS = int(os.getenv("DASHBOARD_CACHE_TTL_SECONDS", "45"))
CACHE_TTL_SECONDS = max(30, min(CACHE_TTL_SECONDS, 60))

_dashboard_cache = {
    "summary": {"data": None, "expires_at": datetime.min},
    "active_alarms": {"data": None, "expires_at": datetime.min},
    "equipment_health": {"data": None, "expires_at": datetime.min},
}

_acknowledged_alarm_ids: Set[str] = set()


def _cache_valid(key: str) -> bool:
    entry = _dashboard_cache[key]
    return entry["data"] is not None and datetime.now() < entry["expires_at"]


def _cache_store(key: str, payload: Any) -> None:
    _dashboard_cache[key]["data"] = payload
    _dashboard_cache[key]["expires_at"] = datetime.now() + timedelta(seconds=CACHE_TTL_SECONDS)


def _cache_invalidate(key: str) -> None:
    _dashboard_cache[key]["data"] = None
    _dashboard_cache[key]["expires_at"] = datetime.min


def invalidate_all_dashboard_cache() -> None:
    """Clear cached dashboard payloads after new readings are persisted."""
    for key in _dashboard_cache:
        _cache_invalidate(key)
    logger.info("Dashboard cache invalidated (all keys)")


def _configured_equipment_total() -> int:
    try:
        return get_v2_equipment_count()
    except Exception as exc:
        logger.warning("Failed to load V2 equipment count: %s", exc)
    try:
        return get_v1_equipment_count()
    except Exception as exc:
        logger.warning("Failed to load equipment count from gmd_machine_config.json: %s", exc)
        return 0


def _alarm_id(record: Dict[str, Any]) -> str:
    """Stable identifier for a specific alarm event (used by acknowledge flow)."""
    key = "|".join(
        [
            record.get("equipment", ""),
            record.get("parameter", ""),
            record.get("timestamp", ""),
            record.get("status", ""),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


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
    """Parse a reading timestamp as plant-local time (default Asia/Kolkata)."""
    return parse_plant_timestamp(value)


def format_last_updated(timestamp: Optional[datetime]) -> str:
    if not timestamp:
        return "Updated Unknown"

    if timestamp.tzinfo is None:
        timestamp = parse_plant_timestamp(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        if not timestamp:
            return "Updated Unknown"

    now = plant_now()
    delta = now - timestamp
    days = max(0, delta.days)

    if days == 0:
        return "Updated Today"
    if days == 1:
        return "Updated Yesterday"

    return f"Updated {days} Days Ago"


def fetch_and_clean_data(
    service: GMDGoogleSheetsService,
) -> tuple[list[str], list[list[str]]]:
    """
    Fetch raw values using the injected service, return (header_row, data_rows).
    Drops blank rows and handles empty sheets gracefully.
    """
    try:
        raw_rows = service.get_all_values()

        if not raw_rows or len(raw_rows) <= 1:
            logger.warning("Google Sheet contains no data or only the header row.")
            return list(GMD_SHEET_HEADERS_LEGACY), []

        headers = raw_rows[0]
        data_rows = [
            row
            for row in raw_rows[1:]
            if is_meaningful_reading_row(row, headers)
        ]
        return headers, data_rows
    except APIError as e:
        logger.warning("Google Sheets API error while reading dashboard sheet: %s", e)
        raise
    except Exception as e:
        logger.error(f"Error reading dataset via GMDGoogleSheetsService: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch telemetry data from the Google Sheets backend."
        )


def parse_row(row: List[str], headers: List[str] | None = None) -> Dict[str, Any]:
    """
    Convert a raw sheet row into the dashboard/reports API shape.
    Uses canonical parsing internally; preserves legacy response field names.
    """
    header_row = headers or GMD_SHEET_HEADERS_LEGACY
    parsed = parse_reading_row(row, header_row)
    api_row = to_dashboard_api_row(parsed)
    return {
        **api_row,
        "status": normalize_status(api_row["status"]),
    }


def normalize_status(status: Any) -> str:
    normalized = str(status or STATUS_NORMAL).strip().upper()
    if normalized in _STATUS_RANK:
        return normalized
    return STATUS_NORMAL


def worst_status(*statuses: str) -> str:
    if not statuses:
        return STATUS_NORMAL
    return max((normalize_status(status) for status in statuses), key=lambda s: _STATUS_RANK[s])


def get_latest_parameter_rows(
    rows: List[List[str]],
    headers: List[str] | None = None,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Return the newest sheet row for each (equipment, parameter) pair."""
    latest: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for row in rows:
        parsed = parse_row(row, headers)
        equipment = parsed["equipment"]
        parameter = parsed.get("parameter", "")
        if not equipment or not parameter:
            continue

        timestamp = parse_timestamp(parsed["timestamp"])
        record = {**parsed, "_parsed_timestamp": timestamp}
        equipment_rows = latest.setdefault(equipment, {})
        existing = equipment_rows.get(parameter)

        if existing is None:
            equipment_rows[parameter] = record
            continue

        existing_ts = existing.get("_parsed_timestamp")
        if timestamp is None:
            continue

        if existing_ts is None or timestamp > existing_ts:
            equipment_rows[parameter] = record

    return latest


def get_equipment_status_aggregates(
    rows: List[List[str]],
    headers: List[str] | None = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate equipment health using the worst status across all latest parameter readings.

    Severity order: ALARM > WARNING > NORMAL
    """
    latest_by_parameter = get_latest_parameter_rows(rows, headers)
    aggregates: Dict[str, Dict[str, Any]] = {}

    for equipment, parameter_rows in latest_by_parameter.items():
        statuses = [
            normalize_status(record.get("status", STATUS_NORMAL))
            for record in parameter_rows.values()
        ]
        overall_status = worst_status(*statuses)

        representative: Optional[Dict[str, Any]] = None
        representative_rank = -1
        representative_ts = plant_datetime_min()

        for record in parameter_rows.values():
            record_status = normalize_status(record.get("status", STATUS_NORMAL))
            record_rank = _STATUS_RANK[record_status]
            record_ts = record.get("_parsed_timestamp") or plant_datetime_min()

            if record_rank > representative_rank or (
                record_rank == representative_rank and record_ts > representative_ts
            ):
                representative = record
                representative_rank = record_rank
                representative_ts = record_ts

        latest_timestamp: Optional[datetime] = None
        for record in parameter_rows.values():
            record_ts = record.get("_parsed_timestamp")
            if record_ts is None:
                continue
            if latest_timestamp is None or record_ts > latest_timestamp:
                latest_timestamp = record_ts

        aggregates[equipment] = {
            "equipment": equipment,
            "category": representative.get("category", "") if representative else "",
            "worst_status": overall_status,
            "parameter_rows": parameter_rows,
            "representative": representative,
            "_parsed_timestamp": latest_timestamp,
        }

    return aggregates


def _load_summary(service: GMDGoogleSheetsService) -> Dict[str, int]:
    logger.info("Computing metrics for dashboard summary.")
    headers, rows = fetch_and_clean_data(service)
    equipment_aggregates = get_equipment_status_aggregates(rows, headers)
    total_equipment = _configured_equipment_total()

    warning = 0
    alarm = 0

    for aggregate in equipment_aggregates.values():
        status = aggregate.get("worst_status", STATUS_NORMAL)
        if status == STATUS_WARNING:
            warning += 1
        elif status == STATUS_ALARM:
            alarm += 1

    ok = max(0, total_equipment - warning - alarm)

    return {
        "total": total_equipment,
        "ok": ok,
        "warning": warning,
        "alarm": alarm
    }


def _fallback_summary() -> Dict[str, int]:
    total_equipment = _configured_equipment_total()
    return {
        "total": total_equipment,
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
    headers, rows = fetch_and_clean_data(service)
    parsed_rows = [parse_row(row, headers) for row in rows]

    parsed_rows.sort(
        key=lambda x: parse_timestamp(x.get("timestamp", "")) or plant_datetime_min(),
        reverse=True
    )

    return parsed_rows[:limit]


def _load_active_alarms(service: GMDGoogleSheetsService) -> List[Dict[str, Any]]:
    logger.info("Retrieving active system alarms.")
    headers, rows = fetch_and_clean_data(service)
    equipment_aggregates = get_equipment_status_aggregates(rows, headers)

    active_alarms = []
    for aggregate in equipment_aggregates.values():
        for record in aggregate["parameter_rows"].values():
            status = normalize_status(record.get("status", STATUS_NORMAL))
            if status not in {STATUS_WARNING, STATUS_ALARM}:
                continue

            alarm_record = {**record, "status": status}
            alarm_record["id"] = _alarm_id(alarm_record)
            if alarm_record["id"] in _acknowledged_alarm_ids:
                continue

            active_alarms.append(alarm_record)

    active_alarms.sort(
        key=lambda x: x.get("_parsed_timestamp") or plant_datetime_min(),
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


@router.post("/acknowledge-alarm/{alarm_id}")
def acknowledge_alarm(alarm_id: str):
    if not alarm_id or not alarm_id.strip():
        raise HTTPException(status_code=400, detail="Alarm id is required.")

    normalized_id = alarm_id.strip()
    _acknowledged_alarm_ids.add(normalized_id)
    _cache_invalidate("active_alarms")
    logger.info("Acknowledged dashboard alarm id=%s", normalized_id)
    return {"status": "ok", "id": normalized_id}


def _load_equipment_health(service: GMDGoogleSheetsService) -> List[Dict[str, Any]]:
    logger.info("Calculating asset health statistics.")
    headers, rows = fetch_and_clean_data(service)
    equipment_metrics: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        parsed = parse_row(row, headers)
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
                "latest_status": STATUS_NORMAL,
                "latest_parameter": "",
                "latest_value": "",
                "latest_verified_by": "",
                "latest_remarks": "",
                "latest_timestamp": None,
            }

        metrics = equipment_metrics[equip]
        metrics["total_readings"] += 1

        status = normalize_status(parsed.get("status", STATUS_NORMAL))
        if status == STATUS_NORMAL:
            metrics["normal_count"] += 1
        elif status == STATUS_WARNING:
            metrics["warning_count"] += 1
        elif status == STATUS_ALARM:
            metrics["alarm_count"] += 1
        else:
            metrics["normal_count"] += 1

    equipment_aggregates = get_equipment_status_aggregates(rows, headers)
    for equip, aggregate in equipment_aggregates.items():
        if equip not in equipment_metrics:
            continue

        metrics = equipment_metrics[equip]
        representative = aggregate.get("representative") or {}
        latest_timestamp = aggregate.get("_parsed_timestamp")

        metrics["latest_status"] = aggregate.get("worst_status", STATUS_NORMAL)
        metrics["latest_parameter"] = representative.get("parameter", "")
        metrics["latest_value"] = representative.get("value", "")
        metrics["latest_verified_by"] = representative.get("verified_by", "")
        metrics["latest_remarks"] = representative.get("remarks", "")
        metrics["latest_timestamp"] = latest_timestamp

    health_report = []
    for metrics in equipment_metrics.values():
        latest_timestamp = metrics.get("latest_timestamp")
        latest_status = normalize_status(metrics.get("latest_status", STATUS_NORMAL))
        metrics["last_reading_time"] = (
            latest_timestamp.strftime("%Y-%m-%d %H:%M:%S") if latest_timestamp else ""
        )
        metrics["latest_timestamp"] = (
            latest_timestamp.strftime("%Y-%m-%d %H:%M:%S") if latest_timestamp else ""
        )
        metrics["last_updated"] = format_last_updated(latest_timestamp)
        metrics["health_percentage"] = 100.0 if latest_status == STATUS_NORMAL else 0.0
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
