"""Load and validate GMD machine configuration from gmd_machine_config.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Set

GMD_CONFIG_PATH = Path(__file__).resolve().parent / "gmd_machine_config.json"


@lru_cache(maxsize=1)
def load_gmd_config(path: str | Path | None = None) -> Dict[str, Any]:
    config_path = Path(path) if path is not None else GMD_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"GMD config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_total_equipment_count(config: Dict[str, Any] | None = None) -> int:
    """Count all equipment entries across every category."""
    cfg = config or load_gmd_config()
    categories = cfg.get("categories", {})
    total = 0
    for category in categories.values():
        equipment = category.get("equipment", [])
        if isinstance(equipment, list):
            total += len(equipment)
    return total


def get_valid_categories(config: Dict[str, Any] | None = None) -> Set[str]:
    """Return display names for all configured categories."""
    cfg = config or load_gmd_config()
    names: Set[str] = set()
    for category in cfg.get("categories", {}).values():
        name = category.get("name")
        if isinstance(name, str) and name.strip():
            names.add(name.strip())
    return names


def get_equipment_for_category(
    category: str,
    config: Dict[str, Any] | None = None,
) -> List[str]:
    """Return equipment names configured for a category display name."""
    cfg = config or load_gmd_config()
    normalized = category.strip()
    for category_data in cfg.get("categories", {}).values():
        name = category_data.get("name", "")
        if isinstance(name, str) and name.strip() == normalized:
            equipment = category_data.get("equipment", [])
            if isinstance(equipment, list):
                return [str(item).strip() for item in equipment if str(item).strip()]
    return []


def validate_gmd_submission(
    category: str,
    equipment: str,
    readings: Dict[str, Any],
    verified_by: str,
) -> None:
    """
    Validate a GMD bulk submission against configuration and business rules.
    Raises ValueError with a user-facing message when validation fails.
    """
    if not isinstance(category, str) or not category.strip():
        raise ValueError("Category is required and cannot be empty.")

    if not isinstance(equipment, str) or not equipment.strip():
        raise ValueError("Equipment name is required and cannot be empty.")

    if not isinstance(verified_by, str) or not verified_by.strip():
        raise ValueError("Verified by is required and cannot be empty.")

    if not readings or not isinstance(readings, dict):
        raise ValueError("At least one reading is required.")

    valid_categories = get_valid_categories()
    normalized_category = category.strip()
    if normalized_category not in valid_categories:
        allowed = ", ".join(sorted(valid_categories))
        raise ValueError(
            f"Invalid category '{normalized_category}'. Allowed categories: {allowed}."
        )

    allowed_equipment = get_equipment_for_category(normalized_category)
    normalized_equipment = equipment.strip()
    if normalized_equipment not in allowed_equipment:
        raise ValueError(
            f"Invalid equipment '{normalized_equipment}' for category "
            f"'{normalized_category}'."
        )

    for parameter, value in readings.items():
        if not isinstance(parameter, str) or not parameter.strip():
            raise ValueError("Reading parameter names cannot be empty.")

        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"Reading for '{parameter}' cannot be empty.")

        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Reading for '{parameter}' must be numeric; received '{value}'."
            ) from exc

        if numeric_value < 0:
            raise ValueError(
                f"Reading for '{parameter}' cannot be negative; received {numeric_value}."
            )
