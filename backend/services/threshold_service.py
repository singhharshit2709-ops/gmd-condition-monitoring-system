"""
Config-driven threshold classification for V2 parameter readings.

Threshold values live in gmd_machine_config_v2.json — nothing is hardcoded here.
Classification is opt-in via GMD_THRESHOLD_CLASSIFICATION_ENABLED until final
engineering limits are approved.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from gmd_config_v2 import collect_equipment_parameters, find_equipment_in_config

logger = logging.getLogger("gmd_condition_monitoring.thresholds")

STATUS_NORMAL = "NORMAL"
STATUS_WARNING = "WARNING"
STATUS_ALARM = "ALARM"


@dataclass(frozen=True)
class ParameterThresholds:
    enabled: bool
    provisional: bool
    normal_limit: float | None
    warning_limit: float | None
    alarm_limit: float | None
    classification_mode: str


def is_threshold_classification_enabled() -> bool:
    return (
        os.environ.get("GMD_THRESHOLD_CLASSIFICATION_ENABLED", "false")
        .strip()
        .lower()
        in {"true", "1", "yes", "on"}
    )


def allow_provisional_thresholds() -> bool:
    return (
        os.environ.get("GMD_THRESHOLD_ALLOW_PROVISIONAL", "false")
        .strip()
        .lower()
        in {"true", "1", "yes", "on"}
    )


def _coerce_limit(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _thresholds_from_param(param: dict[str, Any]) -> ParameterThresholds | None:
    thresholds = param.get("thresholds")
    if not isinstance(thresholds, dict):
        return None

    normal_limit = _coerce_limit(thresholds.get("normal_limit"))
    warning_limit = _coerce_limit(thresholds.get("warning_limit"))
    alarm_limit = _coerce_limit(thresholds.get("alarm_limit"))

    return ParameterThresholds(
        enabled=bool(thresholds.get("enabled", False)),
        provisional=bool(thresholds.get("provisional", False)),
        normal_limit=normal_limit,
        warning_limit=warning_limit,
        alarm_limit=alarm_limit,
        classification_mode=str(
            param.get("classification_mode") or "higher_is_worse"
        ).strip(),
    )


@lru_cache(maxsize=256)
def get_parameter_thresholds(
    equipment_name: str,
    category_name: str,
    parameter_key: str,
) -> ParameterThresholds | None:
    """Load threshold metadata for a parameter from V2 config."""
    match = find_equipment_in_config(equipment_name, category_name or None)
    if not match:
        return None

    _, _, equipment = match
    for param in collect_equipment_parameters(equipment):
        if str(param.get("key", "")).strip() != str(parameter_key).strip():
            continue
        return _thresholds_from_param(param)
    return None


def classify_parameter_value(
    value: float,
    thresholds: ParameterThresholds,
) -> str:
    """
    Classify a numeric reading against configured limits.

    higher_is_worse (default, matches legacy GT classify_value):
        value < normal_limit                 → NORMAL
        normal_limit ≤ value ≤ warning_limit → WARNING
        value > warning_limit                → ALARM

    lower_is_worse inverts the comparison direction.
    """
    mode = thresholds.classification_mode or "higher_is_worse"
    normal_limit = thresholds.normal_limit
    warning_limit = thresholds.warning_limit or thresholds.alarm_limit
    alarm_limit = thresholds.alarm_limit or thresholds.warning_limit

    if mode == "lower_is_worse":
        if normal_limit is not None and value > normal_limit:
            return STATUS_NORMAL
        if warning_limit is not None and value >= warning_limit:
            return STATUS_WARNING
        if alarm_limit is not None and value <= alarm_limit:
            return STATUS_ALARM
        if warning_limit is not None and value < warning_limit:
            return STATUS_ALARM
        return STATUS_NORMAL

    if normal_limit is not None and value < normal_limit:
        return STATUS_NORMAL
    if warning_limit is not None and value <= warning_limit:
        return STATUS_WARNING
    if alarm_limit is not None and value <= alarm_limit:
        return STATUS_WARNING
    return STATUS_ALARM


def classify_v2_parameter_status(
    *,
    value: float,
    equipment: str,
    category: str,
    parameter_key: str,
) -> str:
    """
    Resolve parameter status for V2 submissions.

    Returns NORMAL when classification is disabled, thresholds are missing,
    provisional limits are blocked, or limits are incomplete.
    """
    if not is_threshold_classification_enabled():
        return STATUS_NORMAL

    thresholds = get_parameter_thresholds(equipment, category, parameter_key)
    if thresholds is None or not thresholds.enabled:
        return STATUS_NORMAL

    if thresholds.provisional and not allow_provisional_thresholds():
        return STATUS_NORMAL

    has_limits = any(
        limit is not None
        for limit in (
            thresholds.normal_limit,
            thresholds.warning_limit,
            thresholds.alarm_limit,
        )
    )
    if not has_limits:
        return STATUS_NORMAL

    try:
        status = classify_parameter_value(float(value), thresholds)
        logger.debug(
            "Threshold classification equipment=%r parameter=%r value=%s status=%s",
            equipment,
            parameter_key,
            value,
            status,
        )
        return status
    except Exception as exc:
        logger.warning(
            "Threshold classification failed equipment=%r parameter=%r: %s",
            equipment,
            parameter_key,
            exc,
        )
        return STATUS_NORMAL
