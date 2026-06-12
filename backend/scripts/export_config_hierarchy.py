"""Export plant hierarchy and parameter catalogue from gmd_machine_config_v2.json."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "gmd_machine_config_v2.json"
OUT = Path(__file__).resolve().parent.parent / "reports" / "config_hierarchy_export.json"

DM = {"DM Water Electrode Cooling", "DM Water Batch Charger"}


def dashboard_bucket(area: str, category: str) -> str:
    if category in DM:
        return "DM Water Electrode Cooling"
    return area or "Unknown"


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    hierarchy: dict = defaultdict(lambda: defaultdict(list))
    catalogue: list[dict] = []

    for plant in config.get("plants", []):
        if plant.get("active") is False:
            continue
        for cat in plant.get("categories", []):
            if cat.get("active") is False:
                continue
            cat_name = cat.get("display_name", "")
            for eq in cat.get("equipment", []):
                if eq.get("active") is False:
                    continue
                bucket = dashboard_bucket(eq.get("area", ""), cat_name)
                tag = eq.get("tag_no") or ""
                params = []
                for sec in eq.get("sections", []):
                    if sec.get("active") is False:
                        continue
                    for grp in sec.get("groups", []):
                        if grp.get("active") is False:
                            continue
                        for p in grp.get("parameters", []):
                            if p.get("is_visible") is False or p.get("active") is False:
                                continue
                            entry = {
                                "key": p.get("key"),
                                "display_name": p.get("display_full_label")
                                or p.get("display_short_label"),
                                "unit": p.get("unit", ""),
                            }
                            params.append(entry)
                            catalogue.append(
                                {
                                    **entry,
                                    "category": cat_name,
                                    "equipment": eq.get("display_name"),
                                    "physical_area": eq.get("area", ""),
                                    "dashboard_area": bucket,
                                    "tag_no": tag,
                                }
                            )
                hierarchy[bucket][cat_name].append(
                    {
                        "equipment": eq.get("display_name"),
                        "tag_no": tag,
                        "physical_area": eq.get("area", ""),
                        "parameters": params,
                    }
                )

    payload = {
        "hierarchy": {k: dict(v) for k, v in hierarchy.items()},
        "parameter_catalogue": catalogue,
        "equipment_count": sum(
            len(eqs) for bucket in hierarchy.values() for eqs in bucket.values()
        ),
        "parameter_instance_count": len(catalogue),
        "unique_parameter_keys": len({p["key"] for p in catalogue}),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"Equipment: {payload['equipment_count']}")
    print(f"Parameter instances: {payload['parameter_instance_count']}")


if __name__ == "__main__":
    main()
