"""V2 preview validation — no persistence, no Sheets, no thresholds."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, status

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

logger = logging.getLogger("gmd_v2_preview")

router = APIRouter(prefix="/api/v2", tags=["GMD V2 Preview"])


def _is_numeric_value(value: Any) -> bool:
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


def _validate_readings_payload(
    payload: V2PreviewRequest,
) -> V2PreviewResponse:
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
        return V2PreviewResponse(
            success=False,
            expected_readings=0,
            received_readings=0,
            missing_parameters=[],
            invalid_parameters=[],
            validation_message=message,
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
                InvalidParameterDetail(key=str(key), reason="Parameter key must be a non-empty string.")
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

        if not _is_numeric_value(value):
            invalid_parameters.append(
                InvalidParameterDetail(
                    key=normalized_key,
                    reason="Value must be numeric.",
                )
            )

    submitted_allowed_keys = {
        key.strip()
        for key in submitted
        if isinstance(key, str)
        and key.strip() in allowed_by_key
        and _is_numeric_value(submitted[key])
    }
    received_readings = len(submitted_allowed_keys)

    for key in sorted(required_keys):
        if key not in submitted_allowed_keys:
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
        "V2 preview validation equipment=%s success=%s received=%s expected=%s",
        equipment.get("display_name"),
        success,
        received_readings,
        expected_readings,
    )

    return V2PreviewResponse(
        success=success,
        expected_readings=expected_readings,
        received_readings=received_readings,
        missing_parameters=missing_parameters,
        invalid_parameters=invalid_parameters,
        validation_message=message,
    )


@router.post(
    "/preview",
    response_model=V2PreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate a V2 round sheet submission without persisting data",
)
async def preview_v2_submission(payload: V2PreviewRequest) -> V2PreviewResponse:
    """
    Validate category, equipment, and parameter readings against gmd_machine_config_v2.json.
    Does not write to Google Sheets or trigger classification/alarms.
    """
    return _validate_readings_payload(payload)
