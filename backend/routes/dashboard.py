import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any

# Import dependency components from your existing service architecture
from services.google_sheets_service import GMDGoogleSheetsService

# Configure logger for this route
logger = logging.getLogger("gmd_condition_monitoring.dashboard")

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

# Dependency provider function matching your architecture
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

def fetch_and_clean_data(service: GMDGoogleSheetsService) -> List[List[str]]:
    """
    Fetches raw values using the injected service, drops the header row,
    and filters out completely blank rows. Handles empty sheets gracefully.
    """
    try:
        raw_rows = service.sheet.get_all_values()
        
        # Check if sheet is empty or only contains headers
        if not raw_rows or len(raw_rows) <= 1:
            logger.warning("Google Sheet contains no data or only the header row.")
            return []
            
        # Skip the header row (index 0) and filter out rows that are entirely empty
        return [row for row in raw_rows[1:] if row and any(cell.strip() for cell in row)]
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


@router.get("/summary")
def get_summary(service: GMDGoogleSheetsService = Depends(get_sheets_service)):
    """
    Aggregates runtime severity configurations across all records.
    """
    logger.info("Computing metrics for dashboard summary.")
    rows = fetch_and_clean_data(service)
    
    summary = {
        "total": 0,
        "ok": 0,
        "warning": 0,
        "alarm": 0
    }
    
    for row in rows:
        summary["total"] += 1
        status = row[COL_STATUS].strip().upper() if len(row) > COL_STATUS else "NORMAL"
        
        if status == "NORMAL":
            summary["ok"] += 1
        elif status == "WARNING":
            summary["warning"] += 1
        elif status == "ALARM":
            summary["alarm"] += 1
        else:
            # Default fallback for unmapped statuses
            summary["ok"] += 1
            
    return summary


@router.get("/recent-readings")
def get_recent_readings(service: GMDGoogleSheetsService = Depends(get_sheets_service)):
    """
    Returns the 20 most recent entries sorted by timestamp descending.
    """
    logger.info("Retrieving recent logs.")
    rows = fetch_and_clean_data(service)
    parsed_rows = [parse_row(row) for row in rows]
    
    try:
        # Sort by timestamp string string-descending (works for ISO-8601 or standard datetime formats)
        parsed_rows.sort(key=lambda x: x["timestamp"], reverse=True)
    except Exception as e:
        logger.warning(f"Error performing string-based timestamp sorting: {str(e)}. Reversing raw data array as a fallback.")
        parsed_rows.reverse()
        
    return parsed_rows[:20]


@router.get("/active-alarms")
def get_active_alarms(service: GMDGoogleSheetsService = Depends(get_sheets_service)):
    """
    Filters all data for rows displaying active system anomalies (WARNING or ALARM).
    """
    logger.info("Retrieving active system alarms.")
    rows = fetch_and_clean_data(service)
    active_alarms = []
    
    for row in rows:
        parsed = parse_row(row)
        if parsed["status"] in ["WARNING", "ALARM"]:
            active_alarms.append(parsed)
            
    try:
        active_alarms.sort(key=lambda x: x["timestamp"], reverse=True)
    except Exception:
        pass
        
    return active_alarms


@router.get("/equipment-health")
def get_equipment_health(service: GMDGoogleSheetsService = Depends(get_sheets_service)):
    """
    Groups entries by specific equipment units and computes an operational asset health matrix.
    """
    logger.info("Calculating asset health statistics.")
    rows = fetch_and_clean_data(service)
    equipment_metrics = {}
    
    for row in rows:
        parsed = parse_row(row)
        equip = parsed["equipment"]
        status = parsed["status"]
        
        if not equip:
            continue  # Skip rows without an equipment identifier
            
        if equip not in equipment_metrics:
            equipment_metrics[equip] = {
                "equipment": equip,
                "total_readings": 0,
                "normal_count": 0,
                "warning_count": 0,
                "alarm_count": 0
            }
            
        metrics = equipment_metrics[equip]
        metrics["total_readings"] += 1
        
        if status == "NORMAL":
            metrics["normal_count"] += 1
        elif status == "WARNING":
            metrics["warning_count"] += 1
        elif status == "ALARM":
            metrics["alarm_count"] += 1
        else:
            metrics["normal_count"] += 1

    # Format the response map into a clean list and apply the mathematical health percentage
    health_report = []
    for equip, metrics in equipment_metrics.items():
        total = metrics["total_readings"]
        
        # Calculate performance metrics using the specified business formula: (normal_count / total_readings) * 100
        health_percentage = (metrics["normal_count"] / total * 100) if total > 0 else 0.0
        metrics["health_percentage"] = round(health_percentage, 2)
        
        health_report.append(metrics)
        
    return health_report