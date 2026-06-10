"""Tests for POST /api/v2/submit — validation reuse and Google Sheets persistence."""

from __future__ import annotations

from gmd_config_v2 import collect_equipment_parameters, find_equipment_in_config, load_gmd_config_v2
from routes.dashboard import get_sheets_service
from server import app
from tests.fixtures.mock_sheets_service import MockGMDGoogleSheetsService

MCB1_CATEGORY = "Blowers"
MCB1_EQUIPMENT = "MCB-1"
SUBMIT_URL = "/api/v2/submit"


def _mcb1_parameter_keys() -> list[str]:
    config = load_gmd_config_v2()
    located = find_equipment_in_config(MCB1_EQUIPMENT, MCB1_CATEGORY, config)
    assert located is not None
    _, _, equipment = located
    return [param["key"] for param in collect_equipment_parameters(equipment)]


def _full_mcb1_readings() -> dict[str, float]:
    return {key: 1.0 for key in _mcb1_parameter_keys()}


def _full_submit_payload(**overrides) -> dict:
    payload = {
        "category": MCB1_CATEGORY,
        "equipment": MCB1_EQUIPMENT,
        "readings": _full_mcb1_readings(),
        "verified_by": "Test Technician",
        "remarks": "V2 pilot test",
        "entry_source": "Web",
    }
    payload.update(overrides)
    return payload


class TestV2Submit:
    def test_successful_submission(self, api_client):
        mock = MockGMDGoogleSheetsService([])
        app.dependency_overrides[get_sheets_service] = lambda: mock

        response = api_client.post(SUBMIT_URL, json=_full_submit_payload())
        assert response.status_code == 201
        data = response.json()

        assert data["success"] is True
        assert data["equipment"] == MCB1_EQUIPMENT
        assert data["category"] == MCB1_CATEGORY
        assert data["reading_count"] == 16
        assert data["submitted_at"] == "2026-06-10 12:00:00"
        assert "successfully submitted" in data["message"].lower()

        assert len(mock.append_v2_calls) == 1
        call = mock.append_v2_calls[0]
        assert call["category"] == MCB1_CATEGORY
        assert call["equipment"] == MCB1_EQUIPMENT
        assert len(call["readings"]) == 16
        assert call["verified_by"] == "Test Technician"
        assert call["entry_source"] == "Web"
        assert "blower_drive_end_vertical" in call["parameter_locations"]

    def test_validation_failure_returns_preview_response(self, api_client):
        mock = MockGMDGoogleSheetsService([])
        app.dependency_overrides[get_sheets_service] = lambda: mock

        keys = _mcb1_parameter_keys()
        response = api_client.post(
            SUBMIT_URL,
            json=_full_submit_payload(readings={keys[0]: 2.5}),
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert data["expected_readings"] == 16
        assert data["received_readings"] == 1
        assert len(data["missing_parameters"]) == 15
        assert "validation_message" in data
        assert mock.append_v2_calls == []

    def test_google_sheets_write_failure(self, api_client):
        mock = MockGMDGoogleSheetsService(
            [],
            append_v2_raises=RuntimeError("Spreadsheet unavailable"),
        )
        app.dependency_overrides[get_sheets_service] = lambda: mock

        response = api_client.post(SUBMIT_URL, json=_full_submit_payload())
        assert response.status_code == 500
        data = response.json()
        assert "Google Sheets write failed" in data["detail"]
