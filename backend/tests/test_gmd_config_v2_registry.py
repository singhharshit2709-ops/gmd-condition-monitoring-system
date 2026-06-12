"""Tests for V2 equipment registry helpers."""

from __future__ import annotations

from gmd_config_v2 import (
    collect_active_equipment,
    get_equipment_count_by_area,
    get_equipment_registry,
    get_total_equipment_count,
    load_gmd_config_v2,
)


class TestGmdConfigV2Registry:
    def test_total_equipment_count_matches_registry(self):
        config = load_gmd_config_v2()
        total = get_total_equipment_count(config)
        assert total == len(collect_active_equipment(config))
        assert total == 87

    def test_equipment_by_area_totals(self):
        by_area = get_equipment_count_by_area()
        assert by_area["A Tank"] == 16
        assert by_area["E Tank"] == 13
        assert by_area["G Tank"] == 15
        assert by_area["K Tank"] == 13
        assert by_area["Utility Area"] == 30
        assert sum(by_area.values()) == 87

    def test_registry_metadata_present(self):
        registry = get_equipment_registry()
        assert registry["total_equipment"] == 87
        assert "by_category" in registry
        assert registry["by_category"]["blowers"] == 49
