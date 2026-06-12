"""
Engineering audit: Add Reading (gmd_machine_config_v2.json) vs plant round sheet workbook.

Compares implementation against:
  1) Excel workbook (--workbook path) when available
  2) Embedded engineering manifest in build_plant_round_sheet_config.py + utility_round_sheet_sections.py

Usage:
  cd backend
  python scripts/audit_add_reading_vs_workbook.py
  python scripts/audit_add_reading_vs_workbook.py --workbook "C:/path/to/plant_round_sheets.xlsx"
  python scripts/audit_add_reading_vs_workbook.py --markdown reports/add_reading_audit.md
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

BACKEND = Path(__file__).resolve().parents[1]
SCRIPTS = BACKEND / "scripts"
CONFIG_PATH = BACKEND / "gmd_machine_config_v2.json"

# Cooling Tower Water sheet (engineering workbook tab name variants)
COOLING_TOWER_WATER_SHEET_NAMES = {
    "water parameters cooling tower",
    "cooling tower water monitoring",
    "cooling tower water parameters",
    "water parameters - cooling tower",
}

COOLING_TOWER_WATER_EXPECTED = [
    {
        "sheet": "Water Parameters Cooling Tower",
        "category": "Cooling Tower Water Monitoring",
        "area": "Utility Area",
        "equipment": "Compressor House CT",
        "tag_no": "Compressor House CT",
        "equipment_kind": "Cooling Tower Water Monitoring",
        "parameters": [
            ("water_temperature", "Water Temperature", "°C"),
            ("tds", "TDS", "ppm"),
            ("water_ph", "pH", "pH"),
        ],
    },
    {
        "sheet": "Water Parameters Cooling Tower",
        "category": "Cooling Tower Water Monitoring",
        "area": "G Tank",
        "equipment": "G Tank CT",
        "tag_no": "",
        "parameters": [
            ("water_temperature", "Water Temperature", "°C"),
            ("tds", "TDS", "ppm"),
            ("water_ph", "pH", "pH"),
        ],
    },
    {
        "sheet": "Water Parameters Cooling Tower",
        "category": "Cooling Tower Water Monitoring",
        "area": "A Tank",
        "equipment": "A Tank CT",
        "tag_no": "",
        "parameters": [
            ("water_temperature", "Water Temperature", "°C"),
            ("tds", "TDS", "ppm"),
            ("water_ph", "pH", "pH"),
        ],
    },
]


@dataclass
class ParameterSpec:
    key: str
    label: str
    unit: str
    order: int
    section: str = ""
    group: str = ""


@dataclass
class EquipmentSpec:
    sheet: str
    category: str
    area: str
    equipment: str
    tag_no: str
    equipment_kind: str
    order: int
    parameters: list[ParameterSpec] = field(default_factory=list)


@dataclass
class Mismatch:
    category: str  # present | renamed | missing | param_mismatch
    sheet: str
    area: str
    equipment: str
    tag_no: str
    parameter: str
    expected: str
    current: str
    fix: str


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(module)
    return module


def _normalize_unit(unit: str) -> str:
    u = unit.strip().lower()
    u = u.replace("deg c", "°c").replace("deg c", "°c")
    u = u.replace("c", "°c") if u in {"c", "deg c"} else u
    mapping = {
        "ppm": "ppm",
        "p pm": "ppm",
        "ph": "ph",
        "mm/s": "mm/s",
        "a": "a",
        "v": "v",
        "bar": "bar",
        "kg/cm²": "kg/cm²",
        "kg/cm2": "kg/cm²",
        "°c": "°c",
        "c": "°c",
    }
    return mapping.get(u, u)


def _flatten_params(equipment: dict[str, Any]) -> list[ParameterSpec]:
    params: list[ParameterSpec] = []
    sections = sorted(equipment.get("sections") or [], key=lambda s: s.get("display_order", 0))
    for section in sections:
        if section.get("active") is False:
            continue
        groups = sorted(section.get("groups") or [], key=lambda g: g.get("display_order", 0))
        for group in groups:
            if group.get("active") is False:
                continue
            plist = sorted(group.get("parameters") or [], key=lambda p: p.get("display_order", 0))
            for param in plist:
                if param.get("is_visible") is False or param.get("active") is False:
                    continue
                params.append(
                    ParameterSpec(
                        key=str(param.get("key") or param.get("id") or ""),
                        label=str(
                            param.get("display_full_label")
                            or param.get("display_short_label")
                            or param.get("key")
                            or ""
                        ),
                        unit=str(param.get("unit") or ""),
                        order=len(params) + 1,
                        section=str(section.get("label") or ""),
                        group=str(group.get("label") or ""),
                    )
                )
    return params


def extract_implementation(config_path: Path) -> list[EquipmentSpec]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    rows: list[EquipmentSpec] = []
    sheet_by_category = {
        "Blowers": "Blowers",
        "DM Water Electrode Cooling": "DM Water Electrode Cooling",
        "DM Water Batch Charger": "DM Water Electrode Cooling",
        "Utility Area Monitoring": "Utility",
        "Cooling Tower Water Monitoring": "Water Parameters Cooling Tower",
    }

    for plant in data.get("plants") or []:
        for category in plant.get("categories") or []:
            cat_name = category.get("display_name", "")
            sheet = sheet_by_category.get(cat_name, cat_name)
            for equipment in category.get("equipment") or []:
                if equipment.get("active") is False:
                    continue
                rows.append(
                    EquipmentSpec(
                        sheet=sheet,
                        category=cat_name,
                        area=str(equipment.get("area") or ""),
                        equipment=str(equipment.get("display_name") or ""),
                        tag_no=str(equipment.get("tag_no") or ""),
                        equipment_kind=str(equipment.get("equipment_kind") or ""),
                        order=int(equipment.get("display_order") or 0),
                        parameters=_flatten_params(equipment),
                    )
                )
    return rows


def build_expected_from_manifest() -> list[EquipmentSpec]:
    build = _load_module("build_plant", SCRIPTS / "build_plant_round_sheet_config.py")
    utility = _load_module("utility_sections", SCRIPTS / "utility_round_sheet_sections.py")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    mcb1 = next(
        eq
        for cat in config["plants"][0]["categories"]
        if cat["id"] == "blowers"
        for eq in cat["equipment"]
        if eq["id"] == "mcb_1"
    )
    blower_params = _flatten_params(mcb1)

    expected: list[EquipmentSpec] = []
    tank_order = ["A Tank", "E Tank", "G Tank", "K Tank"]

    for area in tank_order:
        order = 0
        for name in build.TANK_BLOWERS[area]:
            order += 1
            expected.append(
                EquipmentSpec(
                    sheet="Blowers",
                    category="Blowers",
                    area=area,
                    equipment=name,
                    tag_no="",
                    equipment_kind="",
                    order=order,
                    parameters=list(blower_params),
                )
            )
        for name, profile in build.TANK_DM_WATER.get(area, []):
            order += 1
            if profile == "electrode_cooling":
                sections = build.build_electrode_cooling_sections()
                cat = "DM Water Electrode Cooling"
            else:
                sections = build.build_batch_charger_sections()
                cat = "DM Water Batch Charger"
            fake_eq = {"sections": sections}
            expected.append(
                EquipmentSpec(
                    sheet="DM Water Electrode Cooling",
                    category=cat,
                    area=area,
                    equipment=name,
                    tag_no="",
                    equipment_kind="",
                    order=order,
                    parameters=_flatten_params(fake_eq),
                )
            )

    kind_order = 0
    for kind_id, kind_label, tags in utility.UTILITY_EQUIPMENT_TYPES:
        kind_order += 1
        sections = utility.UTILITY_SECTION_BUILDERS[kind_id]()
        fake_eq = {"sections": sections}
        params = _flatten_params(fake_eq)
        for tag_order, tag in enumerate(tags, start=1):
            expected.append(
                EquipmentSpec(
                    sheet="Utility",
                    category="Utility Area Monitoring",
                    area="Utility Area",
                    equipment=tag,
                    tag_no=tag,
                    equipment_kind=kind_label,
                    order=kind_order * 100 + tag_order,
                    parameters=params,
                )
            )

    for row in COOLING_TOWER_WATER_EXPECTED:
        expected.append(
            EquipmentSpec(
                sheet=row["sheet"],
                category=row["category"],
                area=row["area"],
                equipment=row["equipment"],
                tag_no=row.get("tag_no", ""),
                equipment_kind=row.get("equipment_kind", ""),
                order=0,
                parameters=[
                    ParameterSpec(key=k, label=l, unit=u, order=i + 1)
                    for i, (k, l, u) in enumerate(row["parameters"])
                ],
            )
        )

    return expected


def _header_map(row: list[Any]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, cell in enumerate(row):
        key = re.sub(r"\s+", " ", str(cell or "").strip().lower())
        if key:
            mapping[key] = index
    return mapping


def _cell(row: list[Any], headers: dict[str, int], *names: str) -> str:
    for name in names:
        idx = headers.get(name.lower())
        if idx is not None and idx < len(row):
            value = str(row[idx]).strip()
            if value:
                return value
    return ""


def parse_excel_workbook(path: Path) -> list[EquipmentSpec]:
    try:
        import openpyxl
    except ImportError as exc:
        raise RuntimeError("openpyxl required: pip install openpyxl") from exc

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    rows: list[EquipmentSpec] = []

    alias_headers = {
        "area": ("area/tank", "area", "tank", "tank / area"),
        "category": ("category",),
        "equipment": ("equipment", "equipment name"),
        "tag_no": ("tag no", "tag no.", "tag", "tag_no"),
        "section": ("section",),
        "group": ("group",),
        "parameter": ("parameter", "parameter display name", "parameter_display_name"),
        "parameter_key": ("parameter key", "parameter_key", "key"),
        "unit": ("unit",),
        "order": ("order", "display order", "display_order", "parameter order"),
    }

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            continue
        headers = _header_map(list(all_rows[0]))
        if not headers:
            continue

        # Tabular layout: one row per parameter
        if any(h in headers for h in alias_headers["parameter_key"]) or any(
            h in headers for h in alias_headers["parameter"]
        ):
            grouped: dict[tuple[str, str, str, str, str], EquipmentSpec] = {}
            for raw in all_rows[1:]:
                row = list(raw)
                if not any(str(c).strip() for c in row):
                    continue
                area = _cell(row, headers, *alias_headers["area"]) or ""
                category = _cell(row, headers, *alias_headers["category"]) or sheet_name
                equipment = _cell(row, headers, *alias_headers["equipment"]) or ""
                tag_no = _cell(row, headers, *alias_headers["tag_no"]) or ""
                if not equipment and tag_no:
                    equipment = tag_no
                if not equipment:
                    continue
                key = (
                    sheet_name,
                    area,
                    category,
                    equipment,
                    tag_no,
                )
                if key not in grouped:
                    grouped[key] = EquipmentSpec(
                        sheet=sheet_name,
                        category=category,
                        area=area,
                        equipment=equipment,
                        tag_no=tag_no,
                        equipment_kind="",
                        order=len(grouped) + 1,
                        parameters=[],
                    )
                pkey = _cell(row, headers, *alias_headers["parameter_key"]) or _cell(
                    row, headers, *alias_headers["parameter"]
                )
                if not pkey:
                    continue
                label = _cell(row, headers, *alias_headers["parameter"]) or pkey
                unit = _cell(row, headers, *alias_headers["unit"]) or ""
                order_raw = _cell(row, headers, *alias_headers["order"])
                order = int(order_raw) if order_raw.isdigit() else len(grouped[key].parameters) + 1
                grouped[key].parameters.append(
                    ParameterSpec(
                        key=pkey,
                        label=label,
                        unit=unit,
                        order=order,
                        section=_cell(row, headers, *alias_headers["section"]),
                        group=_cell(row, headers, *alias_headers["group"]),
                    )
                )
            rows.extend(grouped.values())
            continue

        # Equipment list layout: Area | Equipment | Tag No (one row per equipment)
        if any(h in headers for h in alias_headers["equipment"]):
            order = 0
            for raw in all_rows[1:]:
                row = list(raw)
                if not any(str(c).strip() for c in row):
                    continue
                equipment = _cell(row, headers, *alias_headers["equipment"])
                if not equipment:
                    continue
                order += 1
                tag_no = _cell(row, headers, *alias_headers["tag_no"]) or ""
                rows.append(
                    EquipmentSpec(
                        sheet=sheet_name,
                        category=_cell(row, headers, *alias_headers["category"]) or sheet_name,
                        area=_cell(row, headers, *alias_headers["area"]) or "",
                        equipment=equipment,
                        tag_no=tag_no,
                        equipment_kind="",
                        order=order,
                        parameters=[],
                    )
                )

    wb.close()
    return rows


def _equipment_key(row: EquipmentSpec) -> tuple[str, str, str, str, str]:
    return (row.sheet, row.area, row.category, row.equipment, row.tag_no)


def _match_impl(
    expected: EquipmentSpec, impl_rows: list[EquipmentSpec]
) -> EquipmentSpec | None:
    candidates = []
    for impl in impl_rows:
        if expected.tag_no and impl.tag_no != expected.tag_no:
            continue
        if expected.area and impl.area != expected.area:
            continue
        if expected.equipment_kind and impl.equipment_kind != expected.equipment_kind:
            continue
        if expected.category and impl.category != expected.category:
            # Allow batch charger rows under DM sheet name
            if not (
                expected.sheet == "DM Water Electrode Cooling"
                and expected.category == "DM Water Batch Charger"
                and impl.category == "DM Water Batch Charger"
            ):
                if expected.category not in {impl.category, ""}:
                    continue
        if expected.equipment and impl.equipment != expected.equipment:
            if not (expected.tag_no and impl.equipment == expected.tag_no):
                continue
        candidates.append(impl)

    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        return None

    # Prefer exact equipment name match
    for impl in candidates:
        if impl.equipment == expected.equipment:
            return impl
    return candidates[0]


def compare(expected_rows: list[EquipmentSpec], impl_rows: list[EquipmentSpec]) -> list[Mismatch]:
    results: list[Mismatch] = []
    matched_impl: set[int] = set()

    for exp in expected_rows:
        impl = _match_impl(exp, impl_rows)
        if impl is None:
            results.append(
                Mismatch(
                    category="missing",
                    sheet=exp.sheet,
                    area=exp.area,
                    equipment=exp.equipment,
                    tag_no=exp.tag_no,
                    parameter="(equipment)",
                    expected=f"{exp.category} / order {exp.order}",
                    current="Not found in gmd_machine_config_v2.json",
                    fix=f"Add equipment '{exp.equipment}' under {exp.area} in category '{exp.category}'.",
                )
            )
            continue

        matched_impl.add(id(impl))

        # Equipment order within area+category
        same_area = [
            r
            for r in impl_rows
            if r.area == exp.area and r.category == impl.category and r.sheet == exp.sheet
        ]
        same_area_sorted = sorted(same_area, key=lambda r: r.order)
        exp_same = [r for r in expected_rows if r.area == exp.area and r.sheet == exp.sheet]
        exp_sorted = sorted(exp_same, key=lambda r: r.order)
        if exp.order and impl.order != exp.order:
            exp_pos = next((i + 1 for i, r in enumerate(exp_sorted) if r.equipment == exp.equipment), None)
            impl_pos = next(
                (i + 1 for i, r in enumerate(same_area_sorted) if r.equipment == impl.equipment), None
            )
            if exp_pos != impl_pos:
                results.append(
                    Mismatch(
                        category="param_mismatch",
                        sheet=exp.sheet,
                        area=exp.area,
                        equipment=exp.equipment,
                        tag_no=exp.tag_no,
                        parameter="(equipment order)",
                        expected=f"Position {exp_pos} in sheet order",
                        current=f"Position {impl_pos} (display_order={impl.order})",
                        fix="Set display_order to match engineering sheet sequence.",
                    )
                )

        if exp.equipment != impl.equipment:
            results.append(
                Mismatch(
                    category="renamed",
                    sheet=exp.sheet,
                    area=exp.area,
                    equipment=exp.equipment,
                    tag_no=exp.tag_no,
                    parameter="(equipment name)",
                    expected=exp.equipment,
                    current=impl.equipment,
                    fix="Rename display_name to match engineering sheet label exactly.",
                )
            )

        if exp.equipment_kind and impl.equipment_kind and exp.equipment_kind != impl.equipment_kind:
            results.append(
                Mismatch(
                    category="renamed",
                    sheet=exp.sheet,
                    area=exp.area,
                    equipment=exp.equipment,
                    tag_no=exp.tag_no,
                    parameter="(equipment kind)",
                    expected=exp.equipment_kind,
                    current=impl.equipment_kind,
                    fix="Set equipment_kind to match Utility sheet equipment type label.",
                )
            )

        if not exp.parameters:
            continue

        impl_params = impl.parameters
        exp_params = sorted(exp.parameters, key=lambda p: p.order)

        if len(exp_params) != len(impl_params):
            results.append(
                Mismatch(
                    category="param_mismatch",
                    sheet=exp.sheet,
                    area=exp.area,
                    equipment=exp.equipment,
                    tag_no=exp.tag_no,
                    parameter="(parameter count)",
                    expected=str(len(exp_params)),
                    current=str(len(impl_params)),
                    fix="Align parameter list length with engineering sheet.",
                )
            )

        for index, exp_p in enumerate(exp_params):
            if index >= len(impl_params):
                results.append(
                    Mismatch(
                        category="missing",
                        sheet=exp.sheet,
                        area=exp.area,
                        equipment=exp.equipment,
                        tag_no=exp.tag_no,
                        parameter=exp_p.key or exp_p.label,
                        expected=f"{exp_p.label} [{exp_p.unit}] order {exp_p.order}",
                        current="Missing",
                        fix=f"Add parameter '{exp_p.key}' with unit '{exp_p.unit}'.",
                    )
                )
                continue
            impl_p = impl_params[index]
            if exp_p.key != impl_p.key:
                results.append(
                    Mismatch(
                        category="param_mismatch",
                        sheet=exp.sheet,
                        area=exp.area,
                        equipment=exp.equipment,
                        tag_no=exp.tag_no,
                        parameter=exp_p.key,
                        expected=f"Position {index + 1}: {exp_p.key}",
                        current=f"Position {index + 1}: {impl_p.key}",
                        fix="Reorder parameters or rename keys to match sheet order.",
                    )
                )
            if _normalize_unit(exp_p.unit) != _normalize_unit(impl_p.unit):
                results.append(
                    Mismatch(
                        category="param_mismatch",
                        sheet=exp.sheet,
                        area=exp.area,
                        equipment=exp.equipment,
                        tag_no=exp.tag_no,
                        parameter=exp_p.key,
                        expected=f"Unit: {exp_p.unit}",
                        current=f"Unit: {impl_p.unit}",
                        fix=f"Set unit to '{exp_p.unit}' as on engineering sheet.",
                    )
                )

    # Extra implementation not in expected
    expected_keys = {_equipment_key(e) for e in expected_rows}
    for impl in impl_rows:
        key = _equipment_key(impl)
        if not any(
            e.area == impl.area
            and (e.equipment == impl.equipment or e.tag_no == impl.tag_no)
            and e.sheet in {impl.sheet, impl.category, "Utility", "Blowers"}
            for e in expected_rows
        ):
            # only flag if clearly extra within known sheets
            if impl.sheet in {"Utility", "Blowers", "DM Water Electrode Cooling"} or impl.category:
                results.append(
                    Mismatch(
                        category="renamed",
                        sheet=impl.sheet,
                        area=impl.area,
                        equipment=impl.equipment,
                        tag_no=impl.tag_no,
                        parameter="(extra in implementation)",
                        expected="Not on engineering manifest",
                        current=f"{impl.category} display_order={impl.order}",
                        fix="Verify with maintenance: remove if not on physical sheet, or add to workbook manifest.",
                    )
                )

    return results


def summarize_present(
    expected_rows: list[EquipmentSpec], impl_rows: list[EquipmentSpec], mismatches: list[Mismatch]
) -> list[str]:
    bad_keys = {
        (m.sheet, m.area, m.equipment, m.tag_no)
        for m in mismatches
        if m.category in {"missing", "param_mismatch", "renamed"}
    }
    lines: list[str] = []
    areas = sorted({r.area for r in expected_rows if r.area})
    lines.append(f"Areas/Tanks in manifest: {', '.join(areas)}")
    for sheet in sorted({r.sheet for r in expected_rows}):
        sheet_rows = [r for r in expected_rows if r.sheet == sheet]
        ok = [
            r
            for r in sheet_rows
            if (r.sheet, r.area, r.equipment, r.tag_no) not in bad_keys
            and _match_impl(r, impl_rows) is not None
        ]
        lines.append(f"Sheet '{sheet}': {len(ok)}/{len(sheet_rows)} equipment entries fully aligned")
    return lines


def render_report(
    *,
    expected_source: str,
    expected_rows: list[EquipmentSpec],
    impl_rows: list[EquipmentSpec],
    mismatches: list[Mismatch],
    workbook_path: str | None,
) -> str:
    sections = {
        "present": [m for m in mismatches if m.category == "present"],
        "renamed": [m for m in mismatches if m.category == "renamed"],
        "missing": [m for m in mismatches if m.category == "missing"],
        "param_mismatch": [m for m in mismatches if m.category == "param_mismatch"],
    }
    # present = expected minus issues
    issue_keys = {(m.sheet, m.area, m.equipment, m.tag_no, m.parameter) for m in mismatches}

    lines: list[str] = [
        "# Add Reading Engineering Audit Report",
        "",
        f"**Expected source:** {expected_source}",
        f"**Implementation:** `{CONFIG_PATH.name}`",
        f"**Excel workbook:** {workbook_path or 'Not provided — used embedded engineering manifest'}",
        "",
        "## Summary",
        "",
        f"- Expected equipment instances: **{len(expected_rows)}**",
        f"- Implemented equipment instances: **{len(impl_rows)}**",
        f"- Renamed/mapped issues: **{len(sections['renamed'])}**",
        f"- Missing completely: **{len(sections['missing'])}**",
        f"- Parameter/order/unit mismatches: **{len(sections['param_mismatch'])}**",
        "",
    ]
    for item in summarize_present(expected_rows, impl_rows, mismatches):
        lines.append(f"- {item}")

    def render_section(title: str, icon: str, items: list[Mismatch]) -> None:
        lines.extend(["", f"## {icon} {title}", ""])
        if not items:
            lines.append("_None._")
            return
        for m in items:
            lines.extend(
                [
                    f"### {m.sheet} → {m.area} → {m.equipment}"
                    + (f" (Tag: {m.tag_no})" if m.tag_no else ""),
                    "",
                    f"| Field | Value |",
                    f"|-------|-------|",
                    f"| Parameter | {m.parameter} |",
                    f"| Expected | {m.expected} |",
                    f"| Current | {m.current} |",
                    f"| **Recommended fix** | {m.fix} |",
                    "",
                ]
            )

    # Present section
    lines.extend(["", "## ✅ Present and correctly implemented", ""])
    present_count = 0
    for exp in expected_rows:
        key_base = (exp.sheet, exp.area, exp.equipment, exp.tag_no)
        if any(k[:4] == key_base for k in issue_keys):
            continue
        impl = _match_impl(exp, impl_rows)
        if impl is None:
            continue
        param_ok = len(exp.parameters) == len(impl.parameters) and all(
            ep.key == impl.parameters[i].key
            and _normalize_unit(ep.unit) == _normalize_unit(impl.parameters[i].unit)
            for i, ep in enumerate(sorted(exp.parameters, key=lambda p: p.order))
            if i < len(impl.parameters)
        )
        if not exp.parameters or param_ok:
            present_count += 1
            tag = f" (Tag: {exp.tag_no})" if exp.tag_no else ""
            lines.append(
                f"- **{exp.sheet}** / {exp.area} / {exp.equipment}{tag} — "
                f"{len(impl.parameters)} parameters, order OK"
            )
    if present_count == 0:
        lines.append("_No fully verified entries (see mismatches below)._")

    render_section("Renamed or mapped differently", "⚠", sections["renamed"])
    render_section("Missing completely", "❌", sections["missing"])
    render_section("Present but parameter mismatch", "🔄", sections["param_mismatch"])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, help="Path to source Excel workbook")
    parser.add_argument("--markdown", type=Path, help="Write markdown report to this path")
    args = parser.parse_args()

    impl_rows = extract_implementation(CONFIG_PATH)

    if args.workbook and args.workbook.exists():
        expected_rows = parse_excel_workbook(args.workbook)
        expected_source = str(args.workbook)
        if not expected_rows:
            print(f"WARNING: No rows parsed from {args.workbook}; falling back to manifest.")
            expected_rows = build_expected_from_manifest()
            expected_source += " (parse failed — using manifest fallback)"
    else:
        expected_rows = build_expected_from_manifest()
        expected_source = "build_plant_round_sheet_config.py + utility_round_sheet_sections.py + cooling tower manifest"

    mismatches = compare(expected_rows, impl_rows)
    report = render_report(
        expected_source=expected_source,
        expected_rows=expected_rows,
        impl_rows=impl_rows,
        mismatches=mismatches,
        workbook_path=str(args.workbook) if args.workbook else None,
    )

    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(report, encoding="utf-8")
        print(f"Report written to {args.markdown}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
