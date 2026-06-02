#!/usr/bin/env python3
"""
Post sample bulk readings for every GT area in machine_config.json.
Usage:
  python scripts/verify_all_machines.py
  python scripts/verify_all_machines.py --base-url https://electrical-condition-monitoring-system.onrender.com
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "machine_config.json"
PLANT_ID = "GT"


def post_bulk(base_url: str, machine_id: str, motors: list[str]) -> dict:
    readings = []
    for i, motor in enumerate(motors):
        readings.append(
            {
                "motor": motor,
                "current": 10.0 + i,
                "temperature": 50.0 + i,
                "vibration": 3.0 + (i * 0.1),
            }
        )
    payload = {
        "plant": PLANT_ID,
        "machine": machine_id,
        "readings": readings,
        "technician": "verify_all_machines.py",
        "entry_source": "AutomatedVerification",
    }
    url = f"{base_url.rstrip('/')}/condition-monitoring/bulk"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API base URL",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    with CONFIG_PATH.open(encoding="utf-8") as fh:
        config = json.load(fh)

    machines = config["plants"][PLANT_ID]["machines"]
    ok = 0
    failed = 0

    print(f"Verifying {len(machines)} areas against {base}\n")
    for machine_id, machine_data in sorted(machines.items()):
        motors = list(machine_data.get("motors", {}).keys())
        try:
            result = post_bulk(base, machine_id, motors)
            inserted = result.get("inserted_count", 0)
            expected = result.get("expected_count", len(motors))
            if inserted != len(motors) or inserted != expected:
                print(f"FAIL {machine_id}: inserted {inserted}/{len(motors)}")
                print(f"      errors: {result.get('errors')}")
                failed += 1
            else:
                print(f"OK   {machine_id}: {inserted} motors")
                ok += 1
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"FAIL {machine_id}: HTTP {exc.code} — {body[:300]}")
            failed += 1
        except Exception as exc:
            print(f"FAIL {machine_id}: {exc}")
            failed += 1

    print(f"\nDone: {ok} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
