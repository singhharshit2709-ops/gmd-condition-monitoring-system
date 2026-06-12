"""
Shared pytest fixtures for GMD dashboard QA automation (Phase 1).

Dependency injection:
  FastAPI's app.dependency_overrides replaces routes.dashboard.get_sheets_service
  so dashboard endpoints read from MockGMDGoogleSheetsService instead of live Sheets.
"""

from __future__ import annotations

from typing import Callable, List

import pytest
from fastapi.testclient import TestClient

from routes import dashboard as dashboard_module
from routes.dashboard import get_sheets_service
from routes.v2_preview import get_drive_media_service
from server import app
from tests.fixtures.mock_sheets_service import MockGMDGoogleSheetsService
from tests.fixtures.sheet_data import (
    build_data_set_a,
    build_data_set_b,
    build_data_set_c,
    build_data_set_d,
    build_data_set_e,
    build_data_set_f,
    build_data_set_g,
)

from gmd_config_v2 import get_total_equipment_count

CONFIGURED_EQUIPMENT_TOTAL = get_total_equipment_count()


def reset_dashboard_state() -> None:
    """Clear dashboard API cache, acknowledged alarms, and sheets service LRU cache."""
    for key in dashboard_module._dashboard_cache:
        dashboard_module._cache_invalidate(key)
    dashboard_module._acknowledged_alarm_ids.clear()
    get_sheets_service.cache_clear()


def apply_mock_sheets(data_rows: List[List[str]]) -> MockGMDGoogleSheetsService:
    """Register a mock Sheets service and reset dashboard state."""
    mock = MockGMDGoogleSheetsService(data_rows)
    app.dependency_overrides[get_sheets_service] = lambda: mock
    reset_dashboard_state()
    return mock


@pytest.fixture(autouse=True)
def _isolate_dashboard_state():
    """Reset caches and dependency overrides before and after every test."""
    app.dependency_overrides.clear()
    reset_dashboard_state()
    get_drive_media_service.cache_clear()
    yield
    app.dependency_overrides.clear()
    reset_dashboard_state()
    get_drive_media_service.cache_clear()


@pytest.fixture
def api_client() -> TestClient:
    """FastAPI TestClient bound to the application under test."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_sheets_factory() -> Callable[[List[List[str]]], MockGMDGoogleSheetsService]:
    """Factory to attach a data set to the app before API calls."""

    def _factory(data_rows: List[List[str]]) -> MockGMDGoogleSheetsService:
        return apply_mock_sheets(data_rows)

    return _factory


# ── DATA-SET row fixtures (no header) ────────────────────────────────────────

@pytest.fixture
def data_set_a_rows() -> List[List[str]]:
    return build_data_set_a()


@pytest.fixture
def data_set_b_rows() -> List[List[str]]:
    return build_data_set_b()


@pytest.fixture
def data_set_c_rows() -> List[List[str]]:
    return build_data_set_c()


@pytest.fixture
def data_set_d_rows() -> List[List[str]]:
    return build_data_set_d()


@pytest.fixture
def data_set_e_rows() -> List[List[str]]:
    return build_data_set_e()


@pytest.fixture
def data_set_f_rows() -> List[List[str]]:
    return build_data_set_f()


@pytest.fixture
def data_set_g_rows() -> List[List[str]]:
    return build_data_set_g()


# ── API client + data set combinations ───────────────────────────────────────

@pytest.fixture
def client_data_set_a(api_client: TestClient, data_set_a_rows: List[List[str]]) -> TestClient:
    apply_mock_sheets(data_set_a_rows)
    return api_client


@pytest.fixture
def client_data_set_b(api_client: TestClient, data_set_b_rows: List[List[str]]) -> TestClient:
    apply_mock_sheets(data_set_b_rows)
    return api_client


@pytest.fixture
def client_data_set_c(api_client: TestClient, data_set_c_rows: List[List[str]]) -> TestClient:
    apply_mock_sheets(data_set_c_rows)
    return api_client


@pytest.fixture
def client_data_set_d(api_client: TestClient, data_set_d_rows: List[List[str]]) -> TestClient:
    apply_mock_sheets(data_set_d_rows)
    return api_client


@pytest.fixture
def client_data_set_e(api_client: TestClient, data_set_e_rows: List[List[str]]) -> TestClient:
    apply_mock_sheets(data_set_e_rows)
    return api_client


@pytest.fixture
def client_data_set_f(api_client: TestClient, data_set_f_rows: List[List[str]]) -> TestClient:
    apply_mock_sheets(data_set_f_rows)
    return api_client


@pytest.fixture
def client_data_set_g(api_client: TestClient, data_set_g_rows: List[List[str]]) -> TestClient:
    apply_mock_sheets(data_set_g_rows)
    return api_client


# ── Helpers ──────────────────────────────────────────────────────────────────

def find_mcb1_health(health_payload: list) -> dict:
    """Return the equipment-health record for MCB-1."""
    for record in health_payload:
        if record.get("equipment") == "MCB-1":
            return record
    raise AssertionError("MCB-1 not found in equipment-health response")


def find_mcb1_alarms(alarms_payload: list) -> list:
    """Return all active-alarm records for MCB-1."""
    return [alarm for alarm in alarms_payload if alarm.get("equipment") == "MCB-1"]
