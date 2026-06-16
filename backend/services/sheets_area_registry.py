"""
Area worksheet registry for multi-tab Google Sheets layout.

Each plant area (plus the virtual DM Water bucket) maps to a dedicated worksheet
with the same canonical 17-column header schema.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Iterable

from gmd_config_v2 import find_equipment_in_config, load_gmd_config_v2

DM_WATER_CATEGORIES = frozenset(
    {
        "DM Water Electrode Cooling",
        "DM Water Batch Charger",
    }
)

VIRTUAL_AREA_WORKSHEETS = ("DM Water Electrode Cooling",)


def is_multi_area_layout_enabled() -> bool:
    """Return True when readings are stored in per-area worksheets."""
    raw = os.environ.get("GOOGLE_SHEETS_AREA_LAYOUT", "multi").strip().lower()
    return raw not in {"legacy", "single", "false", "0", "off"}


def include_legacy_readings_worksheet() -> bool:
    """When True, merged reads also include the legacy Readings tab."""
    raw = os.environ.get(
        "GOOGLE_SHEETS_INCLUDE_LEGACY_READINGS", "true"
    ).strip().lower()
    return raw not in {"false", "0", "off", "no"}


@lru_cache(maxsize=1)
def get_area_worksheet_names() -> tuple[str, ...]:
    """
    Ordered worksheet names for the GMD spreadsheet.

    Physical plant areas come from config; DM Water Electrode Cooling is appended
    as a virtual aggregation bucket for DM categories.
    """
    cfg = load_gmd_config_v2()
    names: list[str] = []
    seen: set[str] = set()

    for plant in cfg.get("plants") or []:
        if plant.get("active") is False:
            continue
        for area in sorted(
            plant.get("areas") or [],
            key=lambda item: item.get("display_order", 0),
        ):
            if area.get("active") is False:
                continue
            display_name = str(area.get("display_name", "")).strip()
            if not display_name or display_name in seen:
                continue
            seen.add(display_name)
            names.append(display_name)

    for virtual_name in VIRTUAL_AREA_WORKSHEETS:
        if virtual_name not in seen:
            names.append(virtual_name)
            seen.add(virtual_name)

    return tuple(names)


def resolve_area_worksheet(
    *,
    area_tank: str = "",
    category: str = "",
    equipment: str = "",
) -> str:
    """
    Resolve the target worksheet for a reading batch.

    DM Water categories always route to the DM Water Electrode Cooling worksheet.
    Otherwise the physical area_tank is used when it matches a known worksheet.
    """
    normalized_category = str(category or "").strip()
    if normalized_category in DM_WATER_CATEGORIES:
        return "DM Water Electrode Cooling"

    normalized_area = str(area_tank or "").strip()
    if normalized_area in get_area_worksheet_names():
        return normalized_area

    if equipment:
        match = find_equipment_in_config(equipment, normalized_category or None)
        if match:
            _, _, equipment_entry = match
            equipment_area = str(equipment_entry.get("area") or "").strip()
            if equipment_area in get_area_worksheet_names():
                return equipment_area

    if normalized_area:
        return normalized_area

    area_names = get_area_worksheet_names()
    return area_names[0] if area_names else "Readings"


def iter_area_worksheets_for_read(
    *,
    include_legacy: bool | None = None,
) -> Iterable[str]:
    """Yield worksheet names to scan when aggregating dashboard data."""
    if is_multi_area_layout_enabled():
        yield from get_area_worksheet_names()
        if include_legacy is False:
            return
        if include_legacy is True or include_legacy_readings_worksheet():
            from services.sheets_config import get_worksheet_name

            legacy = get_worksheet_name()
            if legacy not in get_area_worksheet_names():
                yield legacy
        return

    from services.sheets_config import get_worksheet_name

    yield get_worksheet_name()
