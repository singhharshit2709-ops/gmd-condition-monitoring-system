"""
TC-ALM-01 through TC-ALM-04 — Active Alarms API.

Integration tests via FastAPI TestClient with mocked Google Sheets data.
"""

from __future__ import annotations

import pytest

from routes.dashboard import _alarm_id
from tests.conftest import find_mcb1_alarms


class TestTcAlm01NoActiveAlarms:
    """TC-ALM-01: No active alarms when all parameters NORMAL (DATA-SET-A)."""

    def test_active_alarms_empty(self, client_data_set_a):
        response = client_data_set_a.get("/dashboard/active-alarms")
        assert response.status_code == 200
        assert response.json() == []


class TestTcAlm02OneWarningAlarm:
    """TC-ALM-02: One WARNING produces one alarm record (DATA-SET-B)."""

    def test_one_mcb1_alarm(self, client_data_set_b):
        response = client_data_set_b.get("/dashboard/active-alarms")
        assert response.status_code == 200
        alarms = response.json()
        mcb1_alarms = find_mcb1_alarms(alarms)
        assert len(mcb1_alarms) == 1

    def test_alarm_fields_and_id(self, client_data_set_b):
        alarms = client_data_set_b.get("/dashboard/active-alarms").json()
        alarm = find_mcb1_alarms(alarms)[0]
        assert alarm["parameter"] == "current"
        assert alarm["status"] == "WARNING"
        assert alarm["id"]
        assert len(alarm["id"]) == 16

    def test_alarm_id_is_stable(self, client_data_set_b):
        alarms = client_data_set_b.get("/dashboard/active-alarms").json()
        alarm = find_mcb1_alarms(alarms)[0]
        expected_id = _alarm_id(alarm)
        assert alarm["id"] == expected_id


class TestTcAlm03WarningAndAlarmTwoCards:
    """TC-ALM-03: WARNING + ALARM produces two parameter-level records (DATA-SET-D)."""

    def test_two_mcb1_alarms(self, client_data_set_d):
        response = client_data_set_d.get("/dashboard/active-alarms")
        assert response.status_code == 200
        mcb1_alarms = find_mcb1_alarms(response.json())
        assert len(mcb1_alarms) == 2

    def test_parameters_and_statuses(self, client_data_set_d):
        alarms = client_data_set_d.get("/dashboard/active-alarms").json()
        mcb1_alarms = find_mcb1_alarms(alarms)
        by_param = {a["parameter"]: a for a in mcb1_alarms}
        assert set(by_param) == {"current", "vertical_vibration"}
        assert by_param["current"]["status"] == "WARNING"
        assert by_param["vertical_vibration"]["status"] == "ALARM"
        for alarm in mcb1_alarms:
            assert alarm["id"]


class TestTcAlm04ThreeAlarmParameters:
    """TC-ALM-04: Three ALARM parameters produce three records (DATA-SET-E)."""

    def test_three_mcb1_alarms(self, client_data_set_e):
        response = client_data_set_e.get("/dashboard/active-alarms")
        assert response.status_code == 200
        mcb1_alarms = find_mcb1_alarms(response.json())
        assert len(mcb1_alarms) == 3

    def test_all_parameters_alarm_status(self, client_data_set_e):
        alarms = client_data_set_e.get("/dashboard/active-alarms").json()
        mcb1_alarms = find_mcb1_alarms(alarms)
        params = {a["parameter"] for a in mcb1_alarms}
        assert params == {"temperature", "current", "vertical_vibration"}
        for alarm in mcb1_alarms:
            assert alarm["status"] == "ALARM"
            assert alarm["id"]
