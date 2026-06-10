# GMD Dashboard — Phase 1 QA Automation Tests

Automates **17 test cases** from the QA Automation Plan using pytest and FastAPI `TestClient`. No live Google Sheets connection is required.

## Directory structure

```
backend/tests/
├── README.md                 # This file
├── conftest.py               # Fixtures, mock DI, dashboard state reset
├── fixtures/
│   ├── __init__.py
│   ├── sheet_data.py         # DATA-SET-A through DATA-SET-G builders
│   └── mock_sheets_service.py
├── test_tc_agg.py            # TC-AGG-01 – TC-AGG-07 (unit)
├── test_tc_sum.py            # TC-SUM-01 – TC-SUM-04 (API)
├── test_tc_alm.py            # TC-ALM-01 – TC-ALM-04 (API)
├── test_tc_eh.py             # TC-EH-01 – TC-EH-03 (API)
└── test_tc_ack.py            # TC-ACK-01 (API)
```

## Setup

```powershell
cd backend
pip install -r requirements-dev.txt
```

## Execution commands

Run from the `backend/` directory. On Windows, use `python -m pytest` if `pytest` is not on PATH.

```powershell
cd backend

# Run all Phase 1 tests
python -m pytest

# Verbose with summary
python -m pytest -v --tb=short

# Run by test case file
python -m pytest tests/test_tc_agg.py
python -m pytest tests/test_tc_sum.py
python -m pytest tests/test_tc_alm.py
python -m pytest tests/test_tc_eh.py
python -m pytest tests/test_tc_ack.py

# Run a single test case class
python -m pytest tests/test_tc_agg.py::TestTcAgg07RegressionNewerNormalDoesNotHideAlarm

# Run with coverage (optional: pip install pytest-cov)
python -m pytest --cov=routes.dashboard --cov-report=term-missing

# Quiet pass/fail only
python -m pytest -q
```

## Test case mapping

| Test file        | QA IDs              | Layer                          |
|------------------|---------------------|--------------------------------|
| `test_tc_agg.py` | TC-AGG-01 – 07      | Unit (`get_equipment_status_aggregates`) |
| `test_tc_sum.py` | TC-SUM-01 – 04      | API (`GET /dashboard/summary`) |
| `test_tc_alm.py` | TC-ALM-01 – 04      | API (`GET /dashboard/active-alarms`) |
| `test_tc_eh.py`  | TC-EH-01 – 03       | API (`GET /dashboard/equipment-health`) |
| `test_tc_ack.py` | TC-ACK-01           | API (`POST /dashboard/acknowledge-alarm/{id}`) |

## Dependency injection

Tests override `routes.dashboard.get_sheets_service` via `app.dependency_overrides` so endpoints read from `MockGMDGoogleSheetsService`. See `conftest.py` for `apply_mock_sheets()` and `reset_dashboard_state()`.

No production code changes are required for Phase 1.
