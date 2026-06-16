"""
Plant-local timestamps for GMD readings.

All reading timestamps are stored and interpreted as naive strings in the
configured plant timezone (default Asia/Kolkata / IST). Render and other UTC
hosts must not use datetime.now() without a timezone for operational logs.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger("gmd_condition_monitoring.datetime")

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_PLANT_TIMEZONE = "Asia/Kolkata"


def get_plant_timezone() -> ZoneInfo:
    name = os.environ.get("GMD_PLANT_TIMEZONE", DEFAULT_PLANT_TIMEZONE).strip()
    if not name:
        name = DEFAULT_PLANT_TIMEZONE
    return ZoneInfo(name)


def plant_now() -> datetime:
    """Current time in the plant timezone (timezone-aware)."""
    return datetime.now(get_plant_timezone())


def format_plant_timestamp(value: datetime | None = None) -> str:
    """Format an aware or naive datetime as the canonical sheet timestamp string."""
    dt = value or plant_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_plant_timezone())
    else:
        dt = dt.astimezone(get_plant_timezone())
    return dt.strftime(TIMESTAMP_FORMAT)


def log_submission_timestamp(context: str, *, dt: datetime | None = None) -> str:
    """
    Generate a plant-local submission timestamp and log raw value + timezone + string.

    Returns the formatted timestamp written to Google Sheets.
    """
    aware = dt or plant_now()
    if aware.tzinfo is None:
        aware = aware.replace(tzinfo=get_plant_timezone())
    else:
        aware = aware.astimezone(get_plant_timezone())

    formatted = aware.strftime(TIMESTAMP_FORMAT)
    tz_name = str(get_plant_timezone())
    logger.info(
        "%s timestamp: raw=%r timezone=%s formatted=%r",
        context,
        aware.isoformat(),
        tz_name,
        formatted,
    )
    return formatted


def parse_plant_timestamp(value: str) -> Optional[datetime]:
    """
    Parse a canonical reading timestamp string as plant-local time.

    Stored sheet values are naive YYYY-MM-DD HH:MM:SS in plant local time.
    Returns a timezone-aware datetime in the plant zone.
    """
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    formats = [
        TIMESTAMP_FORMAT,
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]

    tz = get_plant_timezone()
    for fmt in formats:
        try:
            naive = datetime.strptime(text, fmt)
            return naive.replace(tzinfo=tz)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(text.replace(" ", "T"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=tz)
        return parsed.astimezone(tz)
    except ValueError:
        return None


def plant_datetime_min() -> datetime:
    """Earliest sortable plant-local datetime (for aware comparisons)."""
    return datetime.min.replace(tzinfo=get_plant_timezone())


def reading_timestamp_sort_key(value: str) -> datetime:
    """
    Sort key for reading rows (newest-first when used with reverse=True).

    Unparseable timestamps map to plant_datetime_min() so they sort after valid rows.
    """
    return parse_plant_timestamp(value) or plant_datetime_min()


def parse_plant_date(value: str) -> datetime:
    """Parse YYYY-MM-DD as start-of-day in plant timezone."""
    naive = datetime.strptime(value.strip(), "%Y-%m-%d")
    return naive.replace(tzinfo=get_plant_timezone())
