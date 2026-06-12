"""Trends API tests — canonical sheet parsing."""

from __future__ import annotations


class TestTrendsReadings:
    def test_returns_numeric_readings_with_canonical_fields(self, client_data_set_a):
        response = client_data_set_a.get("/trends/readings", params={"equipment": "MCB-1"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        row = data[0]
        assert "timestamp" in row
        assert "parameter" in row
        assert "parameter_display_name" in row
        assert "equipment" in row
        assert "value" in row
        assert isinstance(row["value"], float)

    def test_filters_by_parameter(self, client_data_set_a):
        response = client_data_set_a.get(
            "/trends/readings",
            params={"equipment": "MCB-1", "parameter": "temperature"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(item["parameter"] == "temperature" for item in data)

    def test_window_filter(self, client_data_set_a):
        response = client_data_set_a.get(
            "/trends/readings",
            params={"equipment": "MCB-1", "window": 30},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
