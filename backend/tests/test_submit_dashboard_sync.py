"""End-to-end submit → dashboard sync tests."""

from __future__ import annotations

from routes.dashboard import get_sheets_service, invalidate_all_dashboard_cache
from routes.v2_preview import get_drive_media_service
from server import app
from tests.conftest import apply_mock_sheets, reset_dashboard_state
from tests.fixtures.mock_sheets_service import MockGMDGoogleSheetsService
from tests.test_v2_submit import _apply_mocks, _full_submit_payload


class TestSubmitDashboardSync:
    def test_submit_invalidates_dashboard_cache_and_recent_readings(self, api_client):
        reset_dashboard_state()
        mock = MockGMDGoogleSheetsService([])
        _apply_mocks(mock)

        summary_before = api_client.get("/dashboard/summary")
        assert summary_before.status_code == 200

        submit = api_client.post("/api/v2/submit", json=_full_submit_payload())
        assert submit.status_code == 201
        assert submit.json()["reading_count"] > 0

        recent = api_client.get("/dashboard/recent-readings", params={"limit": 10})
        assert recent.status_code == 200
        rows = recent.json()
        assert len(rows) >= 1
        assert rows[0]["equipment"] == "MCB-1"
        assert rows[0]["verified_by"] == "Test Technician"

    def test_zero_rows_appended_returns_error(self, api_client, monkeypatch):
        mock = MockGMDGoogleSheetsService([])
        _apply_mocks(mock)

        def _fake_append(**kwargs):
            return {
                "success": True,
                "rows_appended": 0,
                "timestamp": "",
                "submission_id": "bad",
            }

        monkeypatch.setattr(mock, "append_v2_readings", _fake_append)

        response = api_client.post("/api/v2/submit", json=_full_submit_payload())
        assert response.status_code == 500
        assert "no rows were appended" in response.json()["detail"].lower()
