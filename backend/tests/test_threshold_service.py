"""Tests for config-driven threshold classification."""

from __future__ import annotations

import os

import pytest

from services.threshold_service import (
    ParameterThresholds,
    classify_parameter_value,
    classify_v2_parameter_status,
    is_threshold_classification_enabled,
)


class TestThresholdService:
    def test_classification_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("GMD_THRESHOLD_CLASSIFICATION_ENABLED", raising=False)
        assert is_threshold_classification_enabled() is False
        assert (
            classify_v2_parameter_status(
                value=99.0,
                equipment="MCB-1",
                category="Blowers",
                parameter_key="blower_drive_end_vertical",
            )
            == "NORMAL"
        )

    def test_higher_is_worse_classification(self):
        thresholds = ParameterThresholds(
            enabled=True,
            provisional=False,
            normal_limit=6.0,
            warning_limit=10.0,
            alarm_limit=None,
            classification_mode="higher_is_worse",
        )
        assert classify_parameter_value(5.0, thresholds) == "NORMAL"
        assert classify_parameter_value(8.0, thresholds) == "WARNING"
        assert classify_parameter_value(12.0, thresholds) == "ALARM"

    def test_provisional_thresholds_blocked_without_flag(self, monkeypatch):
        monkeypatch.setenv("GMD_THRESHOLD_CLASSIFICATION_ENABLED", "true")
        monkeypatch.setenv("GMD_THRESHOLD_ALLOW_PROVISIONAL", "false")

        status = classify_v2_parameter_status(
            value=12.0,
            equipment="MCB-1",
            category="Blowers",
            parameter_key="blower_drive_end_vertical",
        )
        assert status == "NORMAL"

    def test_provisional_thresholds_allowed_with_flag(self, monkeypatch):
        monkeypatch.setenv("GMD_THRESHOLD_CLASSIFICATION_ENABLED", "true")
        monkeypatch.setenv("GMD_THRESHOLD_ALLOW_PROVISIONAL", "true")

        status = classify_v2_parameter_status(
            value=12.0,
            equipment="MCB-1",
            category="Blowers",
            parameter_key="blower_drive_end_vertical",
        )
        assert status == "ALARM"
