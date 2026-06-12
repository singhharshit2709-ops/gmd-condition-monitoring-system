"""Tests for canonical Google Sheets row layout helpers."""

from __future__ import annotations

from services.sheets_row_model import (
    GMD_SHEET_HEADERS,
    GMD_SHEET_HEADERS_LEGACY,
    GMD_SHEET_HEADERS_LEGACY_GT,
    GMD_SHEET_HEADERS_LEGACY_V2,
    ReadingRowRecord,
    SheetSchema,
    build_reading_row,
    detect_sheet_schema,
    extract_reading_rows_from_worksheet,
    is_canonical_reading_slice,
    legacy_row_to_canonical_row,
    parse_reading_row,
    to_dashboard_api_row,
)


class TestSheetsRowLayout:
    def test_canonical_schema_detection(self):
        assert detect_sheet_schema(GMD_SHEET_HEADERS) == SheetSchema.CANONICAL
        assert detect_sheet_schema(GMD_SHEET_HEADERS_LEGACY) == SheetSchema.LEGACY_V1
        assert detect_sheet_schema(GMD_SHEET_HEADERS_LEGACY_V2) == SheetSchema.LEGACY_V2
        assert detect_sheet_schema(GMD_SHEET_HEADERS_LEGACY_GT) == SheetSchema.LEGACY_GT

    def test_build_canonical_row_order(self):
        record = ReadingRowRecord(
            submission_id="sub-123",
            timestamp="2026-06-10 12:00:00",
            area_tank="A Tank",
            category="Blowers",
            equipment="MCB-1",
            tag_no="",
            parameter_key="blower_drive_end_vertical",
            parameter_display_name="Blower Drive End Vertical Vibration",
            unit="mm/s",
            value="2.5",
            status="NORMAL",
            verified_by="Tech",
            remarks="Round complete",
            entry_source="Web",
        )
        row = build_reading_row(record)
        assert row[0] == "sub-123"
        assert row[1] == "2026-06-10 12:00:00"
        assert row[2] == "A Tank"
        assert row[3] == "Blowers"
        assert row[5] == ""
        assert row[6] == "blower_drive_end_vertical"
        assert row[7] == "Blower Drive End Vertical Vibration"
        assert row[8] == "mm/s"
        assert row[9] == "2.5"
        assert row[-1] == "Web"

    def test_parse_legacy_v1_row(self):
        legacy_row = [
            "2026-06-08 10:00:00",
            "Blowers",
            "MCB-1",
            "temperature",
            "Plant",
            "42",
            "NORMAL",
            "QA Tester",
            "DATA-SET-A",
            "QA",
        ]
        parsed = parse_reading_row(legacy_row, GMD_SHEET_HEADERS_LEGACY)
        assert parsed["category"] == "Blowers"
        assert parsed["equipment"] == "MCB-1"
        assert parsed["parameter_key"] == "temperature"
        assert parsed["parameter_display_name"] == "Plant"
        assert parsed["area_tank"] == ""

    def test_parse_legacy_v2_row(self):
        record = ReadingRowRecord(
            submission_id="uuid-1",
            timestamp="2026-06-10 12:00:00",
            area_tank="Utility Area",
            category="Utility Area Monitoring",
            equipment="Screw Compressor",
            tag_no="SC-1",
            parameter_key="discharge_pressure",
            parameter_display_name="Discharge Pressure",
            unit="bar",
            value="7.1",
            status="NORMAL",
            verified_by="Tech",
            entry_source="Web",
        )
        legacy_v2_row = build_reading_row(record, GMD_SHEET_HEADERS_LEGACY_V2)
        parsed = parse_reading_row(legacy_v2_row, GMD_SHEET_HEADERS_LEGACY_V2)
        assert parsed["area_tank"] == "Utility Area"
        assert parsed["tag_no"] == "SC-1"
        assert parsed["unit"] == "bar"
        assert parsed["submission_id"] == "uuid-1"

    def test_parse_canonical_row(self):
        record = ReadingRowRecord(
            submission_id="uuid-2",
            timestamp="2026-06-10 13:00:00",
            area_tank="G Tank",
            category="Blowers",
            equipment="MCB-3",
            parameter_key="motor_drive_end_vertical",
            parameter_display_name="Motor Drive End Vertical Vibration",
            unit="mm/s",
            value="1.2",
            status="NORMAL",
            verified_by="Tech",
            entry_source="Web",
        )
        row = build_reading_row(record)
        parsed = parse_reading_row(row, GMD_SHEET_HEADERS)
        assert parsed["parameter_key"] == "motor_drive_end_vertical"
        assert parsed["parameter_display_name"] == "Motor Drive End Vertical Vibration"

    def test_parse_legacy_gt_misaligned_row(self):
        gt_row = [
            "2026-06-02 9:56:29",
            "Blowers",
            "MCB-1",
            "vertical_vibration",
            "",
            "1.2",
            "NORMAL",
            "Harshil",
            "Test Entry",
            "Field",
        ]
        parsed = parse_reading_row(gt_row, GMD_SHEET_HEADERS_LEGACY_GT)
        assert parsed["timestamp"] == "2026-06-02 9:56:29"
        assert parsed["category"] == "Blowers"
        assert parsed["equipment"] == "MCB-1"
        assert parsed["parameter_key"] == "vertical_vibration"
        assert parsed["value"] == "1.2"
        assert parsed["verified_by"] == "Harshil"
        assert parsed["remarks"] == "Test Entry"
        assert parsed["entry_source"] == "Field"

    def test_legacy_gt_row_migrates_to_canonical(self):
        gt_row = [
            "2026-06-02 9:56:29",
            "Blowers",
            "MCB-1",
            "temperature",
            "",
            "45",
            "NORMAL",
            "singh",
            "testing",
            "Web",
        ]
        canonical = legacy_row_to_canonical_row(
            gt_row,
            GMD_SHEET_HEADERS_LEGACY_GT,
            submission_id="sub-abc",
        )
        assert canonical[0] == "sub-abc"
        assert canonical[1] == "2026-06-02 9:56:29"
        assert canonical[3] == "Blowers"
        assert canonical[4] == "MCB-1"
        assert canonical[6] == "temperature"
        assert canonical[9] == "45"
        assert canonical[11] == "singh"
        assert canonical[16] == "Web"

    def test_extract_drifted_reading_slice(self):
        canonical = build_reading_row(
            ReadingRowRecord(
                submission_id="sub-drift",
                timestamp="2026-06-11 16:35:03",
                area_tank="K Tank",
                category="DM Water Electrode Cooling",
                equipment="K Tank Electrode Cooling",
                parameter_key="tds",
                parameter_display_name="TDS (PPM)",
                unit="PPM",
                value="12",
                status="NORMAL",
                verified_by="Test User",
                remarks="Dashboard Sync Test",
                entry_source="Web",
            )
        )
        drifted_row = [""] * 48 + canonical
        assert is_canonical_reading_slice(canonical)
        assert not is_canonical_reading_slice(drifted_row)

        recovered = extract_reading_rows_from_worksheet(
            [GMD_SHEET_HEADERS, drifted_row]
        )
        assert len(recovered) == 1
        assert recovered[0][4] == "K Tank Electrode Cooling"
        assert recovered[0][6] == "tds"
        assert recovered[0][9] == "12"

    def test_dashboard_api_mapping_preserves_legacy_keys(self):
        parsed = parse_reading_row(
            [
                "2026-06-08 10:00:00",
                "Blowers",
                "MCB-1",
                "temperature",
                "Plant Temperature",
                "42",
                "NORMAL",
                "QA",
                "",
                "Web",
            ],
            GMD_SHEET_HEADERS_LEGACY,
        )
        api_row = to_dashboard_api_row(parsed)
        assert api_row["parameter"] == "temperature"
        assert api_row["location"] == "Plant Temperature"
        assert api_row["parameter_key"] == "temperature"
        assert api_row["parameter_display_name"] == "Plant Temperature"
