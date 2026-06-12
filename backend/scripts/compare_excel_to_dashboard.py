"""Compare threshold Excel/CSV template against V1 and V2 dashboard configuration."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def load_csv_rows(path: Path) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                (
                    row["Category"].strip(),
                    row["Equipment"].strip(),
                    row["Parameter_Key"].strip(),
                )
            )
    return rows


def load_v1_equipment(path: Path) -> dict[str, set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {cat["name"]: set(cat["equipment"]) for cat in data["categories"].values()}


def load_v1_params(path: Path) -> dict[str, set[str]]:
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r'"([^"]+)":\s*\{\s*parameters:\s*\[(.*?)\]', text, re.S)
    result: dict[str, set[str]] = {}
    for name, plist in blocks:
        result[name.strip()] = set(re.findall(r'"([^"]+)"', plist))
    return result


def extract_v2(path: Path) -> tuple[set[str], dict[str, set[str]], list[tuple[str, str, str, str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    areas: set[str] = set()
    by_area: dict[str, set[str]] = defaultdict(set)
    rows: list[tuple[str, str, str, str]] = []

    for plant in data.get("plants", []):
        for area in plant.get("areas", []):
            if area.get("active", True) is False:
                continue
            areas.add(area["display_name"])

        for category in plant.get("categories", []):
            if category.get("active", True) is False:
                continue
            category_name = category["display_name"]
            for equipment in category.get("equipment", []):
                if equipment.get("active", True) is False:
                    continue
                equipment_name = equipment["display_name"]
                area_name = equipment.get("area", "")
                if area_name:
                    by_area[area_name].add(equipment_name)
                for section in equipment.get("sections", []):
                    for group in section.get("groups", []):
                        for param in group.get("parameters", []):
                            if param.get("active", True) is False:
                                continue
                            key = param.get("key") or param.get("id")
                            if key:
                                rows.append((area_name, category_name, equipment_name, key))
    return areas, dict(by_area), rows


def main() -> int:
    csv_path = ROOT / "templates" / "GMD_Threshold_Collection_Template.csv"
    csv_rows = load_csv_rows(csv_path)
    csv_equip = {(cat, eq) for cat, eq, _ in csv_rows}
    csv_params = set(csv_rows)
    csv_equip_names = {eq for _, eq, _ in csv_rows}

    v1_equip = load_v1_equipment(BACKEND / "gmd_machine_config.json")
    v1_params = load_v1_params(ROOT / "frontend" / "src" / "lib" / "equipmentConfig.js")
    areas, by_area, v2_rows = extract_v2(BACKEND / "gmd_machine_config_v2.json")

    v2_by_cat_eq: dict[tuple[str, str], set[str]] = defaultdict(set)
    v2_equip_names: set[str] = set()
    for _, cat, eq, pk in v2_rows:
        v2_by_cat_eq[(cat, eq)].add(pk)
        v2_equip_names.add(eq)

    missing_v1_equip = sorted(
        (cat, eq) for cat, eq in csv_equip if cat not in v1_equip or eq not in v1_equip[cat]
    )
    missing_v1_params = sorted(
        item for item in csv_params if item[1] not in v1_params or item[2] not in v1_params[item[1]]
    )
    missing_v2_params = sorted(
        item for item in csv_params if item[2] not in v2_by_cat_eq.get((item[0], item[1]), set())
    )
    csv_only_equip = sorted(eq for eq in csv_equip_names if eq not in v2_equip_names)
    v2_only_equip = sorted(v2_equip_names - csv_equip_names)

    print("=== Excel/CSV vs Dashboard Configuration Audit ===")
    print(f"Source file: {csv_path.name}")
    print(f"Template rows: {len(csv_rows)}")
    print(f"Unique equipment in template: {len(csv_equip_names)}")
    print()
    print("--- Tanks / Areas (V2 dashboard only) ---")
    for area in sorted(areas):
        print(f"  {area}: {len(by_area.get(area, set()))} equipment configured")
    print()
    print("--- V1 Dashboard (Bulk Entry / legacy) ---")
    print(f"  gmd_machine_config.json equipment missing: {len(missing_v1_equip)}")
    print(f"  equipmentConfig.js parameters missing: {len(missing_v1_params)}")
    if missing_v1_equip:
        print("  Missing equipment:")
        for item in missing_v1_equip:
            print(f"    - {item[0]} / {item[1]}")
    if missing_v1_params:
        print("  Missing parameters:")
        for cat, eq, pk in missing_v1_params:
            print(f"    - {cat} / {eq} / {pk}")
    if not missing_v1_equip and not missing_v1_params:
        print("  All template equipment and parameters are present in V1 dashboard config.")
    print()
    print("--- V2 Dashboard (Add Reading / round sheets) ---")
    print(f"  Parameters missing for template category+equipment pairs: {len(missing_v2_params)}")
    print(f"  Template equipment names not found in V2 at all: {len(csv_only_equip)}")
    print(f"  V2 equipment names not in template (extra in dashboard): {len(v2_only_equip)}")
    if missing_v2_params:
        print("  Missing parameters (first 40):")
        for cat, eq, pk in missing_v2_params[:40]:
            print(f"    - {cat} / {eq} / {pk}")
        if len(missing_v2_params) > 40:
            print(f"    ... and {len(missing_v2_params) - 40} more")
    if csv_only_equip:
        print("  Template equipment absent from V2:")
        for name in csv_only_equip:
            print(f"    - {name}")
    if v2_only_equip:
        print("  Extra V2 equipment vs template (renamed or tank-specific instances, first 30):")
        for name in v2_only_equip[:30]:
            print(f"    - {name}")
        if len(v2_only_equip) > 30:
            print(f"    ... and {len(v2_only_equip) - 30} more")

    # Category-level V2 coverage
    v2_cats: dict[str, dict[str, object]] = defaultdict(
        lambda: {"equip": set(), "param_instances": 0, "areas": set()}
    )
    v2_data = json.loads((BACKEND / "gmd_machine_config_v2.json").read_text(encoding="utf-8"))
    for plant in v2_data.get("plants", []):
        for category in plant.get("categories", []):
            cat_name = category["display_name"]
            for equipment in category.get("equipment", []):
                if equipment.get("active", True) is False:
                    continue
                v2_cats[cat_name]["equip"].add(equipment["display_name"])
                area = equipment.get("area", "")
                if area:
                    v2_cats[cat_name]["areas"].add(area)
                for section in equipment.get("sections", []):
                    for group in section.get("groups", []):
                        for param in group.get("parameters", []):
                            if param.get("active", True) is False:
                                continue
                            v2_cats[cat_name]["param_instances"] += 1

    excel_cats = sorted({cat for cat, _, _ in csv_rows})
    print()
    print("--- Excel categories vs V2 categories ---")
    for cat in excel_cats:
        if cat in v2_cats:
            info = v2_cats[cat]
            print(
                f"  {cat}: present in V2 "
                f"({len(info['equip'])} equipment names, "
                f"{info['param_instances']} parameter slots, "
                f"areas: {', '.join(sorted(info['areas']))})"
            )
        else:
            print(f"  {cat}: NOT a separate V2 category (see notes below)")

    if "Cooling Tower Water Monitoring" not in v2_cats:
        ct_like = sorted(
            name
            for name in v2_equip_names
            if "CT" in name or "Cooling Tower" in name
        )
        print()
        print("  Cooling Tower Water Monitoring from Excel appears under Utility Area in V2:")
        for name in ct_like[:15]:
            print(f"    - {name}")

    print()
    print("--- Important note on parameter keys ---")
    print(
        "  V1/Excel uses simplified keys (e.g. vertical_vibration, temperature). "
        "V2 round sheets use detailed plant keys (e.g. blower_drive_end_vertical, motor_de_temperature). "
        "V2 has MORE parameters per equipment than the 89-row Excel template."
    )

    # Semantic coverage for MCB-1
    mcb1_params = sorted(
        pk for _, cat, eq, pk in v2_rows if eq == "MCB-1"
    )
    if mcb1_params:
        print()
        print(f"  Example: MCB-1 has {len(mcb1_params)} V2 parameters vs 6 in Excel:")
        for pk in mcb1_params:
            print(f"    - {pk}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
