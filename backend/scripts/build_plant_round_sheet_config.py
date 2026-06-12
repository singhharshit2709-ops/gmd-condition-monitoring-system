"""Build plant maintenance round sheet registry for gmd_machine_config_v2.json."""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path
from typing import Literal

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
CONFIG_PATH = ROOT / "gmd_machine_config_v2.json"

sys.path.insert(0, str(SCRIPTS_DIR))
from utility_round_sheet_sections import (  # noqa: E402
    UTILITY_EQUIPMENT_TYPES,
    UTILITY_SECTION_BUILDERS,
    build_cooling_tower_sections,
)

EquipmentProfile = Literal["blower", "electrode_cooling", "batch_charger"]

TANK_BLOWERS: dict[str, list[str]] = {
    "A Tank": [
        "MCB-1",
        "MCB-2",
        "MCB-3",
        "Gas Blower-1",
        "Gas Blower-2",
        "Chimney Blower-3",
        "Chimney Blower-4",
        "Tank Cooling Blower-7",
        "Tank Cooling Blower-8",
        "Cooling Blower-15",
        "Cooling Blower-16",
        "Throat Cool Blower-11",
        "Throat Cool Blower-12",
    ],
    "E Tank": [
        "Gas Blower-1",
        "Gas Blower-2",
        "Chimney Blower-3",
        "Chimney Blower-4",
        "MCB-5",
        "MCB-6",
        "Block Cooling Blower-7",
        "Block Cooling Blower-8",
        "Tank Cool Blower-11",
        "Tank Cool Blower-12",
        "Working End Blower-1",
        "Working End Blower-2",
    ],
    "K Tank": [
        "Gas Blower-1",
        "Gas Blower-2",
        "MCB-132 (132 kW)",
        "Chimney Blower-3",
        "Chimney Blower-4",
        "MCB-5",
        "MCB-6",
        "Block Cooling Blower-7",
        "Block Cooling Blower-8",
        "Throat Cool Blower-11",
        "Throat Cool Blower-12",
    ],
    "G Tank": [
        "MCB-1",
        "MCB-2",
        "MCB-3",
        "Gas Blower-1",
        "Gas Blower-2",
        "Chimney Blower (15 kW)-1",
        "Chimney Blower (15 kW)-2",
        "Chimney Blower (15 kW)-3",
        "Chimney Blower (7.5 kW)-1",
        "Chimney Blower (7.5 kW)-2",
        "Chimney Blower (7.5 kW)-3",
        "Block Cooling Blower-1",
        "Block Cooling Blower-2",
    ],
}

TANK_DM_WATER: dict[str, list[tuple[str, EquipmentProfile]]] = {
    "A Tank": [
        ("A Tank Electrode Cooling", "electrode_cooling"),
        ("A Tank Batch Charger", "batch_charger"),
    ],
    "E Tank": [
        ("E Tank Electrode Cooling", "electrode_cooling"),
    ],
    "G Tank": [
        ("G Tank Electrode Cooling", "electrode_cooling"),
    ],
    "K Tank": [
        ("K Tank Electrode Cooling", "electrode_cooling"),
        ("K & E Tank Batch Charger", "batch_charger"),
    ],
}

TANK_COOLING_TOWER_WATER: dict[str, list[str]] = {
    "A Tank": ["A Tank CT"],
    "G Tank": ["G Tank CT"],
}

UTILITY_COOLING_TOWER_WATER = ["Compressor House CT"]

CATEGORY_BY_PROFILE: dict[EquipmentProfile, tuple[str, str]] = {
    "blower": ("blowers", "Blowers"),
    "electrode_cooling": ("dm_water_electrode_cooling", "DM Water Electrode Cooling"),
    "batch_charger": ("dm_water_batch_charger", "DM Water Batch Charger"),
}


def slug_id(area: str, display_name: str) -> str:
    raw = f"{area}_{display_name}".lower()
    slug = re.sub(r"[^a-z0-9_]+", "_", raw)
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug or not slug[0].isalpha():
        slug = f"eq_{slug}"
    return slug[:64]


def _number_param(
    *,
    key: str,
    short_label: str,
    full_label: str,
    unit: str,
    measurement_type: str,
    display_order: int,
    decimal_precision: int = 2,
    step: float = 0.01,
) -> dict:
    return {
        "key": key,
        "display_short_label": short_label,
        "display_full_label": full_label,
        "measurement_type": measurement_type,
        "unit": unit,
        "display_order": display_order,
        "required": True,
        "is_visible": True,
        "editable": True,
        "source": "manual",
        "validation": {
            "value_type": "number",
            "min": 0,
            "decimal_precision": decimal_precision,
            "step": step,
            "allow_negative": False,
        },
        "thresholds": None,
        "decimal_precision": decimal_precision,
    }


def build_electrode_cooling_sections() -> list[dict]:
    return [
        {
            "id": "dm_water_electrode_cooling",
            "label": "DM Water Electrode Cooling",
            "sheet_heading": "DM Water Electrode Cooling",
            "display_order": 1,
            "description": "TDS, temperature, and pump pressure readings.",
            "active": True,
            "groups": [
                {
                    "id": "readings",
                    "label": "Readings",
                    "display_order": 1,
                    "collapsible": False,
                    "default_expanded": True,
                    "layout": "default",
                    "active": True,
                    "parameters": [
                        _number_param(
                            key="tds",
                            short_label="TDS (PPM)",
                            full_label="TDS (PPM)",
                            unit="PPM",
                            measurement_type="tds",
                            display_order=1,
                            decimal_precision=0,
                            step=1,
                        ),
                        _number_param(
                            key="dm_water_temperature",
                            short_label="DM Water Temperature (°C)",
                            full_label="DM Water Temperature (°C)",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=2,
                            decimal_precision=1,
                            step=0.1,
                        ),
                        _number_param(
                            key="pump_pressure",
                            short_label="Pump Pressure (KG/CM²)",
                            full_label="Pump Pressure (KG/CM²)",
                            unit="KG/CM²",
                            measurement_type="pressure",
                            display_order=3,
                            decimal_precision=2,
                            step=0.01,
                        ),
                    ],
                }
            ],
        }
    ]


def build_cooling_tower_water_monitoring_sections() -> list[dict]:
    """Water Parameters Cooling Tower sheet — same readings as utility cooling tower tags."""
    sections = build_cooling_tower_sections()
    if sections:
        sections[0]["label"] = "Cooling Tower Water Monitoring"
        sections[0]["sheet_heading"] = "Cooling Tower Water Monitoring"
        sections[0]["description"] = "Cooling tower water temperature, TDS, and pH readings."
    return sections


def build_batch_charger_sections() -> list[dict]:
    return [
        {
            "id": "batch_charger",
            "label": "Batch Charger",
            "sheet_heading": "Batch Charger",
            "display_order": 1,
            "description": "Cooling water temperature reading.",
            "active": True,
            "groups": [
                {
                    "id": "readings",
                    "label": "Readings",
                    "display_order": 1,
                    "collapsible": False,
                    "default_expanded": True,
                    "layout": "default",
                    "active": True,
                    "parameters": [
                        _number_param(
                            key="cooling_water_temperature",
                            short_label="Cooling Water Temperature (°C)",
                            full_label="Cooling Water Temperature (°C)",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=1,
                            decimal_precision=1,
                            step=0.1,
                        ),
                    ],
                }
            ],
        }
    ]


def sections_for_profile(profile: EquipmentProfile, blower_template: list) -> list:
    if profile == "blower":
        return copy.deepcopy(blower_template)
    if profile == "electrode_cooling":
        return build_electrode_cooling_sections()
    if profile == "batch_charger":
        return build_batch_charger_sections()
    raise ValueError(f"Unknown profile: {profile}")


def expected_reading_count(sections: list) -> int:
    count = 0
    for section in sections:
        if section.get("active") is False:
            continue
        for group in section.get("groups") or []:
            if group.get("active") is False:
                continue
            for param in group.get("parameters") or []:
                if param.get("is_visible") is False:
                    continue
                if param.get("required"):
                    count += 1
    return count


def build_equipment_registry(
    equipment_by_category: dict[str, list[dict]],
    areas: list[dict],
) -> dict:
    """Summarize equipment counts per tank/area and category for metadata."""
    by_area: dict[str, int] = {}
    by_category: dict[str, int] = {}
    area_categories: dict[str, dict[str, int]] = {}

    for category_id, entries in equipment_by_category.items():
        by_category[category_id] = len(entries)
        for entry in entries:
            area = str(entry.get("area") or "")
            by_area[area] = by_area.get(area, 0) + 1
            area_categories.setdefault(area, {})
            area_categories[area][category_id] = area_categories[area].get(category_id, 0) + 1

    total = sum(by_area.values())
    by_area_ordered = {area["display_name"]: by_area.get(area["display_name"], 0) for area in areas}

    return {
        "total_equipment": total,
        "by_area": by_area_ordered,
        "by_category": by_category,
        "area_category_breakdown": area_categories,
        "tank_equipment_manifest": {
            area: TANK_BLOWERS.get(area, [])
            + [name for name, _ in TANK_DM_WATER.get(area, [])]
            + TANK_COOLING_TOWER_WATER.get(area, [])
            for area in ["A Tank", "E Tank", "G Tank", "K Tank"]
        },
    }


def build_equipment_entry(
    *,
    equipment_id: str,
    display_name: str,
    area: str,
    display_order: int,
    category_id: str,
    sections: list,
    pilot: bool = False,
    version: str = "1.3.0",
    equipment_kind: str | None = None,
    tag_no: str | None = None,
) -> dict:
    reading_count = expected_reading_count(sections)
    entry = {
        "id": equipment_id,
        "display_name": display_name,
        "category_id": category_id,
        "area": area,
        "display_order": display_order,
        "description": f"{display_name} — {area} plant maintenance round sheet.",
        "aliases": [],
        "expected_reading_count": reading_count,
        "minimum_required_count": reading_count,
        "active": True,
        "pilot": pilot,
        "version": version,
        "metadata": {
            "notes": "Plant maintenance round sheet entry.",
            "data_sources": [f"Plant maintenance round sheet — {area}"],
        },
        "sections": sections,
    }
    if equipment_kind is not None:
        entry["equipment_kind"] = equipment_kind
    if tag_no is not None:
        entry["tag_no"] = tag_no
    return entry


def main() -> None:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    plant = config["plants"][0]
    all_categories = {category["id"]: category for category in plant["categories"]}
    blower_category = all_categories["blowers"]
    existing_mcb1 = next(
        item for item in blower_category["equipment"] if item["id"] == "mcb_1"
    )
    blower_template = existing_mcb1["sections"]

    equipment_by_category: dict[str, list[dict]] = {
        "blowers": [],
        "dm_water_electrode_cooling": [],
        "dm_water_batch_charger": [],
        "cooling_tower_water_monitoring": [],
        "utility_area_monitoring": [],
    }

    utility_area_name = "Utility Area"

    tank_order = ["A Tank", "E Tank", "G Tank", "K Tank"]

    for area in tank_order:
        order = 0
        for display_name in TANK_BLOWERS[area]:
            order += 1
            is_pilot = area == "A Tank" and display_name == "MCB-1"
            if is_pilot:
                entry = copy.deepcopy(existing_mcb1)
                entry["area"] = area
                entry["display_order"] = order
                entry["category_id"] = "blowers"
            else:
                sections = sections_for_profile("blower", blower_template)
                entry = build_equipment_entry(
                    equipment_id=slug_id(area, display_name),
                    display_name=display_name,
                    area=area,
                    display_order=order,
                    category_id="blowers",
                    sections=sections,
                )
            equipment_by_category["blowers"].append(entry)

        for display_name, profile in TANK_DM_WATER.get(area, []):
            order += 1
            category_id, _ = CATEGORY_BY_PROFILE[profile]
            sections = sections_for_profile(profile, blower_template)
            entry = build_equipment_entry(
                equipment_id=slug_id(area, display_name),
                display_name=display_name,
                area=area,
                display_order=order,
                category_id=category_id,
                sections=sections,
            )
            equipment_by_category[category_id].append(entry)

        for display_name in TANK_COOLING_TOWER_WATER.get(area, []):
            order += 1
            sections = build_cooling_tower_water_monitoring_sections()
            entry = build_equipment_entry(
                equipment_id=slug_id(area, display_name),
                display_name=display_name,
                area=area,
                display_order=order,
                category_id="cooling_tower_water_monitoring",
                sections=sections,
            )
            equipment_by_category["cooling_tower_water_monitoring"].append(entry)

    kind_order = 0
    for kind_id, kind_label, tags in UTILITY_EQUIPMENT_TYPES:
        kind_order += 1
        sections = UTILITY_SECTION_BUILDERS[kind_id]()
        for tag_order, tag_no in enumerate(tags, start=1):
            equipment_by_category["utility_area_monitoring"].append(
                build_equipment_entry(
                    equipment_id=slug_id(utility_area_name, f"{kind_label}_{tag_no}"),
                    display_name=tag_no,
                    area=utility_area_name,
                    display_order=kind_order * 100 + tag_order,
                    category_id="utility_area_monitoring",
                    sections=copy.deepcopy(sections),
                    equipment_kind=kind_label,
                    tag_no=tag_no,
                )
            )

    ct_sections = build_cooling_tower_water_monitoring_sections()
    for ct_order, display_name in enumerate(UTILITY_COOLING_TOWER_WATER, start=1):
        equipment_by_category["cooling_tower_water_monitoring"].append(
            build_equipment_entry(
                equipment_id=slug_id(utility_area_name, display_name),
                display_name=display_name,
                area=utility_area_name,
                display_order=ct_order,
                category_id="cooling_tower_water_monitoring",
                sections=copy.deepcopy(ct_sections),
                equipment_kind="Cooling Tower Water Monitoring",
                tag_no=display_name,
            )
        )

    plant["areas"] = [
        {
            "id": "a_tank",
            "display_name": "A Tank",
            "display_order": 1,
            "active": True,
            "navigation_mode": "tank_equipment",
        },
        {
            "id": "e_tank",
            "display_name": "E Tank",
            "display_order": 2,
            "active": True,
            "navigation_mode": "tank_equipment",
        },
        {
            "id": "g_tank",
            "display_name": "G Tank",
            "display_order": 3,
            "active": True,
            "navigation_mode": "tank_equipment",
        },
        {
            "id": "k_tank",
            "display_name": "K Tank",
            "display_order": 4,
            "active": True,
            "navigation_mode": "tank_equipment",
        },
        {
            "id": "utility_area",
            "display_name": utility_area_name,
            "display_order": 5,
            "active": True,
            "navigation_mode": "utility_tag",
        },
    ]

    registry = build_equipment_registry(equipment_by_category, plant["areas"])
    for area in plant["areas"]:
        count = registry["by_area"].get(area["display_name"], 0)
        area["metadata"] = {
            "custom": {
                "equipment_count": count,
                "category_breakdown": registry["area_category_breakdown"].get(
                    area["display_name"], {}
                ),
            }
        }

    plant["categories"] = [
        {
            "id": "blowers",
            "display_name": "Blowers",
            "display_order": 1,
            "description": "Rotating blower condition monitoring round sheets.",
            "active": True,
            "equipment": equipment_by_category["blowers"],
        },
        {
            "id": "dm_water_electrode_cooling",
            "display_name": "DM Water Electrode Cooling",
            "display_order": 2,
            "description": "DM water electrode cooling round sheet readings by tank.",
            "active": True,
            "equipment": equipment_by_category["dm_water_electrode_cooling"],
        },
        {
            "id": "dm_water_batch_charger",
            "display_name": "DM Water Batch Charger",
            "display_order": 3,
            "description": "Batch charger cooling water readings by tank.",
            "active": True,
            "equipment": equipment_by_category["dm_water_batch_charger"],
        },
        {
            "id": "cooling_tower_water_monitoring",
            "display_name": "Cooling Tower Water Monitoring",
            "display_order": 4,
            "description": "Cooling tower water quality readings by tank and compressor house.",
            "active": True,
            "equipment": equipment_by_category["cooling_tower_water_monitoring"],
        },
        {
            "id": "utility_area_monitoring",
            "display_name": "Utility Area Monitoring",
            "display_order": 5,
            "description": "Utility Area round sheet readings by equipment type and Tag No.",
            "active": True,
            "equipment": equipment_by_category["utility_area_monitoring"],
        },
    ]

    config["config_version"] = "1.5.0"
    config["metadata"]["description"] = (
        "V2 round sheet configuration for Neutral Glass GMD. "
        f"Full plant equipment registry: {registry['total_equipment']} instances across "
        "A/E/G/K tanks and Utility Area."
    )
    config["metadata"]["custom"] = {
        "equipment_registry": registry,
    }
    config["metadata"]["tags"] = [
        "v2",
        "plant-round-sheet",
        "blowers",
        "dm-water",
        "cooling-tower-water",
        "utility-area",
        f"{registry['total_equipment']}-equipment",
    ]
    changelog = config["metadata"].setdefault("changelog", [])
    if not any(item.get("version") == "1.5.0" for item in changelog):
        changelog.append(
            {
                "version": "1.5.0",
                "date": "2026-06-10",
                "author": "GMD Condition Monitoring V2",
                "summary": (
                    f"Published equipment registry totals ({registry['total_equipment']} instances) "
                    "with per-tank counts and category breakdown in metadata."
                ),
            }
        )
    plant["revision"]["revision_number"] = 7
    plant["revision"]["change_summary"] = (
        f"Equipment registry metadata: {registry['total_equipment']} total — "
        + ", ".join(
            f"{area}={count}"
            for area, count in registry["by_area"].items()
        )
    )

    total = registry["total_equipment"]
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(f"Wrote {total} equipment entries to {CONFIG_PATH}")
    print("Equipment by area:")
    for area, count in registry["by_area"].items():
        print(f"  {area}: {count}")


if __name__ == "__main__":
    main()
