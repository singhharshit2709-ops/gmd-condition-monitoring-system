"""Shared V2 round sheet validation against gmd_machine_config_v2.json."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from gmd_config_v2 import (
    collect_equipment_parameters,
    find_equipment_in_config,
    get_expected_reading_count,
    load_gmd_config_v2,
)
from models.v2_preview_models import (
    InvalidParameterDetail,
    MissingParameterDetail,
    V2PreviewRequest,
    V2PreviewResponse,
)

logger = logging.getLogger("gmd_v2_validation")


@dataclass
class V2ValidationOutcome:
    preview: V2PreviewResponse
    category_name: str | None = None
    equipment_name: str | None = None
    normalized_readings: dict[str, float] | None = None
    parameter_locations: dict[str, str] | None = None
    parameter_units: dict[str, str] | None = None


def is_numeric_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False
        try:
            float(stripped)
            return True
        except ValueError:
            return False
    return False


def normalize_numeric_value(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return float(str(value).strip())


def validate_v2_submission(payload: V2PreviewRequest) -> V2ValidationOutcome:
    config = load_gmd_config_v2()
    located = find_equipment_in_config(
        equipment_name=payload.equipment,
        category_name=payload.category,
        config=config,
    )

    if located is None:
        located_any_category = find_equipment_in_config(
            equipment_name=payload.equipment,
            category_name=None,
            config=config,
        )
        if located_any_category is None:
            message = (
                f"Equipment '{payload.equipment}' was not found in gmd_machine_config_v2.json."
            )
        else:
            _, actual_category, _ = located_any_category
            message = (
                f"Equipment '{payload.equipment}' exists under category "
                f"'{actual_category.get('display_name')}', not '{payload.category}'."
            )
        return V2ValidationOutcome(
            preview=V2PreviewResponse(
                success=False,
                expected_readings=0,
                received_readings=0,
                missing_parameters=[],
                invalid_parameters=[],
                validation_message=message,
            )
        )

    _plant, category, equipment = located
    parameters = collect_equipment_parameters(equipment)
    allowed_by_key = {param["key"]: param for param in parameters}
    required_keys = {key for key, param in allowed_by_key.items() if param.get("required")}

    expected_readings = get_expected_reading_count(equipment, parameters)
    submitted = payload.readings or {}

    invalid_parameters: list[InvalidParameterDetail] = []
    missing_parameters: list[MissingParameterDetail] = []

    for key, value in submitted.items():
        if not isinstance(key, str) or not key.strip():
            invalid_parameters.append(
                InvalidParameterDetail(
                    key=str(key),
                    reason="Parameter key must be a non-empty string.",
                )
            )
            continue

        normalized_key = key.strip()
        if normalized_key not in allowed_by_key:
            invalid_parameters.append(
                InvalidParameterDetail(
                    key=normalized_key,
                    reason="Unexpected parameter key for this equipment.",
                )
            )
            continue

        if not is_numeric_value(value):
            invalid_parameters.append(
                InvalidParameterDetail(
                    key=normalized_key,
                    reason="Value must be numeric.",
                )
            )

    normalized_readings: dict[str, float] = {}
    for key in submitted:
        if not isinstance(key, str):
            continue
        normalized_key = key.strip()
        if normalized_key in allowed_by_key and is_numeric_value(submitted[key]):
            normalized_readings[normalized_key] = normalize_numeric_value(submitted[key])

    received_readings = len(normalized_readings)

    for key in sorted(required_keys):
        if key not in normalized_readings:
            param = allowed_by_key[key]
            missing_parameters.append(
                MissingParameterDetail(
                    key=key,
                    display_full_label=param.get("display_full_label", ""),
                )
            )

    success = (
        not missing_parameters
        and not invalid_parameters
        and received_readings >= len(required_keys)
    )

    if success:
        message = (
            f"Preview validation passed for {equipment.get('display_name')} "
            f"({received_readings}/{expected_readings} readings)."
        )
    elif missing_parameters and invalid_parameters:
        message = (
            f"Validation failed: {len(missing_parameters)} missing and "
            f"{len(invalid_parameters)} invalid parameter(s)."
        )
    elif missing_parameters:
        message = f"Validation failed: {len(missing_parameters)} required parameter(s) missing."
    elif invalid_parameters:
        message = f"Validation failed: {len(invalid_parameters)} invalid parameter(s)."
    else:
        message = "Validation failed."

    logger.info(
        "V2 validation equipment=%s success=%s received=%s expected=%s",
        equipment.get("display_name"),
        success,
        received_readings,
        expected_readings,
    )

    preview = V2PreviewResponse(
        success=success,
        expected_readings=expected_readings,
        received_readings=received_readings,
        missing_parameters=missing_parameters,
        invalid_parameters=invalid_parameters,
        validation_message=message,
    )

    if not success:
        return V2ValidationOutcome(preview=preview)

    parameter_locations = {
        key: allowed_by_key[key].get("display_full_label", "")
        for key in normalized_readings
    }
    parameter_units = {
        key: allowed_by_key[key].get("unit", "")
        for key in normalized_readings
    }

    return V2ValidationOutcome(
        preview=preview,
        category_name=category.get("display_name", payload.category),
        equipment_name=equipment.get("display_name", payload.equipment),
        normalized_readings=normalized_readings,
        parameter_locations=parameter_locations,
        parameter_units=parameter_units,
    )
