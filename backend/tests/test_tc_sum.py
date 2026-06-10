"""
TC-SUM-01 through TC-SUM-04 — Dashboard Summary API.

Integration tests via FastAPI TestClient with mocked Google Sheets data.
"""

from __future__ import annotations

import pytest

from tests.conftest import CONFIGURED_EQUIPMENT_TOTAL


class TestTcSum01AllNormal:
    """TC-SUM-01: Summary when MCB-1 fully NORMAL (DATA-SET-A)."""

    def test_summary_counts(self, client_data_set_a):
        response = client_data_set_a.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data == {
            "total": CONFIGURED_EQUIPMENT_TOTAL,
            "ok": CONFIGURED_EQUIPMENT_TOTAL,
            "warning": 0,
            "alarm": 0,
        }


class TestTcSum02OneWarning:
    """TC-SUM-02: Summary counts one WARNING equipment (DATA-SET-B)."""

    def test_summary_counts(self, client_data_set_b):
        response = client_data_set_b.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == CONFIGURED_EQUIPMENT_TOTAL
        assert data["warning"] == 1
        assert data["alarm"] == 0
        assert data["ok"] == CONFIGURED_EQUIPMENT_TOTAL - 1


class TestTcSum03OneAlarm:
    """TC-SUM-03: Summary counts one ALARM equipment (DATA-SET-C)."""

    def test_summary_counts(self, client_data_set_c):
        response = client_data_set_c.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == CONFIGURED_EQUIPMENT_TOTAL
        assert data["warning"] == 0
        assert data["alarm"] == 1
        assert data["ok"] == CONFIGURED_EQUIPMENT_TOTAL - 1


class TestTcSum04WarningAndAlarmCountsAsOneAlarm:
    """TC-SUM-04: WARNING + ALARM on same equipment counts as 1 alarm (DATA-SET-D)."""

    def test_no_double_count_warning_and_alarm(self, client_data_set_d):
        response = client_data_set_d.get("/dashboard/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == CONFIGURED_EQUIPMENT_TOTAL
        assert data["warning"] == 0
        assert data["alarm"] == 1
        assert data["ok"] == CONFIGURED_EQUIPMENT_TOTAL - 1
