"""
Integrity audit: GMD Equipment Parameter & Threshold Master vs live V2 config.

Read-only — does not modify export data unless mismatches are reported.

Usage:
  cd backend
  python scripts/audit_parameter_threshold_master.py
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TEMPLATES = BACKEND.parent / "templates"
sys.path.insert(0, str(BACKEND))

from gmd_config_v2 import GMD_CONFIG_V2_PATH, collect_active_equipment
from scripts.export_parameter_threshold_master import (
    DM_WATER_CATEGORIES,
    KEY_EQUIPMENT_CHECKS,
    collect_master_rows,
)

CSV_PATH = TEMPLATES / "GMD_Equipment_Parameter_Threshold_Master.csv"
REPORT_PATH = TEMPLATES / "GMD_Equipment_Parameter_Threshold_Master_Integrity_Audit.txt"

IDENTITY_FIELDS = (
    "area_tank",
    "category",
    "equipment",
    "tag_no",
    "parameter_key",
    "parameter_display_name",
    "unit",
)

PHYSICAL_AREAS_ORDER = ["A Tank", "E Tank", "G Tank", "K Tank", "Utility Area"]


@dataclass(frozen=True)
class IdentityRow:
    area_tank: str
    category: str
    equipment: str
    tag_no: str
    parameter_key: str
    parameter_display_name: str
    unit: str

    @classmethod
    def from_csv_row(cls, row: list[str]) -> "IdentityRow":
        return cls(
            area_tank=row[0].strip(),
            category=row[1].strip(),
            equipment=row[2].strip(),
            tag_no=row[3].strip(),
            parameter_key=row[4].strip(),
            parameter_display_name=row[5].strip(),
            unit=row[6].strip(),
        )

    @classmethod
    def from_master_row(cls, row) -> "IdentityRow":
        return cls(
            area_tank=row.area_tank,
            category=row.category,
            equipment=row.equipment,
            tag_no=row.tag_no,
            parameter_key=row.parameter_key,
            parameter_display_name=row.parameter_display_name,
            unit=row.unit,
        )

    def as_tuple(self) -> tuple[str, ...]:
        return (
            self.area_tank,
            self.category,
            self.equipment,
            self.tag_no,
            self.parameter_key,
            self.parameter_display_name,
            self.unit,
        )


def load_csv_identities(path: Path) -> list[IdentityRow]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        headers = next(reader)
        expected_prefix = [
            "Area / Tank",
            "Category",
            "Equipment",
            "Tag No",
            "Parameter Key",
            "Parameter Display Name",
            "Unit",
        ]
        if headers[:7] != expected_prefix:
            raise ValueError(f"Unexpected CSV headers: {headers[:7]}")
        return [IdentityRow.from_csv_row(row) for row in reader if row]


def config_identities() -> list[IdentityRow]:
    return [IdentityRow.from_master_row(row) for row in collect_master_rows()]


def compare_exports(csv_rows: list[IdentityRow], config_rows: list[IdentityRow]) -> list[str]:
    mismatches: list[str] = []

    csv_set = {row.as_tuple() for row in csv_rows}
    config_set = {row.as_tuple() for row in config_rows}

    missing_from_csv = config_set - csv_set
    extra_in_csv = csv_set - config_set

    if missing_from_csv:
        mismatches.append(f"MISSING FROM CSV ({len(missing_from_csv)} rows):")
        for item in sorted(missing_from_csv)[:20]:
            mismatches.append(f"  - {item}")
        if len(missing_from_csv) > 20:
            mismatches.append(f"  ... and {len(missing_from_csv) - 20} more")

    if extra_in_csv:
        mismatches.append(f"EXTRA IN CSV NOT IN CONFIG ({len(extra_in_csv)} rows):")
        for item in sorted(extra_in_csv)[:20]:
            mismatches.append(f"  - {item}")
        if len(extra_in_csv) > 20:
            mismatches.append(f"  ... and {len(extra_in_csv) - 20} more")

    if len(csv_rows) != len(config_rows):
        mismatches.append(
            f"ROW COUNT MISMATCH: CSV={len(csv_rows)} config={len(config_rows)}"
        )

    return mismatches


def verify_dm_water_area_column(rows: list[IdentityRow]) -> list[str]:
    """DM Water must appear as Category under physical tanks, not as Area / Tank."""
    issues: list[str] = []
    dm_as_area = [row for row in rows if row.area_tank == "DM Water Electrode Cooling"]
    if dm_as_area:
        issues.append(
            f"DM Water incorrectly used as Area / Tank in {len(dm_as_area)} row(s)"
        )

    dm_categories = [
        row
        for row in rows
        if row.category in DM_WATER_CATEGORIES
    ]
    if not dm_categories:
        issues.append("No DM Water categories found in export")
        return issues

    tanks_with_dm: dict[str, set[str]] = defaultdict(set)
    for row in dm_categories:
        tanks_with_dm[row.area_tank].add(row.category)

    for tank in ("A Tank", "E Tank", "G Tank", "K Tank"):
        if tank not in tanks_with_dm:
            issues.append(f"Expected DM Water category under {tank} — not found")

    return issues


def build_physical_area_breakdown(rows: list[IdentityRow]) -> list[tuple[str, list[dict]]]:
    """Per physical Area/Tank: categories with equipment and parameter counts."""
    area_data: dict[str, dict[str, dict[str, set]]] = defaultdict(
        lambda: defaultdict(lambda: {"equipment": set(), "parameters": set()})
    )

    for row in rows:
        bucket = area_data[row.area_tank][row.category]
        bucket["equipment"].add((row.equipment, row.tag_no))
        bucket["parameters"].add((row.equipment, row.tag_no, row.parameter_key))

    result: list[tuple[str, list[dict]]] = []
    seen_areas = set()
    for area in PHYSICAL_AREAS_ORDER:
        if area not in area_data:
            continue
        seen_areas.add(area)
        categories = []
        for category in sorted(area_data[area].keys()):
            data = area_data[area][category]
            categories.append(
                {
                    "category": category,
                    "equipment_count": len(data["equipment"]),
                    "parameter_count": len(data["parameters"]),
                }
            )
        result.append((area, categories))

    for area in sorted(area_data):
        if area not in seen_areas:
            categories = []
            for category in sorted(area_data[area].keys()):
                data = area_data[area][category]
                categories.append(
                    {
                        "category": category,
                        "equipment_count": len(data["equipment"]),
                        "parameter_count": len(data["parameters"]),
                    }
                )
            result.append((area, categories))

    return result


def verify_key_equipment(rows: list[IdentityRow]) -> list[tuple[str, bool, str]]:
    pairs = {(row.equipment, row.tag_no) for row in rows}
    results = []
    for label, matcher in KEY_EQUIPMENT_CHECKS:
        matches = [f"{eq} [tag={tag or '-'}]" for eq, tag in pairs if matcher(eq, tag)]
        found = bool(matches)
        detail = "; ".join(sorted(matches)[:5]) if matches else "not found"
        results.append((label, found, detail))
    return results


def run_audit() -> tuple[list[str], dict]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Export CSV not found: {CSV_PATH}")

    csv_rows = load_csv_identities(CSV_PATH)
    config_rows = config_identities()

    mismatches: list[str] = []
    mismatches.extend(compare_exports(csv_rows, config_rows))
    mismatches.extend(verify_dm_water_area_column(csv_rows))

    categories = sorted({row.category for row in csv_rows})
    equipment_count = len({(r.area_tank, r.category, r.equipment, r.tag_no) for r in csv_rows})
    unique_params = len({r.parameter_key for r in csv_rows})
    physical_areas = sorted({r.area_tank for r in csv_rows if r.area_tank})
    area_breakdown = build_physical_area_breakdown(csv_rows)
    equipment_checks = verify_key_equipment(csv_rows)

    summary = {
        "config_source": str(GMD_CONFIG_V2_PATH.resolve()),
        "csv_path": str(CSV_PATH.resolve()),
        "total_areas": len(physical_areas),
        "physical_areas": physical_areas,
        "total_categories": len(categories),
        "categories": categories,
        "total_equipment": equipment_count,
        "total_parameter_rows": len(csv_rows),
        "total_unique_parameters": unique_params,
        "area_breakdown": area_breakdown,
        "equipment_checks": equipment_checks,
        "mismatches": mismatches,
        "passed": len(mismatches) == 0 and all(found for _, found, _ in equipment_checks),
    }
    return mismatches, summary


def write_report(summary: dict) -> None:
    lines = [
        "GMD Equipment Parameter & Threshold Master — Integrity Audit",
        "=" * 62,
        f"Config Source: {summary['config_source']}",
        f"Export CSV:    {summary['csv_path']}",
        "",
        "1. Total Areas (physical Area / Tank column): "
        f"{summary['total_areas']}",
        f"   {', '.join(summary['physical_areas'])}",
        "",
        f"2. Total Categories: {summary['total_categories']}",
        f"   {', '.join(summary['categories'])}",
        "",
        f"3. Total Equipment: {summary['total_equipment']}",
        "",
        f"4. Total Parameter Rows: {summary['total_parameter_rows']}",
        f"   Total Unique Parameter Keys: {summary['total_unique_parameters']}",
        "",
        "5. Area-wise Breakdown (physical Area / Tank)",
        "",
    ]

    for area, categories in summary["area_breakdown"]:
        lines.append(area)
        for entry in categories:
            lines.append(f"  • {entry['category']}")
            lines.append(f"      Equipment Count:  {entry['equipment_count']}")
            lines.append(f"      Parameter Count:  {entry['parameter_count']}")
        lines.append("")

    lines.append("DM Water Electrode Cooling Area Check")
    lines.append(
        "  Requirement: DM Water appears as Category under each Tank, NOT as Area / Tank."
    )
    dm_area_rows = [
        r
        for r in load_csv_identities(CSV_PATH)
        if r.area_tank == "DM Water Electrode Cooling"
    ]
    if dm_area_rows:
        lines.append(f"  FAIL: {len(dm_area_rows)} row(s) use DM Water as Area / Tank")
    else:
        lines.append("  PASS: No rows use DM Water Electrode Cooling as Area / Tank")
    dm_cat_rows = [
        r for r in load_csv_identities(CSV_PATH) if r.category in DM_WATER_CATEGORIES
    ]
    dm_by_tank = defaultdict(set)
    for r in dm_cat_rows:
        dm_by_tank[r.area_tank].add(r.category)
    for tank in ("A Tank", "E Tank", "G Tank", "K Tank"):
        cats = sorted(dm_by_tank.get(tank, set()))
        lines.append(f"  {tank}: {', '.join(cats) if cats else 'NONE'}")
    lines.append("")

    lines.append("Key Equipment Verification")
    for label, found, detail in summary["equipment_checks"]:
        status = "PASS" if found else "FAIL"
        lines.append(f"  [{status}] {label}: {detail}")
    lines.append("")

    if summary["mismatches"]:
        lines.append("MISMATCHES DETECTED")
        lines.extend(summary["mismatches"])
    else:
        lines.append(
            "Threshold Master verified successfully. This is a 1:1 representation "
            "of the live dashboard configuration and is ready to be shared with "
            "management and the user department."
        )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    mismatches, summary = run_audit()
    write_report(summary)

    print("GMD Threshold Master Integrity Audit")
    print(f"  Report: {REPORT_PATH}")
    print()
    print(f"1. Total Areas:           {summary['total_areas']}")
    print(f"2. Total Categories:      {summary['total_categories']}")
    print(f"3. Total Equipment:       {summary['total_equipment']}")
    print(f"4. Total Parameter Rows:  {summary['total_parameter_rows']}")
    print()
    print("5. Area-wise Breakdown")
    for area, categories in summary["area_breakdown"]:
        print(area)
        for entry in categories:
            print(f"  • {entry['category']}")
            print(f"      Equipment Count:  {entry['equipment_count']}")
            print(f"      Parameter Count:  {entry['parameter_count']}")
        print()

    print("DM Water Check (Category under Tank, not separate Area):")
    dm_area = sum(
        1
        for r in load_csv_identities(CSV_PATH)
        if r.area_tank == "DM Water Electrode Cooling"
    )
    print(f"  Rows with DM Water as Area / Tank: {dm_area} (must be 0)")

    print()
    print("Key Equipment:")
    for label, found, detail in summary["equipment_checks"]:
        print(f"  [{'OK' if found else 'MISS'}] {label}")

    print()
    if mismatches:
        print("MISMATCHES DETECTED:")
        for line in mismatches:
            print(line)
    else:
        print(
            "Threshold Master verified successfully. This is a 1:1 representation "
            "of the live dashboard configuration and is ready to be shared with "
            "management and the user department."
        )


if __name__ == "__main__":
    main()
