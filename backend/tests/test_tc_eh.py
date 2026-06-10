"""
TC-EH-01 through TC-EH-03 — Equipment Health API.

Integration tests via FastAPI TestClient with mocked Google Sheets data.
"""

from __future__ import annotations

import pytest

from tests.conftest import find_mcb1_health


class TestTcEh01HealthWhenNormal:
    """TC-EH-01: MCB-1 health when aggregated NORMAL (DATA-SET-A)."""

    def test_latest_status_and_health_percentage(self, client_data_set_a):
        response = client_data_set_a.get("/dashboard/equipment-health")
        assert response.status_code == 200
        mcb1 = find_mcb1_health(response.json())
        assert mcb1["latest_status"] == "NORMAL"
        assert mcb1["health_percentage"] == 100.0


class TestTcEh02HealthWhenWarning:
    """TC-EH-02: MCB-1 health when aggregated WARNING (DATA-SET-B)."""

    def test_latest_status_and_health_percentage(self, client_data_set_b):
        response = client_data_set_b.get("/dashboard/equipment-health")
        assert response.status_code == 200
        mcb1 = find_mcb1_health(response.json())
        assert mcb1["latest_status"] == "WARNING"
        assert mcb1["health_percentage"] == 0.0

    def test_latest_parameter_is_current(self, client_data_set_b):
        mcb1 = find_mcb1_health(client_data_set_b.get("/dashboard/equipment-health").json())
        assert mcb1["latest_parameter"] == "current"


class TestTcEh03HealthWhenAlarm:
    """TC-EH-03: MCB-1 health when aggregated ALARM (DATA-SET-D)."""

    def test_latest_status_and_health_percentage(self, client_data_set_d):
        response = client_data_set_d.get("/dashboard/equipment-health")
        assert response.status_code == 200
        mcb1 = find_mcb1_health(response.json())
        assert mcb1["latest_status"] == "ALARM"
        assert mcb1["health_percentage"] == 0.0

    def test_latest_parameter_is_vertical_vibration(self, client_data_set_d):
        mcb1 = find_mcb1_health(client_data_set_d.get("/dashboard/equipment-health").json())
        assert mcb1["latest_parameter"] == "vertical_vibration"
