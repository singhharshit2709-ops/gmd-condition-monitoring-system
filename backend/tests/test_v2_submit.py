"""Tests for POST /api/v2/submit — validation reuse and Google Sheets persistence."""

from __future__ import annotations

import base64

from gmd_config_v2 import collect_equipment_parameters, find_equipment_in_config, load_gmd_config_v2
from routes.dashboard import get_sheets_service
from routes.v2_preview import get_drive_media_service
from server import app
from tests.fixtures.mock_sheets_service import (
    MockGMDGoogleSheetsService,
    MockGoogleDriveMediaService,
)

MCB1_CATEGORY = "Blowers"
MCB1_EQUIPMENT = "MCB-1"
SUBMIT_URL = "/api/v2/submit"
SAMPLE_IMAGE_DATA_URL = (
    "data:image/jpeg;base64,"
    + base64.b64encode(b"fake-jpeg-bytes").decode("ascii")
)


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
        "area_tank": "A Tank",
        "tag_no": "",
    }
    payload.update(overrides)
    return payload


def _apply_mocks(
    mock_sheets: MockGMDGoogleSheetsService,
    mock_drive: MockGoogleDriveMediaService | None = None,
) -> None:
    app.dependency_overrides[get_sheets_service] = lambda: mock_sheets
    if mock_drive is not None:
        app.dependency_overrides[get_drive_media_service] = lambda: mock_drive
    get_drive_media_service.cache_clear()


class TestV2Submit:
    def test_successful_submission(self, api_client):
        mock = MockGMDGoogleSheetsService([])
        _apply_mocks(mock)

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
        assert call["area_tank"] == "A Tank"
        assert call["tag_no"] == ""
        assert call["media_name"] == ""
        assert call["media_type"] == ""
        assert call["media_url"] == ""
        assert "blower_drive_end_vertical" in call["parameter_locations"]

    def test_submission_with_media_persists_drive_url(self, api_client):
        mock_sheets = MockGMDGoogleSheetsService([])
        mock_drive = MockGoogleDriveMediaService(
            media_url="https://drive.google.com/file/d/test-file/view"
        )
        _apply_mocks(mock_sheets, mock_drive)

        response = api_client.post(
            SUBMIT_URL,
            json=_full_submit_payload(
                media_name="field-photo.jpg",
                media_type="image/jpeg",
                media_data=SAMPLE_IMAGE_DATA_URL,
            ),
        )
        assert response.status_code == 201
        data = response.json()
        assert data.get("submission_id")

        assert len(mock_drive.upload_calls) == 1
        upload = mock_drive.upload_calls[0]
        assert upload["filename"] == "field-photo.jpg"
        assert upload["mime_type"] == "image/jpeg"
        assert upload["equipment"] == MCB1_EQUIPMENT

        call = mock_sheets.append_v2_calls[0]
        assert call["media_name"] == "field-photo.jpg"
        assert call["media_type"] == "image/jpeg"
        assert call["media_url"] == "https://drive.google.com/file/d/test-file/view"

    def test_media_upload_failure_returns_clear_error(self, api_client):
        mock_sheets = MockGMDGoogleSheetsService([])
        mock_drive = MockGoogleDriveMediaService(
            upload_raises=RuntimeError("Drive quota exceeded")
        )
        _apply_mocks(mock_sheets, mock_drive)

        response = api_client.post(
            SUBMIT_URL,
            json=_full_submit_payload(
                media_name="field-photo.jpg",
                media_type="image/jpeg",
                media_data=SAMPLE_IMAGE_DATA_URL,
            ),
        )
        assert response.status_code == 500
        assert "Media upload failed" in response.json()["detail"]
        assert mock_sheets.append_v2_calls == []

    def test_validation_failure_returns_preview_response(self, api_client):
        mock = MockGMDGoogleSheetsService([])
        _apply_mocks(mock)

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
        _apply_mocks(mock)

        response = api_client.post(SUBMIT_URL, json=_full_submit_payload())
        assert response.status_code == 500
        data = response.json()
        assert "Google Sheets write failed" in data["detail"]

    def test_google_sheets_write_failure_after_media_upload(self, api_client):
        mock_sheets = MockGMDGoogleSheetsService(
            [],
            append_v2_raises=RuntimeError("Spreadsheet unavailable"),
        )
        mock_drive = MockGoogleDriveMediaService(
            media_url="https://drive.google.com/file/d/uploaded/view"
        )
        _apply_mocks(mock_sheets, mock_drive)

        response = api_client.post(
            SUBMIT_URL,
            json=_full_submit_payload(
                media_name="verify.jpg",
                media_type="image/jpeg",
                media_data=SAMPLE_IMAGE_DATA_URL,
            ),
        )
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "Media was uploaded to Google Drive" in detail
        assert "https://drive.google.com/file/d/uploaded/view" in detail
        assert "Google Sheets persistence failed" in detail
