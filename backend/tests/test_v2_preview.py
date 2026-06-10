"""Tests for POST /api/v2/preview — validation only, no persistence."""

from __future__ import annotations

from gmd_config_v2 import collect_equipment_parameters, find_equipment_in_config, load_gmd_config_v2

MCB1_CATEGORY = "Blowers"
MCB1_EQUIPMENT = "MCB-1"
PREVIEW_URL = "/api/v2/preview"


def _mcb1_parameter_keys() -> list[str]:
    config = load_gmd_config_v2()
    located = find_equipment_in_config(MCB1_EQUIPMENT, MCB1_CATEGORY, config)
    assert located is not None
    _, _, equipment = located
    return [param["key"] for param in collect_equipment_parameters(equipment)]


def _full_mcb1_readings() -> dict[str, float]:
    return {key: 1.0 for key in _mcb1_parameter_keys()}


class TestV2PreviewValidation:
    def test_valid_full_submission(self, api_client):
        payload = {
            "category": MCB1_CATEGORY,
            "equipment": MCB1_EQUIPMENT,
            "readings": _full_mcb1_readings(),
        }
        response = api_client.post(PREVIEW_URL, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["expected_readings"] == 16
        assert data["received_readings"] == 16
        assert data["missing_parameters"] == []
        assert data["invalid_parameters"] == []
        assert "passed" in data["validation_message"].lower()

    def test_unknown_equipment(self, api_client):
        response = api_client.post(
            PREVIEW_URL,
            json={
                "category": MCB1_CATEGORY,
                "equipment": "MCB-99",
                "readings": {},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["expected_readings"] == 0
        assert "not found" in data["validation_message"].lower()

    def test_wrong_category(self, api_client):
        response = api_client.post(
            PREVIEW_URL,
            json={
                "category": "Cooling Tower",
                "equipment": MCB1_EQUIPMENT,
                "readings": {},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "category" in data["validation_message"].lower()

    def test_missing_required_parameters(self, api_client):
        keys = _mcb1_parameter_keys()
        partial = {keys[0]: 2.5}
        response = api_client.post(
            PREVIEW_URL,
            json={
                "category": MCB1_CATEGORY,
                "equipment": MCB1_EQUIPMENT,
                "readings": partial,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["received_readings"] == 1
        assert data["expected_readings"] == 16
        assert len(data["missing_parameters"]) == 15
        missing_keys = {item["key"] for item in data["missing_parameters"]}
        assert keys[0] not in missing_keys

    def test_unexpected_parameter_key(self, api_client):
        readings = _full_mcb1_readings()
        readings["not_a_real_parameter"] = 3.0
        response = api_client.post(
            PREVIEW_URL,
            json={
                "category": MCB1_CATEGORY,
                "equipment": MCB1_EQUIPMENT,
                "readings": readings,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        invalid_keys = {item["key"] for item in data["invalid_parameters"]}
        assert "not_a_real_parameter" in invalid_keys

    def test_non_numeric_value(self, api_client):
        readings = _full_mcb1_readings()
        readings["blower_drive_end_vertical"] = "abc"
        response = api_client.post(
            PREVIEW_URL,
            json={
                "category": MCB1_CATEGORY,
                "equipment": MCB1_EQUIPMENT,
                "readings": readings,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        invalid = {item["key"]: item["reason"] for item in data["invalid_parameters"]}
        assert "blower_drive_end_vertical" in invalid
        assert "numeric" in invalid["blower_drive_end_vertical"].lower()

    def test_string_numeric_value_accepted(self, api_client):
        readings = _full_mcb1_readings()
        readings["blower_drive_end_vertical"] = " 2.75 "
        response = api_client.post(
            PREVIEW_URL,
            json={
                "category": MCB1_CATEGORY,
                "equipment": MCB1_EQUIPMENT,
                "readings": readings,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["received_readings"] == 16

    def test_empty_body_rejected(self, api_client):
        response = api_client.post(PREVIEW_URL, json={})
        assert response.status_code == 422
