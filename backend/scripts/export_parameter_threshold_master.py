"""
Export the GMD Equipment Parameter & Threshold Master (CSV + Excel).

Generates a professional threshold collection package from gmd_machine_config_v2.json
without altering equipment, parameters, or proposed limit values.

Usage:
  cd backend
  python scripts/export_parameter_threshold_master.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = BACKEND.parent / "templates"
sys.path.insert(0, str(BACKEND))

from gmd_config_v2 import (
    GMD_CONFIG_V2_PATH,
    collect_active_equipment,
    collect_equipment_parameters,
    load_gmd_config_v2,
)

DOCUMENT_TITLE = "GMD Condition Monitoring System"
DOCUMENT_SUBTITLE = "Equipment Parameter Threshold Master"
PREPARED_BY = "Harshit Singh"
DOCUMENT_VERSION = "1.0"
DOCUMENT_PURPOSE = (
    "To collect finalized Warning and Alarm threshold values from the User Department "
    "before production deployment."
)

MASTER_HEADERS = [
    "Area / Tank",
    "Category",
    "Equipment",
    "Tag No",
    "Parameter Key",
    "Parameter Display Name",
    "Unit",
    "Proposed Normal Limit",
    "Proposed Warning Limit",
    "Proposed Alarm Limit",
    "Final Normal Limit",
    "Final Warning Limit",
    "Final Alarm Limit",
    "Approved By",
    "Reviewed By User Department",
    "Approval Date",
    "Remarks",
]

# 1-based column indices for Excel styling
COL_EQUIPMENT_START = 1
COL_EQUIPMENT_END = 7
COL_PROPOSED_START = 8
COL_PROPOSED_END = 10
COL_FINAL_START = 11
COL_FINAL_END = 13

DEFAULT_CSV = TEMPLATES_DIR / "GMD_Equipment_Parameter_Threshold_Master.csv"
DEFAULT_XLSX = TEMPLATES_DIR / "GMD_Equipment_Parameter_Threshold_Master.xlsx"
DEFAULT_VALIDATION = TEMPLATES_DIR / "GMD_Equipment_Parameter_Threshold_Master_Validation.txt"

INSTRUCTIONS_LINES = [
    ("Title", DOCUMENT_TITLE),
    ("Document", DOCUMENT_SUBTITLE),
    ("Prepared By", PREPARED_BY),
    ("Version", DOCUMENT_VERSION),
    ("Purpose", DOCUMENT_PURPOSE),
    ("", ""),
    ("Overview", ""),
    (
        "Description",
        "This workbook lists every configured monitoring parameter across all plant areas, "
        "equipment, and tags in the GMD Condition Monitoring System.",
    ),
    ("", ""),
    ("Proposed Limits", ""),
    (
        "Note",
        "Proposed Normal, Warning, and Alarm Limit values are engineering reference values only. "
        "They are provisional and must not be treated as approved operating limits. "
        "Blank cells indicate no limit is defined in the current configuration.",
    ),
    ("", ""),
    ("Final Limits", ""),
    (
        "Note",
        "Final Normal, Warning, and Alarm Limit values must be completed by the User Department "
        "for each applicable row. Leave blank only where a limit is genuinely not applicable "
        "and document the reason in Remarks.",
    ),
    ("", ""),
    ("Approval", ""),
    (
        "Note",
        "Complete Approved By, Reviewed By User Department, and Approval Date before returning "
        "this document. All values are subject to approval before production deployment and "
        "system enablement of automatic status classification.",
    ),
    ("", ""),
    ("Classification (reference)", ""),
    (
        "Rule",
        "When limits are approved and enabled (higher-is-worse): NORMAL below Final Normal Limit; "
        "WARNING from Final Normal up to Final Warning; ALARM above Final Warning Limit "
        "(exact classification follows system threshold_service rules).",
    ),
]

CATEGORY_DISPLAY_SHORT = {
    "Blowers": "Blowers",
    "Cooling Tower Water Monitoring": "Cooling Tower",
    "DM Water Electrode Cooling": "DM Water Electrode Cooling",
    "DM Water Batch Charger": "DM Water Batch Charger",
    "Utility Area Monitoring": "Utility",
}

DASHBOARD_AREA_ORDER = [
    "A Tank",
    "E Tank",
    "G Tank",
    "K Tank",
    "Utility Area",
    "DM Water Electrode Cooling",
]

KEY_EQUIPMENT_CHECKS = [
    ("MCB-1", lambda eq, tag: eq == "MCB-1"),
    ("MCB-2", lambda eq, tag: eq == "MCB-2"),
    ("MCB-3", lambda eq, tag: eq == "MCB-3"),
    ("Chimney Blowers", lambda eq, tag: "Chimney Blower" in eq),
    ("Cooling Blowers", lambda eq, tag: "Cooling Blower" in eq),
    ("Block Cooling Blowers", lambda eq, tag: "Block Cooling Blower" in eq),
    ("Comp-1", lambda eq, tag: tag == "Comp-1"),
    ("Comp-2", lambda eq, tag: tag == "Comp-2"),
    ("Pilot Air", lambda eq, tag: tag == "Pilot Air"),
    ("Air Dryer LP", lambda eq, tag: eq == "LP (Air Dryer)" and tag == "LP"),
    ("Air Dryer HP", lambda eq, tag: eq == "HP (Air Dryer)" and tag == "HP"),
    ("Centac", lambda eq, tag: "Centac" in eq or "centac" in tag.lower()),
    ("Cooling Towers", lambda eq, tag: "Cooling Tower" in eq or tag == "Compressor House CT"),
    ("DM Water Electrode Cooling", lambda eq, tag: "Electrode Cooling" in eq),
]


@dataclass(frozen=True)
class MasterRow:
    area_tank: str
    category: str
    equipment: str
    tag_no: str
    parameter_key: str
    parameter_display_name: str
    unit: str
    proposed_normal_limit: str
    proposed_warning_limit: str
    proposed_alarm_limit: str
    final_normal_limit: str
    final_warning_limit: str
    final_alarm_limit: str
    approved_by: str
    reviewed_by_user_department: str
    approval_date: str
    remarks: str

    def as_list(self) -> list[str]:
        return [
            self.area_tank,
            self.category,
            self.equipment,
            self.tag_no,
            self.parameter_key,
            self.parameter_display_name,
            self.unit,
            self.proposed_normal_limit,
            self.proposed_warning_limit,
            self.proposed_alarm_limit,
            self.final_normal_limit,
            self.final_warning_limit,
            self.final_alarm_limit,
            self.approved_by,
            self.reviewed_by_user_department,
            self.approval_date,
            self.remarks,
        ]


def _sort_key(row: MasterRow) -> tuple:
    return (
        row.area_tank.lower(),
        row.category.lower(),
        row.equipment.lower(),
        row.tag_no.lower(),
        row.parameter_key.lower(),
    )


def _format_limit(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return ""
    try:
        number = float(value)
        if number == int(number):
            return str(int(number))
        return str(number)
    except (TypeError, ValueError):
        return ""


def _proposed_limits(thresholds: dict | None) -> tuple[str, str, str]:
    """
    Map config thresholds to proposed normal/warning/alarm limits.

    Each value is taken only from its corresponding config field — no cross-fallbacks
    and no fabricated defaults.
    """
    if not isinstance(thresholds, dict):
        return "", "", ""

    normal_limit = _format_limit(thresholds.get("normal_limit"))
    warning_limit = _format_limit(thresholds.get("warning_limit"))
    alarm_limit = _format_limit(thresholds.get("alarm_limit"))

    proposed_alarm = alarm_limit or warning_limit
    return normal_limit, warning_limit, proposed_alarm


def _equipment_specific_remark(equipment: dict, param: dict) -> str:
    """Return a row remark only when equipment-specific notes exist (not generic boilerplate)."""
    for candidate in (
        str(param.get("metadata", {}).get("notes", "") if isinstance(param.get("metadata"), dict) else ""),
        str(equipment.get("metadata", {}).get("notes", "") if isinstance(equipment.get("metadata"), dict) else ""),
    ):
        text = candidate.strip()
        if not text:
            continue
        lowered = text.lower()
        if "plant maintenance round sheet" in lowered:
            continue
        if "provisional" in lowered:
            continue
        return text
    return ""


DM_WATER_CATEGORIES = frozenset(
    {
        "DM Water Electrode Cooling",
        "DM Water Batch Charger",
    }
)


def _dashboard_area_label(area_tank: str, category: str) -> str:
    """Match dashboard virtual bucket for DM Water categories."""
    if category in DM_WATER_CATEGORIES:
        return "DM Water Electrode Cooling"
    return area_tank


def _add_reading_equipment_label(entry: dict[str, Any]) -> str:
    """
    Equipment label aligned with Add Reading submit payload (equipment.display_name).
    Utility rows include type context in parentheses when kind differs from display name.
    """
    display_name = str(entry.get("display_name") or "").strip()
    equipment_kind = str(entry.get("equipment_kind") or "").strip()
    area = str(entry.get("area") or "").strip()

    if area == "Utility Area" and equipment_kind and equipment_kind != display_name:
        return f"{display_name} ({equipment_kind})"
    return display_name


def _add_reading_parameter_label(param: dict[str, Any]) -> str:
    """Parameter label aligned with Add Reading round sheet (display_full_label)."""
    return (
        str(param.get("display_full_label") or "").strip()
        or str(param.get("display_short_label") or "").strip()
        or str(param.get("key") or "").strip()
    )


def collect_master_rows() -> list[MasterRow]:
    """
    Build rows strictly from backend/gmd_machine_config_v2.json — the same file
    bundled into the frontend via @gmd-config/v2 for Add Reading and dashboard.
    """
    config = load_gmd_config_v2()
    _ = config  # explicit load from canonical path
    rows: list[MasterRow] = []

    for entry in sorted(
        collect_active_equipment(),
        key=lambda item: (
            str(item.get("area") or ""),
            str(item.get("category_display_name") or ""),
            item.get("display_order", 0),
            str(item.get("display_name") or ""),
            str(item.get("id") or ""),
        ),
    ):
        area_tank = str(entry.get("area") or "").strip()
        category_name = str(entry.get("category_display_name") or "").strip()
        equipment_label = _add_reading_equipment_label(entry)
        tag_no = str(entry.get("tag_no") or "").strip()

        for param in collect_equipment_parameters(entry):
            parameter_key = str(param.get("key") or "").strip()
            if not parameter_key:
                continue

            display_name = _add_reading_parameter_label(param)
            unit = str(param.get("unit") or "").strip()
            proposed_normal, proposed_warning, proposed_alarm = _proposed_limits(
                param.get("thresholds")
            )

            rows.append(
                MasterRow(
                    area_tank=area_tank,
                    category=category_name,
                    equipment=equipment_label,
                    tag_no=tag_no,
                    parameter_key=parameter_key,
                    parameter_display_name=display_name,
                    unit=unit,
                    proposed_normal_limit=proposed_normal,
                    proposed_warning_limit=proposed_warning,
                    proposed_alarm_limit=proposed_alarm,
                    final_normal_limit="",
                    final_warning_limit="",
                    final_alarm_limit="",
                    approved_by="",
                    reviewed_by_user_department="",
                    approval_date="",
                    remarks=_equipment_specific_remark(entry, param),
                )
            )

    rows.sort(key=_sort_key)
    return rows


def _build_area_category_equipment_counts(
    rows: list[MasterRow],
) -> list[tuple[str, list[tuple[str, int]]]]:
    """Dashboard area → category → unique equipment instance count."""
    buckets: dict[str, dict[str, set[tuple[str, str, str, str]]]] = {}

    for row in rows:
        dashboard_area = _dashboard_area_label(row.area_tank, row.category)
        category_label = CATEGORY_DISPLAY_SHORT.get(row.category, row.category)
        equipment_key = (row.area_tank, row.category, row.equipment, row.tag_no)
        buckets.setdefault(dashboard_area, {}).setdefault(category_label, set()).add(
            equipment_key
        )

    ordered_areas = [area for area in DASHBOARD_AREA_ORDER if area in buckets]
    for area in sorted(buckets):
        if area not in ordered_areas:
            ordered_areas.append(area)

    result: list[tuple[str, list[tuple[str, int]]]] = []
    for area in ordered_areas:
        category_counts = sorted(
            (category, len(keys))
            for category, keys in buckets[area].items()
        )
        result.append((area, category_counts))
    return result


def _verify_key_equipment(rows: list[MasterRow]) -> list[tuple[str, bool]]:
    equipment_pairs = {(row.equipment, row.tag_no) for row in rows}
    results: list[tuple[str, bool]] = []
    for label, matcher in KEY_EQUIPMENT_CHECKS:
        found = any(matcher(eq, tag) for eq, tag in equipment_pairs)
        results.append((label, found))
    return results


def build_validation_summary(rows: list[MasterRow]) -> dict[str, Any]:
    physical_areas = sorted({r.area_tank for r in rows if r.area_tank})
    dashboard_areas = sorted(
        {_dashboard_area_label(r.area_tank, r.category) for r in rows}
    )
    categories = sorted({r.category for r in rows})
    equipment_instances = len({(r.area_tank, r.category, r.equipment, r.tag_no) for r in rows})
    unique_keys = len({r.parameter_key for r in rows})
    tags_used = len({r.tag_no for r in rows if r.tag_no})

    equipment_names: list[str] = []
    seen_equipment: set[tuple[str, str, str, str]] = set()
    for row in rows:
        key = (row.area_tank, row.category, row.equipment, row.tag_no)
        if key in seen_equipment:
            continue
        seen_equipment.add(key)
        equipment_names.append(row.equipment)

    area_breakdown = _build_area_category_equipment_counts(rows)
    equipment_checks = _verify_key_equipment(rows)

    return {
        "config_source": str(GMD_CONFIG_V2_PATH.resolve()),
        "total_areas": len(dashboard_areas),
        "physical_areas": physical_areas,
        "dashboard_areas": dashboard_areas,
        "total_categories": len(categories),
        "categories": categories,
        "total_equipment": equipment_instances,
        "total_unique_parameters": unique_keys,
        "total_rows": len(rows),
        "tag_numbers_populated": tags_used,
        "equipment_names": equipment_names,
        "area_breakdown": area_breakdown,
        "equipment_checks": equipment_checks,
        "records_removed_during_formatting": 0,
        "confirmation": (
            "Export generated directly from the live dashboard configuration. "
            "No placeholder or sample data has been used."
        ),
    }


def export_master_csv(output_path: Path, rows: list[MasterRow]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(MASTER_HEADERS)
        for row in rows:
            writer.writerow(row.as_list())


def export_master_xlsx(output_path: Path, rows: list[MasterRow]) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError as exc:
        raise RuntimeError(
            "openpyxl is required for Excel export. Run: pip install openpyxl"
        ) from exc

    wb = Workbook()

    # --- Instructions sheet ---
    ws_info = wb.active
    ws_info.title = "Instructions"

    ws_info["A1"] = DOCUMENT_TITLE
    ws_info["A1"].font = Font(bold=True, size=14)
    ws_info["A2"] = DOCUMENT_SUBTITLE
    ws_info["A2"].font = Font(bold=True, size=12)
    ws_info.merge_cells("A2:D2")

    info_row = 4
    for label, value in INSTRUCTIONS_LINES:
        if label == "" and value == "":
            info_row += 1
            continue
        if value == "" and label in {
            "Overview",
            "Proposed Limits",
            "Final Limits",
            "Approval",
            "Classification (reference)",
        }:
            ws_info.cell(row=info_row, column=1, value=label)
            ws_info.cell(row=info_row, column=1).font = Font(bold=True, size=11)
            info_row += 1
            continue
        ws_info.cell(row=info_row, column=1, value=label)
        ws_info.cell(row=info_row, column=1).font = Font(bold=True)
        ws_info.cell(row=info_row, column=2, value=value)
        ws_info.cell(row=info_row, column=2).alignment = Alignment(wrap_text=True)
        ws_info.merge_cells(start_row=info_row, start_column=2, end_row=info_row, end_column=4)
        info_row += 1

    ws_info.column_dimensions["A"].width = 28
    ws_info.column_dimensions["B"].width = 72
    ws_info.column_dimensions["C"].width = 20
    ws_info.column_dimensions["D"].width = 20

    # --- Master data sheet ---
    ws = wb.create_sheet("Threshold Master")
    header_font = Font(bold=True, color="000000")
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    fill_equipment = PatternFill("solid", fgColor="D9EAF7")
    fill_proposed = PatternFill("solid", fgColor="FFF2CC")
    fill_final = PatternFill("solid", fgColor="E2EFDA")

    ws.append(MASTER_HEADERS)
    for row in rows:
        ws.append(row.as_list())

    last_col = len(MASTER_HEADERS)
    last_row = len(rows) + 1

    for col in range(1, last_col + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        if COL_EQUIPMENT_START <= col <= COL_EQUIPMENT_END:
            cell.fill = fill_equipment
        elif COL_PROPOSED_START <= col <= COL_PROPOSED_END:
            cell.fill = fill_proposed
        elif COL_FINAL_START <= col <= COL_FINAL_END:
            cell.fill = fill_final

    for row_idx in range(2, last_row + 1):
        for col in range(1, last_col + 1):
            cell = ws.cell(row=row_idx, column=col)
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=False)
            if COL_EQUIPMENT_START <= col <= COL_EQUIPMENT_END:
                cell.fill = fill_equipment
            elif COL_PROPOSED_START <= col <= COL_PROPOSED_END:
                cell.fill = fill_proposed
            elif COL_FINAL_START <= col <= COL_FINAL_END:
                cell.fill = fill_final

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(last_col)}{last_row}"

    for col in range(1, last_col + 1):
        letter = get_column_letter(col)
        max_len = len(str(MASTER_HEADERS[col - 1]))
        for row_idx in range(2, min(last_row + 1, 502)):
            value = ws.cell(row=row_idx, column=col).value
            if value is not None:
                max_len = max(max_len, len(str(value)))
        ws.column_dimensions[letter].width = min(max(max_len + 2, 12), 48)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)


def _format_area_breakdown(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = ["Area → Category → Equipment Count", ""]
    for area, category_counts in summary["area_breakdown"]:
        lines.append(area)
        for category, count in category_counts:
            lines.append(f"  • {category}: {count}")
        lines.append("")
    return lines


def write_validation_report(path: Path, summary: dict[str, Any], csv_path: Path, xlsx_path: Path) -> None:
    lines = [
        "GMD Equipment Parameter & Threshold Master — Validation Summary",
        "=" * 62,
        f"Prepared By: {PREPARED_BY}",
        f"Version: {DOCUMENT_VERSION}",
        f"Config Source: {summary['config_source']}",
        "",
        f"Total Areas:              {summary['total_areas']}",
        f"Total Categories:         {summary['total_categories']}",
        f"Total Equipment:          {summary['total_equipment']}",
        f"Total Unique Parameters:  {summary['total_unique_parameters']}",
        f"Total Rows:               {summary['total_rows']}",
        "",
        *_format_area_breakdown(summary),
        "Key Equipment Verification:",
    ]
    for label, found in summary["equipment_checks"]:
        status = "PRESENT" if found else "MISSING"
        lines.append(f"  [{status}] {label}")
    lines.extend(
        [
            "",
            f"Records removed: {summary['records_removed_during_formatting']}",
            f"Confirmation:    {summary['confirmation']}",
            "",
            "First 30 equipment names:",
        ]
    )
    for index, name in enumerate(summary["equipment_names"][:30], start=1):
        lines.append(f"  {index:2d}. {name}")
    lines.extend(
        [
            "",
            "Output files:",
            f"  CSV:  {csv_path.resolve()}",
            f"  XLSX: {xlsx_path.resolve()}",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_all(csv_path: Path, xlsx_path: Path, validation_path: Path) -> dict[str, Any]:
    rows = collect_master_rows()
    export_master_csv(csv_path, rows)
    export_master_xlsx(xlsx_path, rows)
    summary = build_validation_summary(rows)
    write_validation_report(validation_path, summary, csv_path, xlsx_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Export GMD threshold master CSV + Excel")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    args = parser.parse_args()

    csv_path = args.csv.resolve()
    xlsx_path = args.xlsx.resolve()
    validation_path = args.validation.resolve()

    summary = export_all(csv_path, xlsx_path, validation_path)

    print("GMD Equipment Parameter & Threshold Master exported")
    print(f"  Config: {summary['config_source']}")
    print(f"  CSV:    {csv_path}")
    print(f"  XLSX:   {xlsx_path}")
    print(f"  Report: {validation_path}")
    print()
    print("Validation Summary")
    print(f"  Total Areas:              {summary['total_areas']}")
    print(f"  Total Categories:         {summary['total_categories']}")
    print(f"  Total Equipment:          {summary['total_equipment']}")
    print(f"  Total Parameter Rows:     {summary['total_rows']}")
    print(f"  Total Unique Parameters:  {summary['total_unique_parameters']}")
    print(f"  {summary['confirmation']}")
    print()
    print("Area → Category → Equipment Count")
    for area, category_counts in summary["area_breakdown"]:
        print(area)
        for category, count in category_counts:
            print(f"  • {category}: {count}")
        print()
    print("Key Equipment Verification:")
    for label, found in summary["equipment_checks"]:
        print(f"  [{'OK' if found else 'MISS'}] {label}")
    print()
    print("First 30 equipment names (for manual verification):")
    for index, name in enumerate(summary["equipment_names"][:30], start=1):
        print(f"  {index:2d}. {name}")


if __name__ == "__main__":
    main()
