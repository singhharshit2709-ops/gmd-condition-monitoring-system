"""Tests for plant-local timestamp helpers."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from services.gmd_datetime import (
    format_plant_timestamp,
    parse_plant_timestamp,
    plant_now,
    reading_timestamp_sort_key,
)


class TestGmdDatetime:
    def test_format_plant_timestamp_from_aware_ist(self):
        dt = datetime(2026, 6, 15, 18, 45, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
        assert format_plant_timestamp(dt) == "2026-06-15 18:45:30"

    def test_parse_plant_timestamp_naive_string(self, monkeypatch):
        monkeypatch.delenv("GMD_PLANT_TIMEZONE", raising=False)
        parsed = parse_plant_timestamp("2026-06-15 18:45:30")
        assert parsed is not None
        assert parsed.tzinfo == ZoneInfo("Asia/Kolkata")
        assert parsed.hour == 18
        assert parsed.minute == 45

    def test_plant_now_is_timezone_aware(self, monkeypatch):
        monkeypatch.delenv("GMD_PLANT_TIMEZONE", raising=False)
        now = plant_now()
        assert now.tzinfo is not None
        assert str(now.tzinfo) == "Asia/Kolkata"

    def test_round_trip_format_and_parse(self, monkeypatch):
        monkeypatch.delenv("GMD_PLANT_TIMEZONE", raising=False)
        original = plant_now()
        formatted = format_plant_timestamp(original)
        parsed = parse_plant_timestamp(formatted)
        assert parsed is not None
        assert parsed.replace(microsecond=0) == original.replace(microsecond=0)

    def test_reading_timestamp_sort_key_orders_newest_first(self, monkeypatch):
        monkeypatch.delenv("GMD_PLANT_TIMEZONE", raising=False)
        rows = [
            ("2026-06-15 10:00:00", "yesterday"),
            ("2026-06-16 09:00:00", "today_morning"),
            ("2026-06-16 15:30:00", "newest"),
            ("16/06/2026 14:00:00", "today_dmy"),
        ]
        ordered = sorted(
            rows,
            key=lambda item: reading_timestamp_sort_key(item[0]),
            reverse=True,
        )
        assert ordered[0][1] == "newest"
        assert ordered[1][1] == "today_dmy"
        assert ordered[-1][1] == "yesterday"

    def test_string_sort_would_misorder_dmy_format(self, monkeypatch):
        """Document why parsed datetime sort is required over raw string sort."""
        monkeypatch.delenv("GMD_PLANT_TIMEZONE", raising=False)
        rows = [
            ("2026-06-16 08:00:00", "iso_early"),
            ("16/06/2026 20:00:00", "dmy_late"),
        ]
        string_sorted = sorted(rows, key=lambda item: item[0], reverse=True)
        datetime_sorted = sorted(
            rows,
            key=lambda item: reading_timestamp_sort_key(item[0]),
            reverse=True,
        )
        assert string_sorted[0][1] == "iso_early"
        assert datetime_sorted[0][1] == "dmy_late"
