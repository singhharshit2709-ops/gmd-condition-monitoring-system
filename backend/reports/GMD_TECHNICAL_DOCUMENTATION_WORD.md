---
title: GMD Condition Monitoring System — Technical Documentation
author: GMD Engineering / Documentation Generator
date: 2026-06-12
format: Word-ready Markdown (paste into Microsoft Word or Pandoc)
---

# TITLE PAGE

**GMD Condition Monitoring System**  
**Technical Documentation Package**

Neutral Glass — General Maintenance Department  
Document Version 1.0  
Generated: 2026-06-12

This document is formatted for import into Microsoft Word:
- Open Word → File → Open → select this `.md` file, or
- Use Pandoc: `pandoc GMD_TECHNICAL_DOCUMENTATION_WORD.md -o GMD_Documentation.docx`

Companion appendices are in `backend/reports/`.

---

# GMD Condition Monitoring System — Technical Documentation

**Document version:** 1.0  
**Generated:** 2026-06-12  
**System:** Neutral Glass — General Maintenance Department (GMD) Electrical Condition Monitoring  
**Configuration:** `gmd_machine_config_v2.json` — 87 equipment instances, 1002 parameter slots, 42 unique parameter keys

---

## Table of Contents

1. [Complete Project Assessment](#part-1-complete-project-assessment)
2. [System Architecture](#part-2-system-architecture-documentation)
3. [Functional Module Documentation](#part-3-functional-module-documentation)
4. [Complete Plant Hierarchy](#part-4-complete-plant-hierarchy-documentation)
5. [Parameter Documentation](#part-5-parameter-documentation)
6. [Google Sheets Documentation](#part-6-google-sheets-documentation)
7. [Dashboard Calculations](#part-7-dashboard-calculations)
8. [Configuration Documentation](#part-8-configuration-documentation)
9. [Current Feature Checklist](#part-9-current-feature-checklist)
10. [Technical Assessment](#part-10-technical-assessment)

**Appendices (companion files in `backend/reports/`):**

- `PLANT_HIERARCHY_APPENDIX.md` — full equipment/parameter listing per area
- `PARAMETER_CATALOGUE.md` — 42 unique internal parameter keys
- `PARAMETER_EQUIPMENT_MATRIX.md` — all 1002 parameter-to-equipment mappings
- `config_hierarchy_export.json` — machine-readable hierarchy export

---

# Part 1: Complete Project Assessment

## 1.1 Executive Overview

The GMD Condition Monitoring System is a web application for daily engineering rounds at a glass manufacturing plant. Operators record vibration, temperature, pressure, water quality, and electrical readings for **87 configured equipment instances** across six dashboard areas. Data persists to **Google Sheets** (canonical row store) with optional **Google Drive** media attachments. The **React** frontend provides Dashboard, Add Reading, Equipment Monitoring, Reports, and Trends & Analytics modules. The **FastAPI** backend serves REST APIs, validates submissions against JSON configuration, and integrates with Google APIs.

## 1.2 Frontend Assessment

| Module | Route | Status | Notes |
|--------|-------|--------|-------|
| Dashboard | `/` | Production-ready | Area-first KPIs, auto-refresh 30s, client-side analytics |
| Add Reading | `/add-reading` | Production-ready | V2 round sheet, config-driven hierarchy |
| Equipment Monitoring | `/equipment-monitoring` | Functional | Uses `/reports/readings`; legacy parameter labels |
| Reports | `/reports` | Functional | Filterable table, CSV export in UI |
| Trends & Analytics | `/trends-analytics` | Functional | Config-driven filters, Recharts visualization |

**Stack:** React 18, React Router, Axios, Tailwind CSS, Recharts, Phosphor Icons. Production build is served as static assets from `backend/static/`.

**Strengths:** Config-driven Add Reading and Trends; modular dashboard components; relative time formatting; cross-module event `gmd-readings-updated` for post-submit refresh.

**Gaps:** Equipment Monitoring still uses hardcoded standard parameter names rather than V2 config keys; Jest unit tests for `dashboardAnalytics.js` exist but may require Babel setup locally.

## 1.3 Backend Assessment

| Component | Path | Role |
|-----------|------|------|
| FastAPI app | `backend/server.py` | SPA hosting, legacy GT motor APIs, router mounting |
| Dashboard API | `backend/routes/dashboard.py` | Summary, recent readings, alarms, equipment health |
| V2 Submit | `backend/routes/v2_preview.py` | Preview + persist round sheet submissions |
| Reports API | `backend/routes/reports.py` | Filtered historical readings |
| Trends API | `backend/routes/trends.py` | Numeric time-series for charts |
| Config engine | `backend/gmd_config_v2.py` | Load/query V2 hierarchy |
| Validation | `backend/services/v2_validation.py` | Parameter completeness and type checks |
| Sheets service | `backend/services/google_sheets_service.py` | Read/write canonical rows |
| Row model | `backend/services/sheets_row_model.py` | 17-column schema, legacy parsing |
| Drive service | `backend/services/google_drive_service.py` | Media upload |

**Strengths:** Canonical sheets row model with legacy header compatibility; dashboard caching (30–60s TTL); meaningful-row filtering prevents blank rows from polluting analytics; comprehensive backend tests.

**Gaps:** V2 submit writes `status="NORMAL"` for all parameters — config thresholds are defined but not applied at persist time (see Part 7). Alarm acknowledgement is in-memory only (resets on server restart).

## 1.4 Google Sheets Integration Assessment

- **Write path:** V2 submit → `append_v2_readings()` → `insert_rows` at row 2, column A (prevents horizontal drift on widened worksheets).
- **Read path:** Dashboard, Reports, Trends, Equipment Monitoring all read via `GMDGoogleSheetsService.get_all_values()`.
- **Schema:** 17 canonical columns (snake_case); legacy Title Case layouts parsed via header aliases.
- **Sync:** Dashboard polls every 30 seconds; submit invalidates dashboard cache and dispatches browser event for immediate refresh.

## 1.5 Configuration Assessment

Single source of truth: `backend/gmd_machine_config_v2.json` validated by `gmd_machine_config_v2.schema.json`. Hierarchy: **Plant → Category → Equipment → Sections → Groups → Parameters**. Dashboard areas are derived dynamically — DM Water categories roll into virtual bucket **DM Water Electrode Cooling**.

## 1.6 Aggregation & Status Assessment

- **Backend equipment health:** Worst status across latest parameter readings per equipment name (`ALARM > WARNING > NORMAL`).
- **Frontend area health:** Based on equipment touched **today**; health % = normal ÷ tracked × 100 among today's submissions only.
- **Duplicate equipment names** (e.g. Gas Blower-1 in four tanks): resolved by area + tag matching in `dashboardAnalytics.js`.

---

# Part 2: System Architecture Documentation

## 2.1 Overall Architecture


```

┌─────────────────────────────────────────────────────────────────┐
│                     React SPA (frontend/)                        │
│  Dashboard │ Add Reading │ Equipment Monitoring │ Reports │ Trends│
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/JSON (Axios)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (backend/)                       │
│  /dashboard/*  /api/v2/*  /reports/*  /trends/*  /health       │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐
│ Business     │  │ Configuration │  │ Google Integration        │
│ Logic        │  │ Engine        │  │ Sheets + Drive            │
│ validation,  │  │ gmd_config_v2 │  │ sheets_row_model          │
│ aggregation  │  │ .json         │  │ google_sheets_service     │
└──────────────┘  └───────────────┘  └──────────────────────────┘

```


## 2.2 Data Flow

1. **Configuration load:** Frontend imports V2 JSON via `gmdConfigV2.js`; backend loads via `gmd_config_v2.py` (@lru_cache).
2. **Submission:** User completes round sheet → POST `/api/v2/preview` (optional) → POST `/api/v2/submit` → validation → optional Drive upload → Sheets append (one row per parameter).
3. **Dashboard read:** Four parallel GETs → backend reads Sheets → parse rows → cache → frontend `dashboardAnalytics.js` derives area summaries, round completion, banners.
4. **Reports/Trends read:** GET with query filters → same Sheets source → client-side table/chart rendering.

## 2.3 Request Flow (Add Reading → Dashboard)


```

User → RoundSheetForm → v2SubmitApi.js
  → POST /api/v2/submit
    → validate_v2_submission()
    → GoogleDriveMediaService (if media)
    → GMDGoogleSheetsService.append_v2_readings()
    → invalidate_all_dashboard_cache()
  → window.dispatchEvent('gmd-readings-updated')
  → useDashboardData.fetchData()
  → Dashboard re-renders with new readings

```


## 2.4 Storage Flow

| Store | Content | Lifecycle |
|-------|---------|-----------|
| Google Sheets | All parameter readings (canonical 17 columns) | Append-only at row 2 |
| Google Drive | Submission photos/PDFs | Uploaded on submit; URL stored in sheet |
| Browser localStorage | Cached dashboard summary | Cleared on readings-updated event |
| Server memory | Dashboard cache, acknowledged alarm IDs | TTL 30–60s; alarms lost on restart |

---

# Part 3: Functional Module Documentation

## 3.1 Dashboard

**Purpose:** Plant-wide operational snapshot for daily engineering rounds — area health, KPIs, recent activity, and round completion progress.

**Data sources:** `/dashboard/summary`, `/dashboard/recent-readings?limit=200`, `/dashboard/active-alarms`, `/dashboard/equipment-health`.

**KPI Grid:** Total equipment (from config), OK / Warning / Alarm counts (from backend summary — historical worst-status across all sheet data vs configured total).

**Area Health Overview:** Six area cards (dynamic from config): A Tank, E Tank, G Tank, K Tank, Utility Area, DM Water Electrode Cooling. Each shows health %, normal/warning/alarm/pending counts, last updated (relative time).

**Recent Readings:** Latest deduplicated sheet rows (limit 10 in panel), with area resolution and relative timestamps.

**Recent Alerts:** Active WARNING/ALARM parameter rows from equipment aggregates, excluding acknowledged IDs.

**Today's Round Completion:** Per-area progress bar — equipment with ≥1 reading today ÷ configured equipment in area.

**Footer metrics:** Total areas, total equipment, total parameters, today's entries, completed equipment (unique area::equipment keys), pending round count, last refresh, Sheets connection status.

**Filters & search:** Cascading area → category → equipment → tag → status → verified-by filters with typeahead search index.

**Key files:** `frontend/src/pages/Dashboard.js`, `frontend/src/hooks/useDashboardData.js`, `frontend/src/lib/dashboardAnalytics.js`, `frontend/src/components/dashboard/*`.

## 3.2 Add Reading

**Purpose:** Structured daily round data entry matching plant round sheets.

**Workflow:**

1. Select **Area/Tank** (from config plant areas + virtual DM bucket).
2. **Tank areas:** Select equipment directly.
3. **Utility Area:** Select equipment type (category kind) → select **Tag No** (tagged equipment instances).
4. **RoundSheetForm** renders sections/groups/parameters from config.
5. Enter numeric values, **Verified By**, **Remarks**, optional **media** (image/PDF).
6. **Preview** (POST `/api/v2/preview`) or **Submit** (POST `/api/v2/submit`).
7. On success: Sheets persistence + dashboard refresh event.

**Validation:** Equipment must exist in config under selected category; all `required` parameters must be numeric; unexpected keys rejected.

**Submission payload:** `area_tank`, `category`, `equipment`, `tag_no`, `readings` (key→value map), `verified_by`, `remarks`, `submission_id`, `entry_source`, optional media fields.

**Key files:** `frontend/src/components/v2/AddReadingPage.jsx`, `RoundSheetForm.jsx`, `frontend/src/lib/v2SubmitApi.js`, `backend/routes/v2_preview.py`, `backend/services/v2_validation.py`.

## 3.3 Equipment Monitoring

**Purpose:** Per-equipment historical view with latest snapshot and simple trend chart.

**Behavior:** Loads all readings from `/reports/readings`; builds equipment list from unique equipment names in sheet data; user selects equipment and parameter; displays latest values and Recharts line chart filtered client-side.

**Limitation:** Parameter dropdown uses legacy standard names (Vertical Vibration, Temperature, etc.) — may not align with V2-specific parameter keys for all equipment types.

**Key file:** `frontend/src/pages/ConditionMonitoring.js`.

## 3.4 Reports

**Purpose:** Searchable audit trail of all submitted readings.

**Backend:** GET `/reports/readings` with optional filters: `category`, `equipment`, `status`, `start_date`, `end_date` (YYYY-MM-DD).

**Frontend:** Table with client-side search; date/category/equipment/status filters; displays timestamp, area, category, equipment, tag, parameter, value, unit, status, verified by, remarks.

**Export:** CSV download from filtered results (client-generated).

**Key files:** `backend/routes/reports.py`, `frontend/src/pages/Reports.js`.

## 3.5 Trends & Analytics

**Purpose:** Parameter evolution over time for predictive maintenance groundwork.

**Backend:** GET `/trends/readings` — filters: `area_tank`, `category`, `equipment`, `tag_no`, `parameter`, `window` (days), `start_date`, `end_date`. Returns numeric points only.

**Frontend:** Config-driven area/equipment/parameter pickers; 7/30/90-day windows or custom dates; Recharts multi-series; threshold reference lines from config; statistics grid (min/max/avg/latest).

**Future scope:** Anomaly detection, ML forecasting, SPC control charts, OPC-UA live streaming — architecture supports by swapping data source on trends endpoint.

**Key files:** `backend/routes/trends.py`, `frontend/src/pages/TrendsAnalytics.js`, `frontend/src/lib/trendsAnalytics.js`.

---

# Part 4: Complete Plant Hierarchy Documentation

## 4.1 Summary by Dashboard Area

| Dashboard Area | Equipment Count | Categories |
|----------------|-----------------|------------|
| A Tank | 14 | Blowers, Cooling Tower Water Monitoring |
| E Tank | 12 | Blowers |
| G Tank | 14 | Blowers, Cooling Tower Water Monitoring |
| K Tank | 11 | Blowers |
| DM Water Electrode Cooling | 6 | DM Water Batch Charger, DM Water Electrode Cooling |
| Utility Area | 30 | Cooling Tower Water Monitoring, Utility Area Monitoring |

**Total configured equipment instances:** 87

## 4.2 Hierarchy Structure


```

Plant (Neutral Glass GMD)
├── A Tank
│   ├── Blowers (13 units: MCB-1..3, Gas Blower-1/2, Chimney, Cooling, Throat Cool, etc.)
│   └── Cooling Tower Water Monitoring (A Tank CT)
├── E Tank
│   └── Blowers (12 units)
├── G Tank
│   ├── Blowers (13 units)
│   └── Cooling Tower Water Monitoring (G Tank CT)
├── K Tank
│   └── Blowers (11 units)
├── Utility Area
│   ├── Utility Area Monitoring (compressors, receivers, DG, PHE, air dryers, etc.)
│   └── Cooling Tower Water Monitoring (CT-1/2/3, Compressor House CT, G Tank CT)
└── DM Water Electrode Cooling (virtual bucket)
    ├── DM Water Electrode Cooling (A/E/G/K Tank Electrode Cooling — TDS, temp, pressure)
    └── DM Water Batch Charger (A Tank, K & E Tank batch chargers)

```


## 4.3 Standard Blower Parameter Set (16 parameters)

Most tank blowers share: 6 blower vibration (DE/NDE × V/H/A), 2 blower temperatures, 6 motor vibration, 2 motor temperatures — all in mm/s and °C.

## 4.4 Utility Area Highlights

Tagged equipment includes: Pilot Air, Comp-1..4, centac-1..3, Kaser-1/2, D.G Room, LP/HP/PILOT/G-TANK receivers, BATCH, K.E.PHE, G.PHE, G.Dry, Cooling Towers, Air Receivers, All DG Set.

## 4.5 DM Water Electrode Cooling

| Equipment | Parameters | Units |
|-----------|------------|-------|
| A/E/G/K Tank Electrode Cooling | TDS, DM Water Temperature, Pump Pressure | PPM, °C, KG/CM² |
| A Tank Batch Charger | Cooling Water Temperature | °C |
| K & E Tank Batch Charger | Cooling Water Temperature | °C |

## 4.6 Complete Listing

### 4.7 Complete Equipment Listing

## A Tank

### Blowers

- **MCB-1**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **MCB-2**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **MCB-3**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Gas Blower-1**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Gas Blower-2**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower-3**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower-4**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Tank Cooling Blower-7**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Tank Cooling Blower-8**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Cooling Blower-15**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Cooling Blower-16**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Throat Cool Blower-11**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Throat Cool Blower-12**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)

### Cooling Tower Water Monitoring

- **A Tank CT**
  - Parameters: Water Temperature (°C), TDS (ppm), pH (pH)

## E Tank

### Blowers

- **Gas Blower-1**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Gas Blower-2**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower-3**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower-4**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **MCB-5**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **MCB-6**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Block Cooling Blower-7**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Block Cooling Blower-8**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Tank Cool Blower-11**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Tank Cool Blower-12**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Working End Blower-1**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Working End Blower-2**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)

## G Tank

### Blowers

- **MCB-1**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **MCB-2**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **MCB-3**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Gas Blower-1**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Gas Blower-2**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower (15 kW)-1**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower (15 kW)-2**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower (15 kW)-3**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower (7.5 kW)-1**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower (7.5 kW)-2**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower (7.5 kW)-3**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Block Cooling Blower-1**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Block Cooling Blower-2**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)

### Cooling Tower Water Monitoring

- **G Tank CT**
  - Parameters: Water Temperature (°C), TDS (ppm), pH (pH)

## K Tank

### Blowers

- **Gas Blower-1**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Gas Blower-2**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **MCB-132 (132 kW)**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower-3**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Chimney Blower-4**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **MCB-5**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **MCB-6**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Block Cooling Blower-7**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Block Cooling Blower-8**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Throat Cool Blower-11**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)
- **Throat Cool Blower-12**
  - Parameters: Blower Drive End Vertical Vibration (mm/s), Blower Drive End Horizontal Vibration (mm/s), Blower Drive End Axial Vibration (mm/s), Blower Non Drive End Vertical Vibration (mm/s), Blower Non Drive End Horizontal Vibration (mm/s), Blower Non Drive End Axial Vibration (mm/s), Blower DE Temperature (°C), Blower NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C)

## Utility Area

### Cooling Tower Water Monitoring

- **Compressor House CT** (Tag: Compressor House CT)
  - Parameters: Water Temperature (°C), TDS (ppm), pH (pH)

### Utility Area Monitoring

- **Pilot Air** (Tag: Pilot Air)
  - Parameters: Compressor Drive End Vertical Vibration (mm/s), Compressor Drive End Horizontal Vibration (mm/s), Compressor Drive End Axial Vibration (mm/s), Compressor Non Drive End Vertical Vibration (mm/s), Compressor Non Drive End Horizontal Vibration (mm/s), Compressor Non Drive End Axial Vibration (mm/s), Compressor DE Temperature (°C), Compressor NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C), Current (A)
- **Comp-1** (Tag: Comp-1)
  - Parameters: Compressor Drive End Vertical Vibration (mm/s), Compressor Drive End Horizontal Vibration (mm/s), Compressor Drive End Axial Vibration (mm/s), Compressor Non Drive End Vertical Vibration (mm/s), Compressor Non Drive End Horizontal Vibration (mm/s), Compressor Non Drive End Axial Vibration (mm/s), Compressor DE Temperature (°C), Compressor NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C), Current (A)
- **Comp-2** (Tag: Comp-2)
  - Parameters: Compressor Drive End Vertical Vibration (mm/s), Compressor Drive End Horizontal Vibration (mm/s), Compressor Drive End Axial Vibration (mm/s), Compressor Non Drive End Vertical Vibration (mm/s), Compressor Non Drive End Horizontal Vibration (mm/s), Compressor Non Drive End Axial Vibration (mm/s), Compressor DE Temperature (°C), Compressor NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C), Current (A)
- **Comp-3** (Tag: Comp-3)
  - Parameters: Compressor Drive End Vertical Vibration (mm/s), Compressor Drive End Horizontal Vibration (mm/s), Compressor Drive End Axial Vibration (mm/s), Compressor Non Drive End Vertical Vibration (mm/s), Compressor Non Drive End Horizontal Vibration (mm/s), Compressor Non Drive End Axial Vibration (mm/s), Compressor DE Temperature (°C), Compressor NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C), Current (A)
- **Comp-4** (Tag: Comp-4)
  - Parameters: Compressor Drive End Vertical Vibration (mm/s), Compressor Drive End Horizontal Vibration (mm/s), Compressor Drive End Axial Vibration (mm/s), Compressor Non Drive End Vertical Vibration (mm/s), Compressor Non Drive End Horizontal Vibration (mm/s), Compressor Non Drive End Axial Vibration (mm/s), Compressor DE Temperature (°C), Compressor NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C), Current (A)
- **D.G Room** (Tag: D.G Room)
  - Parameters: Compressor Drive End Vertical Vibration (mm/s), Compressor Drive End Horizontal Vibration (mm/s), Compressor Drive End Axial Vibration (mm/s), Compressor Non Drive End Vertical Vibration (mm/s), Compressor Non Drive End Horizontal Vibration (mm/s), Compressor Non Drive End Axial Vibration (mm/s), Compressor DE Temperature (°C), Compressor NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C), Current (A)
- **Kaser-1** (Tag: Kaser-1)
  - Parameters: Compressor Drive End Vertical Vibration (mm/s), Compressor Drive End Horizontal Vibration (mm/s), Compressor Drive End Axial Vibration (mm/s), Compressor Non Drive End Vertical Vibration (mm/s), Compressor Non Drive End Horizontal Vibration (mm/s), Compressor Non Drive End Axial Vibration (mm/s), Compressor DE Temperature (°C), Compressor NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C), Current (A)
- **Kaser-2** (Tag: Kaser-2)
  - Parameters: Compressor Drive End Vertical Vibration (mm/s), Compressor Drive End Horizontal Vibration (mm/s), Compressor Drive End Axial Vibration (mm/s), Compressor Non Drive End Vertical Vibration (mm/s), Compressor Non Drive End Horizontal Vibration (mm/s), Compressor Non Drive End Axial Vibration (mm/s), Compressor DE Temperature (°C), Compressor NDE Temperature (°C), Motor Drive End Vertical Vibration (mm/s), Motor Drive End Horizontal Vibration (mm/s), Motor Drive End Axial Vibration (mm/s), Motor Non Drive End Vertical Vibration (mm/s), Motor Non Drive End Horizontal Vibration (mm/s), Motor Non Drive End Axial Vibration (mm/s), Motor DE Temperature (°C), Motor NDE Temperature (°C), Current (A)
- **centac-1** (Tag: centac-1)
  - Parameters: Vertical Vibration (mm/s), Horizontal Vibration (mm/s), Temperature (°C), Current (A)
- **centac-2** (Tag: centac-2)
  - Parameters: Vertical Vibration (mm/s), Horizontal Vibration (mm/s), Temperature (°C), Current (A)
- **centac-3** (Tag: centac-3)
  - Parameters: Vertical Vibration (mm/s), Horizontal Vibration (mm/s), Temperature (°C), Current (A)
- **LP** (Tag: LP)
  - Parameters: Temperature (°C), Pressure (bar)
- **HP** (Tag: HP)
  - Parameters: Temperature (°C), Pressure (bar)
- **PILOT** (Tag: PILOT)
  - Parameters: Temperature (°C), Pressure (bar)
- **G-TANK** (Tag: G-TANK)
  - Parameters: Temperature (°C), Pressure (bar)
- **LP** (Tag: LP)
  - Parameters: Vertical Vibration (mm/s), Horizontal Vibration (mm/s), Temperature (°C)
- **HP** (Tag: HP)
  - Parameters: Vertical Vibration (mm/s), Horizontal Vibration (mm/s), Temperature (°C)
- **BATCH** (Tag: BATCH)
  - Parameters: Vertical Vibration (mm/s), Horizontal Vibration (mm/s), Temperature (°C)
- **K.E.PHE** (Tag: K.E.PHE)
  - Parameters: Vertical Vibration (mm/s), Horizontal Vibration (mm/s), Temperature (°C)
- **G.PHE** (Tag: G.PHE)
  - Parameters: Vertical Vibration (mm/s), Horizontal Vibration (mm/s), Temperature (°C)
- **G.Dry** (Tag: G.Dry)
  - Parameters: Vertical Vibration (mm/s), Horizontal Vibration (mm/s), Temperature (°C)
- **Cooling Tower-1** (Tag: Cooling Tower-1)
  - Parameters: Water Temperature (°C), TDS (ppm), pH (pH)
- **Cooling Tower-2** (Tag: Cooling Tower-2)
  - Parameters: Water Temperature (°C), TDS (ppm), pH (pH)
- **Cooling Tower-3** (Tag: Cooling Tower-3)
  - Parameters: Water Temperature (°C), TDS (ppm), pH (pH)
- **G Tank Cooling Tower** (Tag: G Tank Cooling Tower)
  - Parameters: Water Temperature (°C), TDS (ppm), pH (pH)
- **Pilot Air Receiver** (Tag: Pilot Air Receiver)
  - Parameters: Pressure (bar), Temperature (°C)
- **Utility Area Receiver** (Tag: Utility Area Receiver)
  - Parameters: Pressure (bar), Temperature (°C)
- **G-Tank Air Receiver** (Tag: G-Tank Air Receiver)
  - Parameters: Pressure (bar), Temperature (°C)
- **All DG Set** (Tag: All DG Set)
  - Parameters: Temperature (°C), Current (A), Voltage (V)

## DM Water Electrode Cooling

### DM Water Batch Charger

- **A Tank Batch Charger**
  - Parameters: Cooling Water Temperature (°C) (°C)
- **K & E Tank Batch Charger**
  - Parameters: Cooling Water Temperature (°C) (°C)

### DM Water Electrode Cooling

- **A Tank Electrode Cooling**
  - Parameters: TDS (PPM) (PPM), DM Water Temperature (°C) (°C), Pump Pressure (KG/CM²) (KG/CM²)
- **E Tank Electrode Cooling**
  - Parameters: TDS (PPM) (PPM), DM Water Temperature (°C) (°C), Pump Pressure (KG/CM²) (KG/CM²)
- **G Tank Electrode Cooling**
  - Parameters: TDS (PPM) (PPM), DM Water Temperature (°C) (°C), Pump Pressure (KG/CM²) (KG/CM²)
- **K Tank Electrode Cooling**
  - Parameters: TDS (PPM) (PPM), DM Water Temperature (°C) (°C), Pump Pressure (KG/CM²) (KG/CM²)


---

# Part 5: Parameter Documentation

## 5.1 Unique Parameter Keys (42 keys)

The system uses stable snake_case **parameter keys** in submissions and Google Sheets. Display names and units come from config.

### 5.1.1 Master Parameter Key Catalogue

| Internal Key | Display Name | Typical Unit |
|---|---|---|
| blower_de_temperature | Blower DE Temperature | °C |
| blower_drive_end_axial | Blower Drive End Axial Vibration | mm/s |
| blower_drive_end_horizontal | Blower Drive End Horizontal Vibration | mm/s |
| blower_drive_end_vertical | Blower Drive End Vertical Vibration | mm/s |
| blower_nde_temperature | Blower NDE Temperature | °C |
| blower_non_drive_end_axial | Blower Non Drive End Axial Vibration | mm/s |
| blower_non_drive_end_horizontal | Blower Non Drive End Horizontal Vibration | mm/s |
| blower_non_drive_end_vertical | Blower Non Drive End Vertical Vibration | mm/s |
| compressor_de_temperature | Compressor DE Temperature | °C |
| compressor_drive_end_axial_vibration | Compressor Drive End Axial Vibration | mm/s |
| compressor_drive_end_horizontal_vibration | Compressor Drive End Horizontal Vibration | mm/s |
| compressor_drive_end_vertical_vibration | Compressor Drive End Vertical Vibration | mm/s |
| compressor_nde_temperature | Compressor NDE Temperature | °C |
| compressor_non_drive_end_axial_vibration | Compressor Non Drive End Axial Vibration | mm/s |
| compressor_non_drive_end_horizontal_vibration | Compressor Non Drive End Horizontal Vibration | mm/s |
| compressor_non_drive_end_vertical_vibration | Compressor Non Drive End Vertical Vibration | mm/s |
| cooling_water_temperature | Cooling Water Temperature (°C) | °C |
| current | Current | A |
| dm_water_temperature | DM Water Temperature (°C) | °C |
| horizontal_vibration | Horizontal Vibration | mm/s |
| motor_de_temperature | Motor DE Temperature | °C |
| motor_drive_end_axial | Motor Drive End Axial Vibration | mm/s |
| motor_drive_end_axial_vibration | Motor Drive End Axial Vibration | mm/s |
| motor_drive_end_horizontal | Motor Drive End Horizontal Vibration | mm/s |
| motor_drive_end_horizontal_vibration | Motor Drive End Horizontal Vibration | mm/s |
| motor_drive_end_vertical | Motor Drive End Vertical Vibration | mm/s |
| motor_drive_end_vertical_vibration | Motor Drive End Vertical Vibration | mm/s |
| motor_nde_temperature | Motor NDE Temperature | °C |
| motor_non_drive_end_axial | Motor Non Drive End Axial Vibration | mm/s |
| motor_non_drive_end_axial_vibration | Motor Non Drive End Axial Vibration | mm/s |
| motor_non_drive_end_horizontal | Motor Non Drive End Horizontal Vibration | mm/s |
| motor_non_drive_end_horizontal_vibration | Motor Non Drive End Horizontal Vibration | mm/s |
| motor_non_drive_end_vertical | Motor Non Drive End Vertical Vibration | mm/s |
| motor_non_drive_end_vertical_vibration | Motor Non Drive End Vertical Vibration | mm/s |
| pressure | Pressure | bar |
| pump_pressure | Pump Pressure (KG/CM²) | KG/CM² |
| tds | TDS (PPM) | PPM |
| temperature | Temperature | °C |
| vertical_vibration | Vertical Vibration | mm/s |
| voltage | Voltage | V |
| water_ph | pH | pH |
| water_temperature | Water Temperature | °C |

## 5.2 Parameter Categories

| Family | Example Keys | Typical Unit |
|--------|--------------|--------------|
| Blower vibration | `blower_drive_end_vertical`, etc. | mm/s |
| Motor vibration | `motor_drive_end_vertical`, etc. | mm/s |
| Temperatures | `blower_de_temperature`, `motor_de_temperature`, `temperature` | °C |
| Compressor (utility) | `compressor_drive_end_vertical_vibration`, etc. | mm/s |
| Water quality | `water_temperature`, `tds`, `water_ph` | °C, ppm, pH |
| DM water | `tds`, `dm_water_temperature`, `pump_pressure` | PPM, °C, KG/CM² |
| Electrical | `current`, `voltage` | A, V |
| Pressure | `pressure` | bar |

## 5.3 Full Equipment Matrix

See **`backend/reports/PARAMETER_EQUIPMENT_MATRIX.md`** (1002 rows) for Parameter Key × Equipment × Tank/Area × Tag mappings.

---

# Part 6: Google Sheets Documentation

## 6.1 Canonical Schema (17 columns)

| # | Column | Meaning | Written By | Read By |
|---|--------|---------|------------|---------|
| A | `submission_id` | UUID grouping one round-sheet submit | V2 submit | All modules |
| B | `timestamp` | Local timestamp `YYYY-MM-DD HH:MM:SS` | V2 submit | Dashboard, Reports, Trends |
| C | `area_tank` | Physical plant area (A/E/G/K Tank, Utility Area) | V2 submit | Area resolution, Trends |
| D | `category` | Config category name | V2 submit | Filters, Reports |
| E | `equipment` | Equipment display name | V2 submit | All modules |
| F | `tag_no` | Utility tag identifier | V2 submit | Utility matching |
| G | `parameter_key` | Internal parameter key | V2 submit | Trends, validation |
| H | `parameter_display_name` | Human label | V2 submit | UI display |
| I | `unit` | Engineering unit | V2 submit | Reports, Trends |
| J | `value` | Numeric reading | V2 submit | All analytics |
| K | `status` | NORMAL / WARNING / ALARM | V2 submit* | Dashboard, Reports |
| L | `verified_by` | Operator name | V2 submit | Reports, filters |
| M | `remarks` | Free text | V2 submit | Reports |
| N | `media_name` | Attachment filename | V2 submit | Audit |
| O | `media_type` | MIME type | V2 submit | Audit |
| P | `media_url` | Google Drive URL | V2 submit | Audit |
| Q | `entry_source` | e.g. "Web" | V2 submit | Audit |

*Currently all V2 submits write `NORMAL` — thresholds in config not yet wired to persist path.

## 6.2 Module Usage Mapping

| Module | Columns Used | Logic |
|--------|--------------|-------|
| Dashboard summary | value, status, equipment | Count equipment by worst status vs config total |
| Recent readings | All display columns | Sort by timestamp desc, limit N |
| Active alarms | status, equipment, parameter, timestamp | WARNING/ALARM latest params |
| Equipment health | Aggregated per equipment | Latest param rows, worst status |
| Round completion | timestamp, area, equipment | Today's unique equipment per area |
| Area health | Same + config lookups | Today-filtered status counts |
| Reports | All | Server-side filter |
| Trends | timestamp, value, parameter_key, filters | Numeric series |
| Equipment Monitoring | equipment, parameter, value, timestamp | Client aggregation |

## 6.3 Legacy Compatibility

`sheets_row_model.py` supports legacy header layouts (Title Case, GT motor schema) via `_HEADER_FIELD_ALIASES`. New writes always use canonical snake_case headers.

## 6.4 Operational Notes

- Rows inserted at **row 2** (newest first below header).
- `is_meaningful_reading_row()` filters blank/partial rows.
- Worksheet drift repair runs on service init if detected.

---

# Part 7: Dashboard Calculations

## 7.1 Health % (Area Card)

**Formula (frontend, today-scoped):**


```

tracked = count of equipment in area with ≥1 reading today
normal  = count of those with latest_status = NORMAL
healthPercent = round(normal / tracked × 100)   if tracked > 0
              = null (shows "Awaiting Today's Round") if no today readings

```


**Important:** Health % reflects **today's submitted equipment only**, not plant-wide historical health. Pending equipment (not yet read today) are excluded from the numerator and denominator.

## 7.2 Pending (Area Card)


```

pendingToday = configuredEquipmentInArea - equipmentTouchedToday

```


Equipment is "touched" if any reading row today matches equipment name or tag within that dashboard area.

## 7.3 Today's Entries (Footer)


```

todayEntryCount = count of sheet rows where timestamp is today (local calendar)

```


## 7.4 Completed Equipment (Footer)


```

todayCompletedRounds = |{ area::equipmentName }| for all today's rows
  where equipment resolves to config via matchConfiguredEquipmentInArea()

```


Unique across all areas (same name in different tanks counts separately due to area prefix).

## 7.5 Pending Round Count (Footer)


```

pendingRoundCount = Σ (configuredInArea - completedInArea) for each dashboard area

```


## 7.6 Recent Readings Selection

1. Backend returns up to 200 rows sorted by timestamp descending.
2. Frontend applies active filters + search.
3. `dedupeRecentReadings(filtered, 10)` — unique by timestamp|area|equipment|tag|parameter|value.

## 7.7 Recent Alerts Selection

1. Backend `_load_active_alarms`: all parameter rows where latest status ∈ {WARNING, ALARM}.
2. Excludes `_acknowledged_alarm_ids` (in-memory set).
3. Frontend filters + slices to 10.

## 7.8 Area Aggregation

`computeAreaSummaries()` iterates `dashboardAreaOrder` from config. For each area:

- Resolve equipment list from config (`areaEquipment` map).
- Cross-reference `equipmentHealth` API (keyed by equipment name — limitation for duplicates).
- Count normal/warning/alarm among **today's touched** equipment only.
- `deriveAreaStatus`: no today readings → PENDING; else ALARM if any alarm; else WARNING if any warning; else NORMAL.

## 7.9 Status Propagation

**Backend (historical):** For each equipment, latest row per parameter → worst status wins (`ALARM > WARNING > NORMAL`).

**Submit path:** Currently all parameters saved as `NORMAL` regardless of config thresholds.

**Legacy GT path:** `classify_value()` in `server.py` uses normal_limit and warning_limit from motor config.

## 7.10 Footer Metrics

| Metric | Source |
|--------|--------|
| Total areas | `dashboardAreaOrder.length` |
| Total equipment | `getTotalEquipmentCount(config)` |
| Total parameters | Sum of visible active parameters in config |
| Sheets connected | Any dashboard API call succeeded |
| Last refresh | Client clock on successful fetch |

## 7.11 Synchronization

- Auto-poll: 30 seconds (`REFRESH_MS` in `useDashboardData.js`).
- Manual: `fetchData()` on demand.
- Post-submit: `gmd-readings-updated` event + backend `invalidate_all_dashboard_cache()`.
- Backend cache TTL: 30–60 seconds per endpoint.

---

# Part 8: Configuration Documentation

## 8.1 Files

| File | Purpose |
|------|---------|
| `gmd_machine_config_v2.json` | Live equipment/parameter instances |
| `gmd_machine_config_v2.schema.json` | JSON Schema validation |
| `gmd_config_v2.py` | Backend config queries |
| `frontend/src/lib/gmdConfigV2.js` | Frontend config queries (mirrors backend) |

## 8.2 Hierarchy Generation


```

plants[] → categories[] → equipment[] → sections[] → groups[] → parameters[]

```


Each parameter defines: `key`, `display_name`, `display_full_label`, `unit`, `required`, `thresholds` (optional), `is_visible`, `active`.

## 8.3 Dynamic Dashboard Areas

`buildDashboardAreaOrder()`:

1. Add all plant area display names.
2. Add virtual buckets (DM Water Electrode Cooling) when equipment categories match `DM_WATER_CATEGORIES`.

## 8.4 Equipment Rendering (Add Reading)

- `getPlantAreas()` — area dropdown.
- `collectEquipmentByArea()` / `collectTagsByAreaAndKind()` — equipment/tag pickers.
- `RoundSheetForm` — renders sections/groups/parameters sorted by `display_order`.

## 8.5 No Hardcoded Equipment Philosophy

New equipment is added by editing JSON config only — no frontend code changes required for standard parameter layouts. Utility tags use `tag_no` field for disambiguation.

## 8.6 Future Scalability

- Schema supports `parameter_types`, `sheet_templates`, `validation_hooks`, `integration` blocks.
- Multi-plant ready via `plants[]` array (currently single plant).
- Threshold-driven classification can be enabled in `append_v2_readings()` by reading parameter thresholds from config.

---

# Part 9: Current Feature Checklist

## 9.1 Implemented Features

- ✅ Dashboard with area-first layout
- ✅ Add Reading (V2 round sheet)
- ✅ Equipment Monitoring
- ✅ Reports with filtering
- ✅ Trends & Analytics with charts
- ✅ Google Sheets persistence (canonical 17-column schema)
- ✅ Google Drive media upload
- ✅ Dynamic V2 configuration (87 equipment)
- ✅ Tank hierarchy (A, E, G, K)
- ✅ Utility Area with tag-based navigation
- ✅ DM Water Electrode Cooling virtual area
- ✅ Verified By and Remarks on submissions
- ✅ Relative time display on dashboard
- ✅ Today's round completion tracking
- ✅ Area health cards with pending state
- ✅ Dashboard search and cascading filters
- ✅ Alarm acknowledgement (session-scoped)
- ✅ Backend test suite (dashboard, submit, trends, sheets)
- ✅ SPA production build served from FastAPI

## 9.2 Known Limitations

- ⚠️ V2 submit does not compute WARNING/ALARM from config thresholds
- ⚠️ Alarm acknowledgement stored in memory only
- ⚠️ Equipment Monitoring uses legacy parameter names, not full V2 config
- ⚠️ Backend equipment health keyed by equipment name — duplicate names across tanks may conflate
- ⚠️ Dashboard summary OK/Warning/Alarm uses historical sheet data, not today-only (differs from area cards)
- ⚠️ Google Sheets as sole database — no offline mode or local replica
- ⚠️ No role-based authentication on API endpoints

## 9.3 Future Improvements

- Wire threshold classification into V2 submit path
- Persist alarm acknowledgements to Sheets or database
- Migrate Equipment Monitoring to V2 config-driven parameters
- Composite equipment key (area + equipment + tag) in backend aggregates
- PostgreSQL/TimescaleDB read replica for analytics performance
- OPC-UA / MQTT ingestion for live sensor data
- Email/SMS alerting on ALARM status
- Mobile-optimized round sheet with barcode tag scanning

## 9.4 Nice-to-Have Enhancements

- PDF round sheet export matching paper forms
- Shift handover report automation
- SPC/control chart overlays in Trends
- Multi-language UI
- Dark mode
- Config admin UI (instead of JSON editing)

---

# Part 10: Technical Assessment

## 10.1 Architecture Assessment — **B+**

Clean separation: React SPA, FastAPI routers, services layer, config engine. Config-driven design is appropriate for a plant with evolving equipment lists. Google Sheets as MVP storage is pragmatic but becomes the main scalability bottleneck. Legacy GT motor APIs coexist with V2 — consider deprecation path.

## 10.2 Code Quality Assessment — **B**

Consistent naming, typed Python models, shared validation for preview/submit, dedicated row model module. Frontend analytics module is well-factored but large (~900 lines). Some duplication between frontend/backend config helpers. Test coverage is good on backend; frontend tests need toolchain fix.

## 10.3 UI/UX Assessment — **B+**

Professional industrial dashboard aesthetic (Klein blue accent, zinc palette). Relative timestamps, pending states, and round banners support daily operator workflow. Utility Area tag flow matches plant practice. Equipment Monitoring UI is functional but less polished than Dashboard/Trends.

## 10.4 Scalability Assessment — **C+**

Suitable for current scale (~87 equipment, daily rounds). Sheets API rate limits and full-sheet reads will degrade with years of data. Recommend archival worksheet strategy or external time-series DB before 100k+ rows.

## 10.5 Industry 4.0 Readiness — **B-**

Strong foundation: structured parameter keys, threshold schema, REST APIs, config versioning. Gaps: no live sensor ingestion, no MES/ERP integration, no persistent alert workflow, status classification not fully automated on V2 path. Schema `integration` block anticipates future OPC-UA/MQTT.

## 10.6 Maintainability — **A-**

Single JSON config drives UI and validation — excellent for maintenance engineers. Schema file documents structure. Scripts in `backend/scripts/` support audits and config exports. Documentation package (this file) completes onboarding readiness.

## 10.7 Production Readiness — **B**

Deployable as internal plant tool with Google service account credentials. Requires: `.env` secrets, Sheets worksheet normalization, HTTPS reverse proxy, backup strategy for Sheets. Missing: auth, persistent alarms, monitoring/observability.

## 10.8 Suggested Future Roadmap

**Phase 1 (0–3 months):** Threshold classification on submit; composite equipment keys; persist alarm acks.  
**Phase 2 (3–6 months):** TimescaleDB mirror + nightly ETL; email alerts; Equipment Monitoring V2 alignment.  
**Phase 3 (6–12 months):** OPC-UA pilot on Utility compressors; anomaly detection in Trends; config admin UI.  
**Phase 4 (12+ months):** Full Industry 4.0 integration — MES dashboard embed, mobile app, predictive maintenance models.

## 10.9 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sheets API outage | No reads/writes | Cache + read replica |
| Worksheet schema drift | Data corruption | Row model + drift repair (implemented) |
| Duplicate equipment names | Wrong area assignment | Area+tag matching (implemented) |
| No authentication | Unauthorized submissions | Add plant SSO |
| All-NORMAL status on submit | False green dashboard | Wire thresholds |

## 10.10 Recommendations

1. **Priority 1:** Implement config threshold classification in `append_v2_readings()`.
2. **Priority 2:** Use composite key `area_tank|equipment|tag_no` in backend aggregates.
3. **Priority 3:** Archive readings monthly to cold storage worksheet.
4. **Priority 4:** Add lightweight auth (plant VPN + API key minimum).
5. **Priority 5:** Align Equipment Monitoring with V2 parameter keys.

---

*End of Technical Documentation — Generated 2026-06-12*
