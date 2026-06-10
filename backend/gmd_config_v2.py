"""Load and query GMD machine configuration v2 (round sheet hierarchy)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

GMD_CONFIG_V2_PATH = Path(__file__).resolve().parent / "gmd_machine_config_v2.json"


@lru_cache(maxsize=1)
def load_gmd_config_v2(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else GMD_CONFIG_V2_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"GMD V2 config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sort_by_display_order(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: item.get("display_order", 0))


def collect_equipment_parameters(equipment: dict[str, Any]) -> list[dict[str, Any]]:
    """Return flat parameter definitions for an equipment entry (visible only)."""
    parameters: list[dict[str, Any]] = []

    for section in _sort_by_display_order(equipment.get("sections") or []):
        if section.get("active") is False:
            continue
        for group in _sort_by_display_order(section.get("groups") or []):
            if group.get("active") is False:
                continue
            for param in _sort_by_display_order(group.get("parameters") or []):
                if param.get("is_visible") is False:
                    continue
                parameters.append(
                    {
                        **param,
                        "section_label": section.get("label", ""),
                        "group_label": group.get("label", ""),
                    }
                )
    return parameters


def find_equipment_in_config(
    equipment_name: str,
    category_name: str | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    """
    Locate equipment by display_name (and optional category display_name).
    Returns (plant, category, equipment) or None.
    """
    cfg = config or load_gmd_config_v2()
    normalized_equipment = equipment_name.strip()
    normalized_category = category_name.strip() if category_name else None

    for plant in cfg.get("plants") or []:
        for category in plant.get("categories") or []:
            if normalized_category and category.get("display_name", "").strip() != normalized_category:
                continue
            for equipment in category.get("equipment") or []:
                if equipment.get("display_name", "").strip() != normalized_equipment:
                    continue
                if equipment.get("active") is False:
                    continue
                return plant, category, equipment
    return None


def get_expected_reading_count(equipment: dict[str, Any], parameters: list[dict[str, Any]]) -> int:
    if isinstance(equipment.get("expected_reading_count"), int):
        return equipment["expected_reading_count"]
    return sum(1 for param in parameters if param.get("required"))
