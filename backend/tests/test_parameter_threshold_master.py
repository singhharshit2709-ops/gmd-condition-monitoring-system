"""Tests for the parameter & threshold master export."""

from __future__ import annotations

import csv
from pathlib import Path

from gmd_config_v2 import collect_active_equipment
from scripts.export_parameter_threshold_master import (
    MASTER_HEADERS,
    collect_master_rows,
    export_all,
)

EXPECTED_AREAS = {
    "A Tank",
    "E Tank",
    "G Tank",
    "K Tank",
    "Utility Area",
}

PROVISIONAL_BOILERPLATE = "PROVISIONAL — pending user-department approval"


class TestParameterThresholdMasterExport:
    def test_covers_all_configured_areas(self):
        rows = collect_master_rows()
        areas = {row.area_tank for row in rows}
        assert EXPECTED_AREAS.issubset(areas)

    def test_covers_all_equipment_instances(self):
        rows = collect_master_rows()
        exported_slots = {(r.area_tank, r.category, r.equipment, r.tag_no) for r in rows}
        assert len(exported_slots) == 87
        assert len(collect_active_equipment()) == 87

    def test_required_columns_present(self, tmp_path: Path):
        csv_path = tmp_path / "master.csv"
        xlsx_path = tmp_path / "master.xlsx"
        validation_path = tmp_path / "validation.txt"
        summary = export_all(csv_path, xlsx_path, validation_path)

        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            headers = next(reader)
            data_rows = list(reader)

        assert headers == MASTER_HEADERS
        assert len(data_rows) == 1002
        assert summary["total_rows"] == 1002
        assert all(len(row) == len(MASTER_HEADERS) for row in data_rows)
        # Final Normal, Warning, Alarm blank
        assert all(row[10] == "" and row[11] == "" and row[12] == "" for row in data_rows)
        assert all(row[13] == "" and row[14] == "" and row[15] == "" for row in data_rows)
        assert xlsx_path.exists()
        assert validation_path.exists()

    def test_no_repetitive_provisional_remarks(self):
        rows = collect_master_rows()
        for row in rows:
            assert PROVISIONAL_BOILERPLATE not in row.remarks
            assert "Not approved for production classification" not in row.remarks

    def test_mcb1_has_v2_parameter_keys(self):
        rows = collect_master_rows()
        mcb1_keys = {
            row.parameter_key
            for row in rows
            if row.equipment == "MCB-1" and row.category == "Blowers"
        }
        assert "blower_drive_end_vertical" in mcb1_keys

    def test_utility_lp_entries_are_distinct(self):
        rows = collect_master_rows()
        lp_rows = [
            row
            for row in rows
            if row.area_tank == "Utility Area" and row.tag_no == "LP"
        ]
        equipment_labels = {(row.equipment, row.tag_no) for row in lp_rows}
        assert ("LP (Air Dryer)", "LP") in equipment_labels
        assert ("LP (Cooling Tower Pump)", "LP") in equipment_labels

    def test_config_source_is_v2_json(self):
        rows = collect_master_rows()
        assert len(rows) == 1002
        assert "MCB-1" in {row.equipment for row in rows}
        assert "Compressor C1" not in {row.equipment for row in rows}

    def test_proposed_values_preserved_for_mcb1_vertical(self):
        rows = collect_master_rows()
        match = next(
            r
            for r in rows
            if r.equipment == "MCB-1"
            and r.parameter_key == "blower_drive_end_vertical"
        )
        assert match.proposed_normal_limit == "6"
        assert match.proposed_warning_limit == "10"
        assert match.proposed_alarm_limit == "10"

    def test_proposed_normal_blank_when_not_in_config(self):
        rows = collect_master_rows()
        without_thresholds = [
            row for row in rows if not row.proposed_normal_limit and not row.proposed_warning_limit
        ]
        assert len(without_thresholds) > 0
