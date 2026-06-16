"""Tests for area worksheet registry and routing."""

from __future__ import annotations

from services.sheets_area_registry import (
    get_area_worksheet_names,
    resolve_area_worksheet,
)


class TestSheetsAreaRegistry:
    def test_area_worksheet_names_include_virtual_dm_bucket(self):
        names = get_area_worksheet_names()
        assert "A Tank" in names
        assert "E Tank" in names
        assert "G Tank" in names
        assert "K Tank" in names
        assert "Utility Area" in names
        assert "DM Water Electrode Cooling" in names

    def test_dm_categories_route_to_virtual_worksheet(self):
        worksheet = resolve_area_worksheet(
            area_tank="A Tank",
            category="DM Water Electrode Cooling",
            equipment="A Tank Electrode Cooling",
        )
        assert worksheet == "DM Water Electrode Cooling"

    def test_blower_routes_to_physical_area(self):
        worksheet = resolve_area_worksheet(
            area_tank="G Tank",
            category="Blowers",
            equipment="MCB-3",
        )
        assert worksheet == "G Tank"

    def test_utility_area_routing(self):
        worksheet = resolve_area_worksheet(
            area_tank="Utility Area",
            category="Utility Area Monitoring",
            equipment="",
        )
        assert worksheet == "Utility Area"

    def test_equipment_lookup_fallback(self):
        worksheet = resolve_area_worksheet(
            area_tank="",
            category="Blowers",
            equipment="MCB-1",
        )
        assert worksheet == "A Tank"
