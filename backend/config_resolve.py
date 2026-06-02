"""
Resolve plant / area (machine) / equipment (motor) names against machine_config.json.
Handles trimming, case-insensitive match, and common aliases.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from fastapi import HTTPException

# Common alternate labels → canonical config motor id
MOTOR_ALIASES: dict[str, str] = {
    "stardelta": "Star Delta",
    "star-delta": "Star Delta",
    "star_delta": "Star Delta",
    "star delta starter": "Star Delta",
    "drive motor": "Drive",
    "main drive": "Drive",
}

# Alternate area labels → canonical machine id
MACHINE_ALIASES: dict[str, str] = {
    "g1": "G1 Lehr",
    "g1 lehr": "G1 Lehr",
    "g2": "G2 Lehr",
    "g2 lehr": "G2 Lehr",
    "g3": "G3 Lehr",
    "g3 lehr": "G3 Lehr",
    "furnace cooling blower": "Furnace Cooling Blower",
    "furnace blower": "Furnace Cooling Blower",
    "mold cooling blower": "Mold Cooling Blower",
    "combustion blower": "Combustion Blower",
    "block air fan": "Block Air Fan",
    "injector blower": "Injector Blower",
    "electrode cooling blower": "Electrode Cooling Blower",
    "electrode water pump": "Electrode Water Pump",
}


def _normalize_key(value: str) -> str:
    """Collapse unicode spaces and punctuation for fuzzy matching."""
    text = unicodedata.normalize("NFKC", value or "")
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def _lookup_canonical(candidates: dict[str, str], raw: str) -> str | None:
    """Return canonical key from candidates map keyed by normalized form."""
    norm = _normalize_key(raw)
    if not norm:
        return None
    return candidates.get(norm)


def resolve_machine_id(
    config: dict[str, Any],
    plant_id: str,
    machine_id: str,
) -> str:
    plants = config.get("plants", {})
    if plant_id not in plants:
        raise HTTPException(status_code=404, detail=f"Plant not found: {plant_id!r}")
    machines = plants[plant_id].get("machines", {})
    raw = (machine_id or "").strip()
    if raw in machines:
        return raw

    by_norm = {_normalize_key(k): k for k in machines}
    canonical = _lookup_canonical(by_norm, raw)
    if canonical:
        return canonical

    alias_target = MACHINE_ALIASES.get(_normalize_key(raw))
    if alias_target and alias_target in machines:
        return alias_target

    available_areas = sorted(machines.keys())
    raise HTTPException(
        status_code=404,
        detail=(
            f"Area not found: {machine_id!r} (plant={plant_id!r}). "
            f"Configured areas: {available_areas}"
        ),
    )


def resolve_motor_name(
    config: dict[str, Any],
    plant_id: str,
    machine_id: str,
    motor_name: str,
) -> str:
    machine_id = resolve_machine_id(config, plant_id, machine_id)
    motors = config["plants"][plant_id]["machines"][machine_id].get("motors", {})
    raw = (motor_name or "").strip()
    if not raw:
        raise HTTPException(
            status_code=422,
            detail=f"Equipment name is required for area {machine_id!r}",
        )
    if raw in motors:
        return raw

    by_norm = {_normalize_key(k): k for k in motors}
    canonical = _lookup_canonical(by_norm, raw)
    if canonical:
        return canonical

    alias_target = MOTOR_ALIASES.get(_normalize_key(raw))
    if alias_target and alias_target in motors:
        return alias_target

    available_motors = sorted(motors.keys())
    raise HTTPException(
        status_code=404,
        detail=(
            f"Equipment not found: {motor_name!r} in area {machine_id!r}. "
            f"Configured equipment: {available_motors}"
        ),
    )


def get_motor_thresholds_resolved(
    config: dict[str, Any],
    plant_id: str,
    machine_id: str,
    motor_name: str,
) -> tuple[str, str, dict[str, float]]:
    """Return (canonical_machine_id, canonical_motor_name, thresholds)."""
    canonical_machine = resolve_machine_id(config, plant_id, machine_id)
    canonical_motor = resolve_motor_name(config, plant_id, canonical_machine, motor_name)
    thresholds = config["plants"][plant_id]["machines"][canonical_machine]["motors"][
        canonical_motor
    ]
    return canonical_machine, canonical_motor, thresholds
