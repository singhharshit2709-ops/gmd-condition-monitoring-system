"""
TC-ACK-01 — Alarm Acknowledgement API.

Integration test via FastAPI TestClient with mocked Google Sheets data.
"""

from __future__ import annotations

import pytest

from tests.conftest import find_mcb1_alarms


class TestTcAck01AcknowledgeApiAcceptsValidId:
    """TC-ACK-01: POST /dashboard/acknowledge-alarm/{id} returns 200 and status ok."""

    def test_acknowledge_valid_alarm_id(self, client_data_set_b):
        alarms_response = client_data_set_b.get("/dashboard/active-alarms")
        assert alarms_response.status_code == 200
        alarms = alarms_response.json()
        mcb1_alarms = find_mcb1_alarms(alarms)
        assert len(mcb1_alarms) == 1
        alarm_id = mcb1_alarms[0]["id"]

        ack_response = client_data_set_b.post(f"/dashboard/acknowledge-alarm/{alarm_id}")
        assert ack_response.status_code == 200
        body = ack_response.json()
        assert body == {"status": "ok", "id": alarm_id}

    def test_acknowledged_alarm_removed_from_active_list(self, client_data_set_b):
        alarm_id = find_mcb1_alarms(
            client_data_set_b.get("/dashboard/active-alarms").json()
        )[0]["id"]

        client_data_set_b.post(f"/dashboard/acknowledge-alarm/{alarm_id}")

        remaining = client_data_set_b.get("/dashboard/active-alarms").json()
        remaining_ids = {alarm["id"] for alarm in remaining}
        assert alarm_id not in remaining_ids
