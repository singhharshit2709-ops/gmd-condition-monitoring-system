"""
TC-AGG-01 through TC-AGG-07 — Equipment Status Aggregation.

Unit tests call get_equipment_status_aggregates() directly with fixture rows.
No live Google Sheets or HTTP requests.
"""

from __future__ import annotations

import pytest

from routes.dashboard import STATUS_ALARM, STATUS_NORMAL, STATUS_WARNING, get_equipment_status_aggregates
from tests.fixtures.sheet_data import (
    DATA_SET_A,
    DATA_SET_B,
    DATA_SET_C,
    DATA_SET_D,
    DATA_SET_E,
    DATA_SET_F,
    DATA_SET_G,
    TS_PRIMARY,
)


def _mcb1_aggregate(rows):
    aggregates = get_equipment_status_aggregates(rows)
    assert "MCB-1" in aggregates, "MCB-1 should appear in aggregates"
    return aggregates["MCB-1"]


class TestTcAgg01AllNormal:
    """TC-AGG-01: All latest parameters NORMAL → equipment NORMAL."""

    def test_worst_status_is_normal(self, data_set_a_rows):
        aggregate = _mcb1_aggregate(data_set_a_rows)
        assert aggregate["worst_status"] == STATUS_NORMAL

    def test_module_constant_data_set(self):
        aggregate = _mcb1_aggregate(DATA_SET_A)
        assert aggregate["worst_status"] == STATUS_NORMAL


class TestTcAgg02OneWarning:
    """TC-AGG-02: One WARNING parameter elevates equipment to WARNING."""

    def test_worst_status_is_warning(self, data_set_b_rows):
        aggregate = _mcb1_aggregate(data_set_b_rows)
        assert aggregate["worst_status"] == STATUS_WARNING

    def test_representative_parameter_is_current(self, data_set_b_rows):
        aggregate = _mcb1_aggregate(data_set_b_rows)
        representative = aggregate["representative"]
        assert representative is not None
        assert representative["parameter"] == "current"
        assert representative["status"] == STATUS_WARNING


class TestTcAgg03OneAlarm:
    """TC-AGG-03: One ALARM parameter elevates equipment to ALARM."""

    def test_worst_status_is_alarm_not_normal(self, data_set_c_rows):
        aggregate = _mcb1_aggregate(data_set_c_rows)
        assert aggregate["worst_status"] == STATUS_ALARM
        assert aggregate["worst_status"] != STATUS_NORMAL

    def test_representative_parameter_is_vertical_vibration(self, data_set_c_rows):
        aggregate = _mcb1_aggregate(data_set_c_rows)
        assert aggregate["representative"]["parameter"] == "vertical_vibration"


class TestTcAgg04WarningAndAlarmResolvesToAlarm:
    """TC-AGG-04: WARNING + ALARM on same equipment resolves to ALARM."""

    def test_worst_status_is_alarm_not_warning(self, data_set_d_rows):
        aggregate = _mcb1_aggregate(data_set_d_rows)
        assert aggregate["worst_status"] == STATUS_ALARM
        assert aggregate["worst_status"] != STATUS_WARNING

    def test_representative_is_highest_severity_alarm(self, data_set_d_rows):
        aggregate = _mcb1_aggregate(data_set_d_rows)
        assert aggregate["representative"]["parameter"] == "vertical_vibration"
        assert aggregate["representative"]["status"] == STATUS_ALARM


class TestTcAgg05MultipleAlarms:
    """TC-AGG-05: Multiple ALARM parameters still yield equipment ALARM."""

    def test_worst_status_remains_alarm(self, data_set_e_rows):
        aggregate = _mcb1_aggregate(data_set_e_rows)
        assert aggregate["worst_status"] == STATUS_ALARM

    def test_all_three_parameters_present(self, data_set_e_rows):
        aggregate = _mcb1_aggregate(data_set_e_rows)
        params = set(aggregate["parameter_rows"].keys())
        assert params == {"temperature", "current", "vertical_vibration"}
        for record in aggregate["parameter_rows"].values():
            assert record["status"] == STATUS_ALARM


class TestTcAgg06MissingParameter:
    """TC-AGG-06: Missing parameters do not break aggregation."""

    def test_worst_status_warning_from_available_params(self, data_set_f_rows):
        aggregate = _mcb1_aggregate(data_set_f_rows)
        assert aggregate["worst_status"] == STATUS_WARNING

    def test_vertical_vibration_not_present(self, data_set_f_rows):
        aggregate = _mcb1_aggregate(data_set_f_rows)
        assert "vertical_vibration" not in aggregate["parameter_rows"]

    def test_representative_parameter_is_current(self, data_set_f_rows):
        aggregate = _mcb1_aggregate(data_set_f_rows)
        assert aggregate["representative"]["parameter"] == "current"


class TestTcAgg07RegressionNewerNormalDoesNotHideAlarm:
    """TC-AGG-07: Newer NORMAL rows must not hide older ALARM parameter."""

    def test_worst_status_remains_alarm(self, data_set_g_rows):
        aggregate = _mcb1_aggregate(data_set_g_rows)
        assert aggregate["worst_status"] == STATUS_ALARM

    def test_vibration_alarm_persists_at_earlier_timestamp(self, data_set_g_rows):
        aggregate = _mcb1_aggregate(data_set_g_rows)
        vibration = aggregate["parameter_rows"]["vertical_vibration"]
        assert vibration["status"] == STATUS_ALARM
        assert vibration["timestamp"] == "2026-06-08 09:00:00"

    def test_latest_timestamp_reflects_most_recent_reading(self, data_set_g_rows):
        aggregate = _mcb1_aggregate(data_set_g_rows)
        latest = aggregate["_parsed_timestamp"]
        assert latest is not None
        assert latest.strftime("%Y-%m-%d %H:%M:%S") == TS_PRIMARY
