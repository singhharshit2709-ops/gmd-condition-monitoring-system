"""Utility Area round sheet section builders — labels match the plant maintenance sheet."""

from __future__ import annotations

from typing import Callable


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


def _vibration_triplet(prefix: str, label_prefix: str, start_order: int = 1) -> list[dict]:
    axes = [
        ("vertical", "Vertical Vibration"),
        ("horizontal", "Horizontal Vibration"),
        ("axial", "Axial Vibration"),
    ]
    params = []
    for index, (axis, label) in enumerate(axes, start=start_order):
        params.append(
            _number_param(
                key=f"{prefix}_{axis}_vibration",
                short_label=label,
                full_label=f"{label_prefix} {label}",
                unit="mm/s",
                measurement_type="vibration_velocity",
                display_order=index,
            )
        )
    return params


def _section(section_id: str, label: str, groups: list[dict], display_order: int = 1) -> dict:
    return {
        "id": section_id,
        "label": label,
        "sheet_heading": label,
        "display_order": display_order,
        "active": True,
        "groups": groups,
    }


def _group(
    group_id: str,
    label: str,
    parameters: list[dict],
    *,
    display_order: int = 1,
    layout: str = "default",
) -> dict:
    return {
        "id": group_id,
        "label": label,
        "display_order": display_order,
        "collapsible": layout == "vibration_triplet",
        "default_expanded": True,
        "layout": layout,
        "active": True,
        "parameters": parameters,
    }


def build_screw_compressor_sections() -> list[dict]:
    """Compressor + Motor hierarchy matching the utility round sheet."""
    return [
        _section(
            "compressor",
            "Compressor",
            [
                _group(
                    "drive_end",
                    "Drive End",
                    _vibration_triplet("compressor_drive_end", "Compressor Drive End"),
                    layout="vibration_triplet",
                ),
                _group(
                    "non_drive_end",
                    "Non Drive End",
                    _vibration_triplet("compressor_non_drive_end", "Compressor Non Drive End"),
                    display_order=2,
                    layout="vibration_triplet",
                ),
                _group(
                    "de_temperature",
                    "DE Temperature",
                    [
                        _number_param(
                            key="compressor_de_temperature",
                            short_label="DE Temperature",
                            full_label="Compressor DE Temperature",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=1,
                            decimal_precision=1,
                            step=0.1,
                        )
                    ],
                    display_order=3,
                ),
                _group(
                    "nde_temperature",
                    "NDE Temperature",
                    [
                        _number_param(
                            key="compressor_nde_temperature",
                            short_label="NDE Temperature",
                            full_label="Compressor NDE Temperature",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=1,
                            decimal_precision=1,
                            step=0.1,
                        )
                    ],
                    display_order=4,
                ),
            ],
        ),
        _section(
            "motor",
            "Motor",
            [
                _group(
                    "drive_end",
                    "Drive End",
                    _vibration_triplet("motor_drive_end", "Motor Drive End"),
                    layout="vibration_triplet",
                ),
                _group(
                    "non_drive_end",
                    "Non Drive End",
                    _vibration_triplet("motor_non_drive_end", "Motor Non Drive End"),
                    display_order=2,
                    layout="vibration_triplet",
                ),
                _group(
                    "de_temperature",
                    "DE Temperature",
                    [
                        _number_param(
                            key="motor_de_temperature",
                            short_label="DE Temperature",
                            full_label="Motor DE Temperature",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=1,
                            decimal_precision=1,
                            step=0.1,
                        )
                    ],
                    display_order=3,
                ),
                _group(
                    "nde_temperature",
                    "NDE Temperature",
                    [
                        _number_param(
                            key="motor_nde_temperature",
                            short_label="NDE Temperature",
                            full_label="Motor NDE Temperature",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=1,
                            decimal_precision=1,
                            step=0.1,
                        )
                    ],
                    display_order=4,
                ),
                _group(
                    "current",
                    "Current",
                    [
                        _number_param(
                            key="current",
                            short_label="Current",
                            full_label="Current",
                            unit="A",
                            measurement_type="current",
                            display_order=1,
                            decimal_precision=2,
                            step=0.01,
                        )
                    ],
                    display_order=5,
                ),
            ],
            display_order=2,
        ),
    ]


def build_centrifugal_compressor_sections() -> list[dict]:
    return [
        _section(
            "centac",
            "Centac",
            [
                _group(
                    "drive_end",
                    "Drive End",
                    [
                        _number_param(
                            key="vertical_vibration",
                            short_label="Vertical Vibration",
                            full_label="Vertical Vibration",
                            unit="mm/s",
                            measurement_type="vibration_velocity",
                            display_order=1,
                        ),
                        _number_param(
                            key="horizontal_vibration",
                            short_label="Horizontal Vibration",
                            full_label="Horizontal Vibration",
                            unit="mm/s",
                            measurement_type="vibration_velocity",
                            display_order=2,
                        ),
                    ],
                ),
                _group(
                    "readings",
                    "Readings",
                    [
                        _number_param(
                            key="temperature",
                            short_label="Temperature",
                            full_label="Temperature",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=1,
                            decimal_precision=1,
                            step=0.1,
                        ),
                        _number_param(
                            key="current",
                            short_label="Current",
                            full_label="Current",
                            unit="A",
                            measurement_type="current",
                            display_order=2,
                        ),
                    ],
                    display_order=2,
                ),
            ],
        )
    ]


def build_air_dryer_sections() -> list[dict]:
    return [
        _section(
            "air_dryer",
            "Air Dryer",
            [
                _group(
                    "readings",
                    "Readings",
                    [
                        _number_param(
                            key="temperature",
                            short_label="Temperature",
                            full_label="Temperature",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=1,
                            decimal_precision=1,
                            step=0.1,
                        ),
                        _number_param(
                            key="pressure",
                            short_label="Pressure",
                            full_label="Pressure",
                            unit="bar",
                            measurement_type="pressure",
                            display_order=2,
                        ),
                    ],
                )
            ],
        )
    ]


def build_cooling_tower_pump_sections() -> list[dict]:
    return [
        _section(
            "cooling_tower_pump",
            "Cooling Tower Pump",
            [
                _group(
                    "drive_end",
                    "Drive End",
                    [
                        _number_param(
                            key="vertical_vibration",
                            short_label="Vertical Vibration",
                            full_label="Vertical Vibration",
                            unit="mm/s",
                            measurement_type="vibration_velocity",
                            display_order=1,
                        ),
                        _number_param(
                            key="horizontal_vibration",
                            short_label="Horizontal Vibration",
                            full_label="Horizontal Vibration",
                            unit="mm/s",
                            measurement_type="vibration_velocity",
                            display_order=2,
                        ),
                    ],
                ),
                _group(
                    "temperature",
                    "Temperature",
                    [
                        _number_param(
                            key="temperature",
                            short_label="Temperature",
                            full_label="Temperature",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=1,
                            decimal_precision=1,
                            step=0.1,
                        )
                    ],
                    display_order=2,
                ),
            ],
        )
    ]


def build_cooling_tower_sections() -> list[dict]:
    return [
        _section(
            "cooling_tower",
            "Cooling Tower",
            [
                _group(
                    "readings",
                    "Readings",
                    [
                        _number_param(
                            key="water_temperature",
                            short_label="Water Temperature",
                            full_label="Water Temperature",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=1,
                            decimal_precision=1,
                            step=0.1,
                        ),
                        _number_param(
                            key="tds",
                            short_label="TDS",
                            full_label="TDS",
                            unit="ppm",
                            measurement_type="tds",
                            display_order=2,
                            decimal_precision=0,
                            step=1,
                        ),
                        _number_param(
                            key="water_ph",
                            short_label="pH",
                            full_label="pH",
                            unit="pH",
                            measurement_type="ph",
                            display_order=3,
                            decimal_precision=2,
                            step=0.01,
                        ),
                    ],
                )
            ],
        )
    ]


def build_air_receiver_sections() -> list[dict]:
    return [
        _section(
            "air_receiver",
            "Air Receiver",
            [
                _group(
                    "readings",
                    "Readings",
                    [
                        _number_param(
                            key="pressure",
                            short_label="Pressure",
                            full_label="Pressure",
                            unit="bar",
                            measurement_type="pressure",
                            display_order=1,
                        ),
                        _number_param(
                            key="temperature",
                            short_label="Temperature",
                            full_label="Temperature",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=2,
                            decimal_precision=1,
                            step=0.1,
                        ),
                    ],
                )
            ],
        )
    ]


def build_dg_set_sections() -> list[dict]:
    return [
        _section(
            "dg_set",
            "DG Set",
            [
                _group(
                    "readings",
                    "Readings",
                    [
                        _number_param(
                            key="temperature",
                            short_label="Temperature",
                            full_label="Temperature",
                            unit="°C",
                            measurement_type="temperature",
                            display_order=1,
                            decimal_precision=1,
                            step=0.1,
                        ),
                        _number_param(
                            key="current",
                            short_label="Current",
                            full_label="Current",
                            unit="A",
                            measurement_type="current",
                            display_order=2,
                        ),
                        _number_param(
                            key="voltage",
                            short_label="Voltage",
                            full_label="Voltage",
                            unit="V",
                            measurement_type="voltage",
                            display_order=3,
                        ),
                    ],
                )
            ],
        )
    ]


UTILITY_SECTION_BUILDERS: dict[str, Callable[[], list]] = {
    "screw_compressor": build_screw_compressor_sections,
    "centrifugal_compressor": build_centrifugal_compressor_sections,
    "air_dryer": build_air_dryer_sections,
    "cooling_tower_pump": build_cooling_tower_pump_sections,
    "cooling_tower": build_cooling_tower_sections,
    "air_receiver": build_air_receiver_sections,
    "dg_set": build_dg_set_sections,
}

UTILITY_EQUIPMENT_TYPES: list[tuple[str, str, list[str]]] = [
    (
        "screw_compressor",
        "Screw Compressor",
        [
            "Pilot Air",
            "Comp-1",
            "Comp-2",
            "Comp-3",
            "Comp-4",
            "D.G Room",
            "Kaser-1",
            "Kaser-2",
        ],
    ),
    (
        "centrifugal_compressor",
        "Centrifugal Compressor",
        ["centac-1", "centac-2", "centac-3"],
    ),
    (
        "air_dryer",
        "Air Dryer",
        ["LP", "HP", "PILOT", "G-TANK"],
    ),
    (
        "cooling_tower_pump",
        "Cooling Tower Pump",
        ["LP", "HP", "BATCH", "K.E.PHE", "G.PHE", "G.Dry"],
    ),
    (
        "cooling_tower",
        "Cooling Tower",
        [
            "Cooling Tower-1",
            "Cooling Tower-2",
            "Cooling Tower-3",
            "G Tank Cooling Tower",
        ],
    ),
    (
        "air_receiver",
        "Air Receiver",
        [
            "Pilot Air Receiver",
            "Utility Area Receiver",
            "G-Tank Air Receiver",
        ],
    ),
    (
        "dg_set",
        "DG Set",
        ["All DG Set"],
    ),
]
