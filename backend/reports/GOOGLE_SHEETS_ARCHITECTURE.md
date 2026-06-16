# Google Sheets Architecture Documentation

**GMD Condition Monitoring System — Multi-Area Worksheet Layout**  
**Validation Timestamp:** 2026-06-15 10:24 IST  
**Verification Status:** PASS — routing, schema, merged reads confirmed

---

## Overview

Readings are stored in a single Google Spreadsheet with **one worksheet per plant area** (plus a virtual DM Water bucket). All worksheets share the same canonical 17-column schema. A centralized data access layer (`SheetsDataAccess`) handles routing, merging, caching, and header normalization.

---

## Spreadsheet Structure

```
Spreadsheet (GOOGLE_SHEET_ID)
│
├── A Tank                          ← physical area writes
├── E Tank                          ← physical area writes
├── G Tank                          ← physical area writes
├── K Tank                          ← physical area writes
├── Utility Area                    ← physical area writes
├── DM Water Electrode Cooling      ← virtual bucket (DM categories)
└── Readings (legacy — optional merge on read during migration)
```

---

## Production Verification Summary

| Verification Item | Result | Test / Module |
|-------------------|--------|---------------|
| A Tank worksheet selection | PASS | `resolve_area_worksheet(area_tank="A Tank", category="Blowers")` → `A Tank` |
| E Tank worksheet selection | PASS | Registry + routing tests |
| G Tank worksheet selection | PASS | MCB-3 blower → `G Tank` |
| K Tank worksheet selection | PASS | Registry + routing tests |
| Utility Area worksheet selection | PASS | `test_utility_area_routing` |
| DM Water virtual bucket | PASS | DM categories → `DM Water Electrode Cooling` |
| Canonical 17-column schema | PASS | `GMD_SHEET_HEADERS` |
| Column order on write | PASS | `test_build_canonical_row_order` |
| Timestamp format | PASS | `YYYY-MM-DD HH:MM:SS` |
| area_tank preserved on row | PASS | Column index 2 |
| category preserved | PASS | Column index 3 |
| equipment preserved | PASS | Column index 4 |
| tag_no preserved | PASS | Column index 5 |
| parameter_key / display / unit | PASS | Columns 6–8 |
| value / status | PASS | Columns 9–10 |
| verified_by / remarks | PASS | Columns 11–12 |
| media_name / type / url | PASS | Columns 13–15; submit media test |
| entry_source | PASS | Column 16 |
| Merged read (all tabs) | PASS | `SheetsDataAccess.get_all_values()` |
| Legacy tab merge (optional) | PASS | `GOOGLE_SHEETS_INCLUDE_LEGACY_READINGS=true` |
| Legacy layout parse | PASS | 10-col and 17-col Title Case + GT drift |

---

## Canonical Column Schema (All Worksheets)

| # | Column | Description |
|---|--------|-------------|
| 1 | `submission_id` | UUID grouping parameters from one submit |
| 2 | `timestamp` | `YYYY-MM-DD HH:MM:SS` |
| 3 | `area_tank` | Physical plant area |
| 4 | `category` | Config category (Blowers, DM Water, etc.) |
| 5 | `equipment` | Equipment display name |
| 6 | `tag_no` | Utility tag identifier |
| 7 | `parameter_key` | Stable parameter key |
| 8 | `parameter_display_name` | Human-readable label |
| 9 | `unit` | Engineering unit |
| 10 | `value` | Numeric reading |
| 11 | `status` | NORMAL / WARNING / ALARM |
| 12 | `verified_by` | Operator name |
| 13 | `remarks` | Free text |
| 14 | `media_name` | Attachment filename |
| 15 | `media_type` | MIME type |
| 16 | `media_url` | Google Drive URL |
| 17 | `entry_source` | Web / Field / QA |

New rows are inserted at **row 2** (newest first, below header).

---

## Write Routing

| Condition | Target Worksheet |
|-----------|------------------|
| Category = DM Water Electrode Cooling or DM Water Batch Charger | `DM Water Electrode Cooling` |
| `area_tank` = A Tank | `A Tank` |
| `area_tank` = E Tank | `E Tank` |
| `area_tank` = G Tank | `G Tank` |
| `area_tank` = K Tank | `K Tank` |
| `area_tank` = Utility Area | `Utility Area` |
| Missing area, equipment in config | Resolved from `gmd_machine_config_v2.json` |

**Implementation:** `services/sheets_area_registry.py` → `resolve_area_worksheet()`

**Grouped writes:** `SheetsDataAccess.append_v2_readings()` routes each submission batch to the resolved worksheet and builds canonical rows via `build_reading_row()`.

---

## Read Path (Dashboard, Reports, Trends)

```
GMDGoogleSheetsService.get_all_values()
  └── SheetsDataAccess.get_all_values()
        ├── Read each area worksheet (A, E, G, K, Utility, DM Water)
        ├── Optionally merge legacy Readings tab
        ├── Parse all rows to canonical format (header-aware)
        ├── Sort by timestamp descending
        └── Return [header] + merged rows
```

All downstream modules use existing helpers:

- `fetch_and_clean_data()` in `routes/dashboard.py`
- Shared by `reports.py` and `trends.py`

**No API contract changes** — frontend modules unchanged.

---

## Centralized Data Access Layer

| Module | Responsibility |
|--------|----------------|
| `services/sheets_row_model.py` | Column schema, row build/parse, legacy detection |
| `services/sheets_config.py` | Credentials, worksheet open/create, header repair |
| `services/sheets_area_registry.py` | Area names, write routing, layout flags |
| `services/sheets_data_access.py` | Multi-worksheet read merge, grouped writes, cache |
| `services/google_sheets_service.py` | Singleton facade, V1/V2 append APIs |
| `services/threshold_service.py` | Config-driven status classification (opt-in) |

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GOOGLE_SHEETS_AREA_LAYOUT` | `multi` | `multi` = per-area tabs; `legacy` = single Readings tab |
| `GOOGLE_SHEETS_INCLUDE_LEGACY_READINGS` | `true` | Merge legacy tab during migration |
| `GOOGLE_SHEET_WORKSHEET` | `Readings` | Legacy worksheet name |
| `GOOGLE_SHEETS_CACHE_TTL_SECONDS` | `45` | Read cache TTL |
| `GOOGLE_SHEETS_ENABLED` | — | Must be `true` in production |
| `GOOGLE_SHEET_ID` | — | Target spreadsheet |

---

## Migration

To copy existing `Readings` tab rows into area worksheets:

```bash
cd backend
python scripts/migrate_readings_to_area_sheets.py --dry-run
python scripts/migrate_readings_to_area_sheets.py
```

Rows are deduplicated and routed using the same `resolve_area_worksheet()` logic as live writes.

---

## Legacy Compatibility

- Legacy 10-column and 17-column Title Case layouts still parse on read
- GT motor 22-column rows supported via schema detection
- Horizontal drift repair runs per-worksheet on init
- Dashboard API mapping preserves legacy response keys (`test_dashboard_api_mapping_preserves_legacy_keys`)

---

## Post-Deploy Worksheet Smoke Test

For each target worksheet, submit one reading and confirm:

1. Row appears in the **correct tab** (not legacy `Readings` unless layout=legacy)
2. All 17 columns populated (media columns blank if no attachment)
3. Dashboard recent readings reflect submission within cache TTL
4. Reports and Trends show the new row after cache refresh

---

*Architecture verified 2026-06-15 — GMD final deployment package.*
