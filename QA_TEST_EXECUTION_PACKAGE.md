# GMD Condition Monitoring Dashboard — QA Test Execution Package

**Document version:** 1.0  
**Prepared for:** Intern / single-tester execution  
**Project:** GMD Condition Monitoring Dashboard  
**Scope:** 23 test cases (Equipment Aggregation, Dashboard Summary, Active Alarms, Equipment Health, Alarm Acknowledgement)  
**Test equipment:** `MCB-1` (Category: `Blowers`)  
**Configured equipment total:** 25 (from `gmd_machine_config.json`)

---

## Table of Contents

1. [Pre-execution setup](#1-pre-execution-setup)
2. [Test data preparation guide](#2-test-data-preparation-guide)
3. [Step-by-step execution guide (23 test cases)](#3-step-by-step-execution-guide-23-test-cases)
4. [Test execution tracker](#4-test-execution-tracker)
5. [Defect logging template](#5-defect-logging-template)
6. [QA closure report template](#6-qa-closure-report-template)
7. [Deployment sign-off checklist](#7-deployment-sign-off-checklist)
8. [Evidence folder structure](#8-evidence-folder-structure)

---

## 1. Pre-execution setup

### 1.1 Tester profile

| Field | Value |
|-------|-------|
| Tester name | __________________ |
| Date started | __________________ |
| Environment tested | ☐ Local  ☐ Production |
| Browser | Chrome (recommended) |
| Screen resolution | 1920×1080 (for consistent screenshots) |

### 1.2 Environment URLs

| Resource | Local | Production |
|----------|-------|------------|
| Dashboard UI | http://localhost:3000/ | https://electrical-condition-monitoring-system.onrender.com/ |
| API base | http://127.0.0.1:8000 | https://electrical-condition-monitoring-system.onrender.com |
| Health check | `{BASE}/health` | Same |
| Swagger docs | `{BASE}/docs` | Same |
| Google Sheet | [GMD Readings Sheet](https://docs.google.com/spreadsheets/d/1BLjtK2ds_cMN5H13gkfntxL6YcKDZMyXfjlS3X54VgQ/edit) |

### 1.3 Local setup (if testing locally)

```powershell
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
$env:REACT_APP_BACKEND_URL="http://127.0.0.1:8000"
npm install
npm start
```

### 1.4 Pre-flight checklist (run before any test case)

| # | Check | Command / Action | Pass criteria |
|---|-------|------------------|---------------|
| P1 | API is alive | `curl {BASE}/health` | `"status": "ok"` |
| P2 | Sheets connected | Same response | `"sheets_enabled": true` (or equivalent true flag) |
| P3 | Dashboard ready | Same response | `"dashboard_ready": true` |
| P4 | Sheet header row | Open Google Sheet tab `Readings` | Row 1 has 10 columns: Timestamp, Category, Equipment, Parameter, Location, Value, Status, Verified By, Remarks, Entry Source |
| P5 | MCB-1 exists | Check `backend/gmd_machine_config.json` | MCB-1 listed under Blowers |
| P6 | Browser DevTools | Open F12 → Network tab | Ready to capture API calls |
| P7 | Evidence folder | Create `QA_Evidence/YYYY-MM-DD/` | Subfolders: `screenshots/`, `api-responses/`, `defects/` |

**Record pre-flight evidence:** Save `health_response.json` and screenshot `P0_health_check.png`.

### 1.5 Important testing notes

- **Status source for QA:** New bulk entries write `NORMAL` automatically. For aggregation tests, you **manually set the Status column (column G)** in Google Sheets after inserting rows, or insert rows directly in the sheet.
- **Cache delay:** Dashboard APIs cache responses for 30–60 seconds. After changing sheet data, wait up to 60 seconds **or** click **Refresh** on the dashboard, then re-call APIs.
- **Acknowledgement persistence:** Acknowledged alarms are stored **in server memory** and reset when the backend restarts. Re-run TC-ACK tests in the same session.
- **UI quirk:** Active alarm cards display a red **ALARM** badge in the UI even when the underlying status is `WARNING`. Always verify severity via API response `status` field.
- **Test isolation:** Before each Section A case, remove or archive prior `MCB-1` test rows, or use distinct timestamps so latest-per-parameter logic is unambiguous.

---

## 2. Test data preparation guide

### 2.1 Google Sheet row format (10 columns)

| Col | Field | Example |
|-----|-------|---------|
| A | Timestamp | `2026-06-08 10:00:00` |
| B | Category | `Blowers` |
| C | Equipment | `MCB-1` |
| D | Parameter | `temperature` |
| E | Location | `Plant` |
| F | Value | `42` |
| G | Status | `NORMAL` / `WARNING` / `ALARM` |
| H | Verified By | `QA Tester` |
| I | Remarks | `TC-AGG-01` |
| J | Entry Source | `QA` |

### 2.2 Parameter names used in test cases

| Parameter | Used in |
|-----------|---------|
| `temperature` | TC-AGG-01 through TC-AGG-07 |
| `current` | TC-AGG-02, 04, 05, 06 (sheet row — not in Blowers bulk-entry form) |
| `vertical_vibration` | TC-AGG-01 through TC-AGG-07 |

### 2.3 Test data sets (reference)

Use these row sets when preparing sheet data. Enter one row per parameter per timestamp.

#### DATA-SET-A (TC-AGG-01 / baseline NORMAL)

| Timestamp | Parameter | Value | Status |
|-----------|-----------|-------|--------|
| 2026-06-08 10:00:00 | temperature | 42 | NORMAL |
| 2026-06-08 10:00:00 | current | 8.5 | NORMAL |
| 2026-06-08 10:00:00 | vertical_vibration | 1.2 | NORMAL |

#### DATA-SET-B (TC-AGG-02 / one WARNING)

| Timestamp | Parameter | Value | Status |
|-----------|-----------|-------|--------|
| 2026-06-08 10:00:00 | temperature | 42 | NORMAL |
| 2026-06-08 10:00:00 | current | 12 | WARNING |
| 2026-06-08 10:00:00 | vertical_vibration | 1.2 | NORMAL |

#### DATA-SET-C (TC-AGG-03 / one ALARM)

| Timestamp | Parameter | Value | Status |
|-----------|-----------|-------|--------|
| 2026-06-08 10:00:00 | temperature | 42 | NORMAL |
| 2026-06-08 10:00:00 | current | 8.5 | NORMAL |
| 2026-06-08 10:00:00 | vertical_vibration | 8.0 | ALARM |

#### DATA-SET-D (TC-AGG-04 / WARNING + ALARM)

| Timestamp | Parameter | Value | Status |
|-----------|-----------|-------|--------|
| 2026-06-08 10:00:00 | temperature | 42 | NORMAL |
| 2026-06-08 10:00:00 | current | 12 | WARNING |
| 2026-06-08 10:00:00 | vertical_vibration | 8.0 | ALARM |

#### DATA-SET-E (TC-AGG-05 / three ALARMs)

| Timestamp | Parameter | Value | Status |
|-----------|-----------|-------|--------|
| 2026-06-08 10:00:00 | temperature | 90 | ALARM |
| 2026-06-08 10:00:00 | current | 20 | ALARM |
| 2026-06-08 10:00:00 | vertical_vibration | 9.0 | ALARM |

#### DATA-SET-F (TC-AGG-06 / missing parameter)

| Timestamp | Parameter | Value | Status |
|-----------|-----------|-------|--------|
| 2026-06-08 10:00:00 | temperature | 42 | NORMAL |
| 2026-06-08 10:00:00 | current | 12 | WARNING |

*(No `vertical_vibration` row)*

#### DATA-SET-G (TC-AGG-07 / regression: older ALARM must persist)

| Timestamp | Parameter | Value | Status |
|-----------|-----------|-------|--------|
| 2026-06-08 09:00:00 | vertical_vibration | 8.0 | ALARM |
| 2026-06-08 10:00:00 | temperature | 42 | NORMAL |
| 2026-06-08 10:00:00 | current | 8.5 | NORMAL |

### 2.4 API verification commands (replace `{BASE}`)

```powershell
# Summary
curl "{BASE}/dashboard/summary"

# Active alarms
curl "{BASE}/dashboard/active-alarms"

# Equipment health (filter for MCB-1 in response)
curl "{BASE}/dashboard/equipment-health"

# Acknowledge (replace {ALARM_ID})
curl -X POST "{BASE}/dashboard/acknowledge-alarm/{ALARM_ID}"
```

**PowerShell tip:** Pipe to file for evidence:

```powershell
curl "{BASE}/dashboard/summary" | Out-File "QA_Evidence/YYYY-MM-DD/api-responses/TC-SUM-01_summary.json"
```

---

## 3. Step-by-step execution guide (23 test cases)

### Section A — Equipment Status Aggregation (7 cases)

> **Objective:** Verify worst-status aggregation per equipment: `ALARM > WARNING > NORMAL`, using latest row per (equipment, parameter).

---

#### TC-AGG-01 — All parameters NORMAL → equipment NORMAL

| Item | Detail |
|------|--------|
| **Priority** | High |
| **Depends on** | Pre-flight P1–P7 |
| **Test data** | DATA-SET-A |

**Steps**

1. Clear or isolate prior `MCB-1` QA rows in Google Sheet.
2. Insert DATA-SET-A rows (3 rows). Confirm column G = `NORMAL` for all.
3. Wait ≤60s or click dashboard **Refresh**.
4. Call `GET {BASE}/dashboard/equipment-health`.
5. Locate object where `"equipment": "MCB-1"`.
6. Open dashboard UI at `/`.

**API verification**

```http
GET /dashboard/equipment-health
```

Expected for MCB-1:

```json
{
  "equipment": "MCB-1",
  "latest_status": "NORMAL",
  "health_percentage": 100.0
}
```

**Expected UI behavior**

- Summary cards: Normal count includes MCB-1 (exact counts depend on other equipment; with only MCB-1 non-normal absent, if MCB-1 is sole monitored deviant none — with full 25 config: `ok: 25, warning: 0, alarm: 0` if only MCB-1 has data and is NORMAL).
- Area health card for MCB-1 shows **100%** in green.
- Green banner: **"All systems normal"** (if no other equipment has WARNING/ALARM).
- Recent readings table shows three MCB-1 rows with green NORMAL badges.

**Screenshots to capture**

| File name | Content |
|-----------|---------|
| `TC-AGG-01_sheet_rows.png` | Google Sheet rows for DATA-SET-A |
| `TC-AGG-01_api_health.json` | API response excerpt for MCB-1 |
| `TC-AGG-01_dashboard.png` | Full dashboard showing MCB-1 at 100% |

**Evidence to collect**

- [ ] Sheet rows screenshot
- [ ] API JSON (MCB-1 excerpt)
- [ ] Dashboard screenshot
- [ ] Timestamp of execution

---

#### TC-AGG-02 — One WARNING → equipment WARNING

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-B |

**Steps**

1. Replace MCB-1 QA data with DATA-SET-B.
2. Wait for cache / Refresh.
3. `GET /dashboard/equipment-health` — find MCB-1.
4. Verify representative parameter is `current`.

**API verification**

```json
{
  "equipment": "MCB-1",
  "latest_status": "WARNING",
  "health_percentage": 0.0,
  "latest_parameter": "current"
}
```

**Expected UI behavior**

- MCB-1 area health card shows **0%** (red).
- Summary: `warning: 1` (assuming no other warning equipment).
- Active alarms section shows ≥1 card for MCB-1 / current.

**Screenshots**

| File name | Content |
|-----------|---------|
| `TC-AGG-02_sheet.png` | DATA-SET-B in sheet |
| `TC-AGG-02_api_health.json` | MCB-1 health response |
| `TC-AGG-02_dashboard_alarms.png` | Alarm card for MCB-1 |

**Evidence**

- [ ] API shows `latest_status: WARNING`
- [ ] `latest_parameter: current`
- [ ] UI 0% health for MCB-1

---

#### TC-AGG-03 — One ALARM → equipment ALARM (not NORMAL)

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-C |

**Steps**

1. Insert DATA-SET-C.
2. Refresh data.
3. `GET /dashboard/equipment-health` — MCB-1.
4. Confirm status is ALARM, not NORMAL or WARNING.

**API verification**

```json
{
  "equipment": "MCB-1",
  "latest_status": "ALARM",
  "health_percentage": 0.0,
  "latest_parameter": "vertical_vibration"
}
```

**Expected UI behavior**

- MCB-1 health: **0%**, red.
- Summary: `alarm: 1`, `warning: 0`.
- Active alarm card for `vertical_vibration`.

**Screenshots**

`TC-AGG-03_sheet.png`, `TC-AGG-03_api.json`, `TC-AGG-03_dashboard.png`

**Evidence**

- [ ] Status is ALARM (API + UI)
- [ ] Representative parameter = `vertical_vibration`

---

#### TC-AGG-04 — WARNING + ALARM → resolves to ALARM

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-D |

**Steps**

1. Insert DATA-SET-D (both WARNING on current and ALARM on vertical_vibration).
2. `GET /dashboard/equipment-health`.
3. Confirm worst status wins.

**API verification**

```json
{
  "equipment": "MCB-1",
  "latest_status": "ALARM",
  "latest_parameter": "vertical_vibration"
}
```

**Expected UI behavior**

- Equipment aggregates as ALARM, not WARNING.
- Summary: `alarm: 1`, `warning: 0` (one equipment counts once).
- Two active alarm cards at parameter level (current/WARNING + vertical_vibration/ALARM).

**Screenshots**

`TC-AGG-04_api_summary.json`, `TC-AGG-04_api_alarms.json`, `TC-AGG-04_dashboard.png`

**Evidence**

- [ ] `latest_status` = ALARM
- [ ] Summary counts 1 alarm, 0 warning
- [ ] Two parameter-level alarm records in active-alarms API

---

#### TC-AGG-05 — Multiple ALARM parameters → still ALARM

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-E |

**Steps**

1. Insert DATA-SET-E (all three parameters ALARM).
2. Verify aggregation and alarm list count.

**API verification**

- MCB-1: `"latest_status": "ALARM"`
- `GET /dashboard/active-alarms` returns **3** records for MCB-1 (temperature, current, vertical_vibration).

**Expected UI behavior**

- Three alarm cards visible for MCB-1.
- Summary: `alarm: 1` (equipment-level).

**Screenshots**

`TC-AGG-05_active_alarms.json`, `TC-AGG-05_three_cards.png`

**Evidence**

- [ ] 3 active alarm API records
- [ ] 1 equipment in alarm summary count

---

#### TC-AGG-06 — Missing parameter does not break aggregation

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-F (no vibration row) |

**Steps**

1. Insert only temperature + current rows.
2. Verify no errors in API or UI.
3. Confirm aggregation uses available parameters only.

**API verification**

```json
{
  "equipment": "MCB-1",
  "latest_status": "WARNING",
  "latest_parameter": "current"
}
```

**Expected UI behavior**

- No crash, no blank dashboard.
- MCB-1 shows WARNING state.
- No errors in browser console (F12 → Console).

**Screenshots**

`TC-AGG-06_api.json`, `TC-AGG-06_console.png` (console tab, no red errors)

**Evidence**

- [ ] API 200 OK
- [ ] WARNING despite missing vibration
- [ ] No JS errors

---

#### TC-AGG-07 — Regression: newer NORMAL rows must not hide older ALARM

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-G |

**Steps**

1. Insert ALARM row at **09:00** for vertical_vibration.
2. Insert NORMAL rows at **10:00** for temperature and current.
3. Verify per-parameter latest: vibration still ALARM at 09:00 (only row); temperature/current NORMAL at 10:00.
4. Equipment aggregate must remain ALARM.

**API verification**

```json
{
  "equipment": "MCB-1",
  "latest_status": "ALARM",
  "latest_parameter": "vertical_vibration",
  "latest_timestamp": "2026-06-08 10:00:00"
}
```

Note: `latest_timestamp` reflects the **most recent reading across all parameters** (10:00), while status remains ALARM from vibration.

**Expected UI behavior**

- MCB-1 shows 0% health, ALARM state.
- `last_updated` on card reflects recent activity (e.g., "Updated Today").

**Screenshots**

`TC-AGG-07_sheet_timestamps.png`, `TC-AGG-07_api.json`, `TC-AGG-07_area_health_card.png`

**Evidence**

- [ ] Status ALARM despite newer NORMAL params
- [ ] `latest_timestamp` = 10:00:00

---

### Section B — Dashboard Summary (4 cases)

> **Objective:** Verify `GET /dashboard/summary` counts match UI summary cards.  
> **Precondition:** Use DATA-SET from referenced TC-AGG case.

---

#### TC-SUM-01 — Summary when MCB-1 fully NORMAL

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-A (after TC-AGG-01) |

**Steps**

1. Ensure DATA-SET-A is active.
2. `GET {BASE}/dashboard/summary`.
3. Open dashboard `/` — read four summary cards.

**API verification**

```json
{
  "total": 25,
  "ok": 25,
  "warning": 0,
  "alarm": 0
}
```

**Expected UI behavior**

| Card | Label | Value |
|------|-------|-------|
| 1 | Total equipment | 25 |
| 2 | Normal | 25 |
| 3 | Warning | 0 |
| 4 | Alarm | 0 |

**Screenshots**

`TC-SUM-01_api.json`, `TC-SUM-01_summary_cards.png`

**Evidence**

- [ ] API numbers match UI exactly
- [ ] `total` always 25 (from config, not row count)

---

#### TC-SUM-02 — Summary counts one WARNING

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-B |

**API verification**

```json
{ "total": 25, "ok": 24, "warning": 1, "alarm": 0 }
```

**Expected UI**

- Warning card = **1**, Normal = **24**.

**Screenshots**

`TC-SUM-02_api.json`, `TC-SUM-02_cards.png`

**Evidence**

- [ ] `ok` = 24, `warning` = 1

---

#### TC-SUM-03 — Summary counts one ALARM

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-C |

**API verification**

```json
{ "total": 25, "ok": 24, "warning": 0, "alarm": 1 }
```

**Expected UI**

- Alarm card = **1**.

**Screenshots**

`TC-SUM-03_api.json`, `TC-SUM-03_cards.png`

---

#### TC-SUM-04 — WARNING + ALARM on same equipment = 1 alarm

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-D |

**API verification**

```json
{ "total": 25, "ok": 24, "warning": 0, "alarm": 1 }
```

**Expected UI**

- Equipment counted once in Alarm, not Warning.
- Warning card = **0**, Alarm card = **1**.

**Screenshots**

`TC-SUM-04_api.json`, `TC-SUM-04_cards.png`

**Evidence**

- [ ] No double-count across warning + alarm on same equipment

---

### Section C — Active Alarms (4 cases)

> **Objective:** Verify parameter-level alarm listing and stable `id` fields.

---

#### TC-ALM-01 — No active alarms when all NORMAL

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-A |

**Steps**

1. Ensure all MCB-1 statuses NORMAL; no other equipment in WARNING/ALARM.
2. `GET /dashboard/active-alarms`.
3. View dashboard alarm banner.

**API verification**

```json
[]
```

**Expected UI behavior**

- Green banner: **"All systems normal"**
- Subtext: **"No active alarms on monitored equipment"**
- No alarm cards rendered.

**Screenshots**

`TC-ALM-01_api.json`, `TC-ALM-01_green_banner.png`

**Evidence**

- [ ] Empty array from API
- [ ] Green all-normal banner visible

---

#### TC-ALM-02 — One WARNING → one alarm card

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-B |

**Steps**

1. Load DATA-SET-B.
2. `GET /dashboard/active-alarms`.
3. Count records; verify each has non-empty `id`.

**API verification**

- Array length = **1**
- Record:

```json
{
  "equipment": "MCB-1",
  "parameter": "current",
  "status": "WARNING",
  "id": "<16-char hex string>"
}
```

**Expected UI behavior**

- One alarm card showing MCB-1, parameter current, value 12.
- **Acknowledge** button visible.

**Screenshots**

`TC-ALM-02_api.json`, `TC-ALM-02_card.png`

**Evidence**

- [ ] Exactly 1 alarm
- [ ] `id` present and non-empty

---

#### TC-ALM-03 — WARNING + ALARM → two parameter cards

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-D |

**API verification**

- Array length = **2**
- Records include:
  - MCB-1 / current / WARNING
  - MCB-1 / vertical_vibration / ALARM

**Expected UI behavior**

- Two cards in active alarms grid.
- Both show Acknowledge button.

**Screenshots**

`TC-ALM-03_api.json`, `TC-ALM-03_two_cards.png`

**Evidence**

- [ ] 2 distinct `id` values
- [ ] Correct parameters in each card

---

#### TC-ALM-04 — Three ALARM parameters → three cards

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-E |

**API verification**

- Array length = **3**
- Parameters: temperature, current, vertical_vibration — all `status: ALARM`

**Expected UI behavior**

- Three alarm cards visible.

**Screenshots**

`TC-ALM-04_api.json`, `TC-ALM-04_three_cards.png`

**Evidence**

- [ ] 3 API records, 3 UI cards

---

### Section D — Equipment Health (4 cases)

> **Objective:** Verify per-equipment health metrics in `GET /dashboard/equipment-health`.

---

#### TC-EH-01 — MCB-1 health when aggregated NORMAL

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-A |

**API verification** (MCB-1 object)

```json
{
  "latest_status": "NORMAL",
  "health_percentage": 100.0
}
```

**Expected UI behavior**

- Area health card: **100%** green.
- OK/Warn/Alarm counts reflect historical rows.

**Screenshots**

`TC-EH-01_api.json`, `TC-EH-01_card.png`

---

#### TC-EH-02 — MCB-1 health when aggregated WARNING

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-B |

**API verification**

```json
{
  "latest_status": "WARNING",
  "health_percentage": 0.0,
  "latest_parameter": "current"
}
```

**Expected UI behavior**

- Health card shows **0%** in red.

**Screenshots**

`TC-EH-02_api.json`, `TC-EH-02_card.png`

---

#### TC-EH-03 — MCB-1 health when aggregated ALARM

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-D |

**API verification**

```json
{
  "latest_status": "ALARM",
  "health_percentage": 0.0,
  "latest_parameter": "vertical_vibration"
}
```

**Expected UI behavior**

- 0% health, representative param shown in API.

**Screenshots**

`TC-EH-03_api.json`, `TC-EH-03_card.png`

---

#### TC-EH-04 — `last_updated` reflects most recent timestamp

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-G |

**Steps**

1. Load DATA-SET-G.
2. Find MCB-1 in equipment-health response.
3. Compare `latest_timestamp` / `last_updated` with sheet.

**API verification**

```json
{
  "latest_status": "ALARM",
  "latest_timestamp": "2026-06-08 10:00:00",
  "last_updated": "Updated Today"
}
```

**Expected UI behavior**

- Card subtitle shows recent update (e.g., "Updated Today").
- Status remains ALARM.

**Screenshots**

`TC-EH-04_api.json`, `TC-EH-04_card_timestamp.png`, `TC-EH-04_sheet.png`

**Evidence**

- [ ] `latest_timestamp` matches newest row (10:00)
- [ ] Status still ALARM

---

### Section E — Alarm Acknowledgement (4 cases)

> **Objective:** Verify acknowledge API, UI refresh, correct endpoint, and missing-id guard.

---

#### TC-ACK-01 — Acknowledge API accepts valid alarm id

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-B |
| **Precondition** | TC-ALM-02 passed; alarm id captured |

**Steps**

1. `GET /dashboard/active-alarms` — copy `id` from MCB-1/current record.
2. `POST /dashboard/acknowledge-alarm/{id}`.
3. Record HTTP status and body.

**API verification**

```http
POST /dashboard/acknowledge-alarm/abc123def4567890
```

Expected response (200):

```json
{
  "status": "ok",
  "id": "abc123def4567890"
}
```

**Expected UI behavior**

- N/A for this step (API-only); UI covered in TC-ACK-02.

**Screenshots**

`TC-ACK-01_post_response.json` (or Postman screenshot)

**Evidence**

- [ ] HTTP 200
- [ ] `status: ok` in body
- [ ] Same `id` echoed back

---

#### TC-ACK-02 — Acknowledged card disappears after refresh

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-D (2 alarms) recommended |

**Steps**

1. Load DATA-SET-D — confirm 2 alarm cards.
2. Click **Acknowledge** on one card only.
3. Wait for auto-refresh or click **Refresh**.
4. `GET /dashboard/active-alarms` — count remaining.

**API verification**

- Acknowledged alarm absent from active-alarms array.
- Other alarm still present.

**Expected UI behavior**

- Acknowledged card removed.
- Remaining card still visible.

**Screenshots**

`TC-ACK-02_before.png`, `TC-ACK-02_after.png`, `TC-ACK-02_api_after.json`

**Evidence**

- [ ] Card count reduced by 1
- [ ] Unacknowledged alarm persists

---

#### TC-ACK-03 — Frontend calls correct endpoint

| Item | Detail |
|------|--------|
| **Test data** | DATA-SET-B (fresh, unacknowledged) |

**Steps**

1. Open DevTools → **Network** tab → filter `acknowledge`.
2. Clear prior acknowledgements (use new alarm or restart backend).
3. Click **Acknowledge** on MCB-1 card.
4. Inspect request URL and method.

**API verification**

- Request: `POST {BASE}/dashboard/acknowledge-alarm/{id}`
- Must **NOT** be legacy `/acknowledge-alarm/` (without `/dashboard/` prefix).

**Expected UI behavior**

- Card disappears after successful POST.
- No error toast/console `POST FAILED`.

**Screenshots**

`TC-ACK-03_network_tab.png` showing full URL

**Evidence**

- [ ] Correct endpoint path
- [ ] POST method
- [ ] 200 response

---

#### TC-ACK-04 — Missing `id` does not send broken request

| Item | Detail |
|------|--------|
| **Type** | Edge case / code inspection + simulated test |

**Steps (option A — code review)**

1. Open `frontend/src/pages/Dashboard.js`.
2. Confirm guard: `if (!alarmId) { console.error(...); return; }`.
3. Document line reference in evidence.

**Steps (option B — simulated test)**

1. In browser console on dashboard, if possible invoke acknowledge with null id (or inspect that buttons always pass `alarm.id`).
2. Confirm Network tab shows **no** POST to `.../undefined`.

**API verification**

- No `POST /dashboard/acknowledge-alarm/undefined`
- Server remains healthy: `GET /health` → ok

**Expected UI behavior**

- Console error: `Cannot acknowledge alarm without id`
- No UI crash.

**Screenshots**

`TC-ACK-04_console.png`, `TC-ACK-04_network_no_post.png`

**Evidence**

- [ ] No broken POST
- [ ] Server health unchanged

---

## 4. Test execution tracker

Copy this table into your execution workbook or print it. Update after each test case.

| Test Case | Title | Status | Evidence | Remarks |
|-----------|-------|--------|----------|---------|
| TC-AGG-01 | All parameters NORMAL → equipment NORMAL | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-AGG-02 | One WARNING → equipment WARNING | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-AGG-03 | One ALARM → equipment ALARM | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-AGG-04 | WARNING + ALARM → ALARM | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-AGG-05 | Multiple ALARMs → ALARM | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-AGG-06 | Missing parameter — no break | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-AGG-07 | Newer NORMAL must not hide ALARM | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-SUM-01 | Summary — all NORMAL | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-SUM-02 | Summary — one WARNING | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-SUM-03 | Summary — one ALARM | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-SUM-04 | Same equipment — counts as 1 alarm | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ALM-01 | No alarms when all NORMAL | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ALM-02 | One WARNING → one card | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ALM-03 | WARNING + ALARM → two cards | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ALM-04 | Three ALARMs → three cards | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-EH-01 | Health 100% when NORMAL | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-EH-02 | Health 0% when WARNING | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-EH-03 | Health 0% when ALARM | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-EH-04 | last_updated reflects latest timestamp | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ACK-01 | Acknowledge API 200 OK | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ACK-02 | Card disappears after ack | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ACK-03 | Correct frontend endpoint | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ACK-04 | Missing id — no broken POST | ☐ Pass ☐ Fail ☐ Blocked | | |

### Summary counts (fill when complete)

| Metric | Count |
|--------|-------|
| Total test cases | 23 |
| Passed | |
| Failed | |
| Blocked | |
| Not executed | |
| Pass rate | % |

---

## 5. Defect logging template

Copy one block per defect found. Save as `QA_Evidence/YYYY-MM-DD/defects/DEF-XXX.md` or log in your issue tracker.

---

### Defect ID: DEF-___

| Field | Value |
|-------|-------|
| **Title** | Short one-line summary |
| **Reported by** | |
| **Date reported** | |
| **Environment** | ☐ Local ☐ Production |
| **Severity** | ☐ Critical ☐ High ☐ Medium ☐ Low |
| **Priority** | ☐ P1 ☐ P2 ☐ P3 ☐ P4 |
| **Status** | ☐ New ☐ Open ☐ Fixed ☐ Retest ☐ Closed |
| **Related test case** | e.g., TC-AGG-04 |
| **Component** | ☐ Backend API ☐ Frontend UI ☐ Google Sheets ☐ Aggregation ☐ Acknowledgement ☐ Other |

**Description**

What happened? Describe observed behavior in plain language.

**Steps to reproduce**

1. 
2. 
3. 

**Expected result**

(From test case specification)

**Actual result**

(What you observed)

**API evidence**

```
HTTP method + URL:
Status code:
Response body (paste or attach):
```

**UI evidence**

- Screenshot file name(s): 
- Browser / version: 
- Console errors (if any): 

**Impact**

Who is affected? Can testing continue? Deployment blocker?

**Workaround (if any)**

**Retest result (after fix)**

| Retest date | Tester | Test case | Result |
|-------------|--------|-----------|--------|
| | | | ☐ Pass ☐ Fail |

**Closure notes**

---

## 6. QA closure report template

Fill this report when all 23 test cases have been executed (or explicitly deferred). Submit to QA Lead / Manager with the `QA_Evidence/` folder.

---

# QA Closure Report — GMD Condition Monitoring Dashboard

| Field | Value |
|-------|-------|
| **Report date** | |
| **Tester name** | |
| **Reviewer / QA Lead** | |
| **Build / release version** | v1.0.0 |
| **Environment** | ☐ Local ☐ Production ☐ Both |
| **Test period** | Start: ______ → End: ______ |
| **Documentation reference** | QA_TEST_EXECUTION_PACKAGE.md v1.0 |

---

### 1. Executive summary

_(2–4 sentences: overall quality assessment, readiness recommendation, major risks.)_

---

### 2. Test scope

| Area | Test cases | Description |
|------|------------|-------------|
| Equipment status aggregation | TC-AGG-01 – 07 | Worst-status logic per equipment |
| Dashboard summary | TC-SUM-01 – 04 | Count accuracy vs UI |
| Active alarms | TC-ALM-01 – 04 | Parameter-level alarm listing |
| Equipment health | TC-EH-01 – 04 | Health %, timestamps, representative param |
| Alarm acknowledgement | TC-ACK-01 – 04 | API, UI, endpoint, edge cases |
| **Total** | **23** | |

**Out of scope for this cycle:** GT legacy APIs (`/machine-health`, `/condition-monitoring/bulk` strict mode), Trends, Reports, Bulk Entry validation (unless defects found during setup).

---

### 3. Test results summary

| Result | Count | % |
|--------|-------|---|
| Pass | | |
| Fail | | |
| Blocked | | |
| Not executed | | |
| **Total** | 23 | 100% |

---

### 4. Defects summary

| Defect ID | Severity | Title | Status | Blocker? |
|-----------|----------|-------|--------|----------|
| | | | | ☐ |
| | | | | ☐ |

**Open critical/high defects:** ___

---

### 5. Requirements traceability

| Requirement | Test cases | Status |
|-------------|------------|--------|
| Equipment status uses worst parameter status | TC-AGG-01 – 07 | ☐ Met ☐ Not met |
| Dashboard summary reflects aggregation | TC-SUM-01 – 04 | ☐ Met ☐ Not met |
| Active alarms list parameter-level issues | TC-ALM-01 – 04 | ☐ Met ☐ Not met |
| Equipment health metrics accurate | TC-EH-01 – 04 | ☐ Met ☐ Not met |
| Alarms can be acknowledged from dashboard | TC-ACK-01 – 04 | ☐ Met ☐ Not met |

---

### 6. Known limitations observed (not defects)

| # | Limitation | Noted in |
|---|------------|----------|
| 1 | Acknowledgements reset on server restart | RELEASE_NOTES |
| 2 | UI alarm badge always red "ALARM" even for WARNING | Dashboard.js |
| 3 | Dashboard API cache 30–60s | dashboard.py |
| 4 | Bulk entry writes NORMAL; QA uses manual Status | google_sheets_service |

---

### 7. Evidence package checklist

| Item | Included? |
|------|-----------|
| Pre-flight health check | ☐ |
| All API response files | ☐ |
| All required screenshots | ☐ |
| Completed execution tracker (Section 4) | ☐ |
| Defect logs (if any) | ☐ |
| Network capture for TC-ACK-03 | ☐ |

**Evidence folder path:** `QA_Evidence/YYYY-MM-DD/`

---

### 8. Risks and recommendations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| | | | |

---

### 9. QA recommendation

Select one:

- ☐ **Approve for deployment** — All critical/high tests passed; no open P1 defects.
- ☐ **Approve with conditions** — Minor issues documented; acceptable for release with noted limitations.
- ☐ **Do not approve** — Critical failures or open blockers remain.

**Sign-off**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Tester | | | |
| QA Lead | | | |
| Project Manager | | | |

---

## 7. Deployment sign-off checklist

Use this checklist for deployment approval after QA closure. Each item requires evidence or explicit sign-off.

### 7.1 Pre-deployment verification

| # | Item | Owner | Done | Evidence |
|---|------|-------|------|----------|
| D1 | QA closure report approved | QA Lead | ☐ | Closure report §9 |
| D2 | All 23 test cases Pass or accepted waiver | QA Lead | ☐ | Execution tracker |
| D3 | Zero open P1/P2 defects (or waivers documented) | PM | ☐ | Defect log |
| D4 | `GET /health` returns `status: ok` on target env | DevOps | ☐ | health_response.json |
| D5 | `dashboard_ready: true` on target env | DevOps | ☐ | health_response.json |
| D6 | Google Sheets enabled and connected | DevOps | ☐ | health + sample API call |
| D7 | Frontend build included in deploy (`build.sh`) | DevOps | ☐ | RENDER_BUILD.md / deploy log |
| D8 | Environment variables set (see `.env.example`) | DevOps | ☐ | Render dashboard screenshot |
| D9 | `GOOGLE_SERVICE_ACCOUNT_JSON` configured (Render secret) | DevOps | ☐ | Secret configured (no value pasted) |
| D10 | CORS origins appropriate for production | DevOps | ☐ | Config review |

### 7.2 Functional smoke test (post-deploy, 15 minutes)

| # | Check | Command / URL | Expected | Done |
|---|-------|---------------|----------|------|
| S1 | Health | `GET /health` | 200, status ok | ☐ |
| S2 | Summary | `GET /dashboard/summary` | JSON with total=25 | ☐ |
| S3 | Active alarms | `GET /dashboard/active-alarms` | 200, array | ☐ |
| S4 | Equipment health | `GET /dashboard/equipment-health` | 200, array | ☐ |
| S5 | Dashboard UI loads | `/` | No blank page | ☐ |
| S6 | Bulk Entry loads | `/add-reading` | Form renders | ☐ |
| S7 | Equipment Monitoring loads | `/equipment-monitoring` | Page renders | ☐ |
| S8 | Reports loads | `/reports` | Page renders | ☐ |
| S9 | Trends loads | `/trends-analytics` | Page renders | ☐ |
| S10 | Swagger docs | `/docs` | OpenAPI UI loads | ☐ |

### 7.3 Production configuration checklist

| Variable | Required | Verified |
|----------|----------|----------|
| `GOOGLE_SHEETS_ENABLED=true` | Yes | ☐ |
| `GOOGLE_SHEET_ID` | Yes | ☐ |
| `GOOGLE_SHEET_WORKSHEET` | Yes (default: Readings) | ☐ |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Yes (production) | ☐ |
| `DASHBOARD_CACHE_TTL_SECONDS` | Optional (30–60) | ☐ |
| `CORS_ORIGINS` | Recommended review | ☐ |

### 7.4 Rollback readiness

| # | Item | Done |
|---|------|------|
| R1 | Previous deploy tag / commit ID documented | ☐ |
| R2 | Rollback procedure reviewed (`PRODUCTION_RELEASE.md`) | ☐ |
| R3 | Sheet data backup or version history accessible | ☐ |

### 7.5 Final deployment approval

| Role | Name | Approve ☐ / Reject ☐ | Date | Comments |
|------|------|----------------------|------|----------|
| QA Lead | | | | |
| Technical Lead | | | | |
| Project Manager | | | | |
| Deployment Engineer | | | | |

**Deployment target URL:** https://electrical-condition-monitoring-system.onrender.com/

**Approved deployment window:** __________________

---

## 8. Evidence folder structure

Create this structure before starting:

```
QA_Evidence/
└── YYYY-MM-DD/
    ├── screenshots/
    │   ├── TC-AGG-01_dashboard.png
    │   ├── TC-SUM-01_summary_cards.png
    │   └── ...
    ├── api-responses/
    │   ├── P0_health_response.json
    │   ├── TC-AGG-01_api_health.json
    │   └── ...
    ├── network/
    │   └── TC-ACK-03_network_tab.png
    ├── defects/
    │   └── DEF-001.md
    ├── QA_EXECUTION_TRACKER.xlsx   (optional copy of Section 4)
    └── QA_CLOSURE_REPORT.md        (filled Section 6)
```

---

## Recommended execution order

For fastest path with minimal sheet resets:

1. Pre-flight P1–P7  
2. TC-AGG-01 → TC-SUM-01 → TC-ALM-01 → TC-EH-01  
3. TC-AGG-02 → TC-SUM-02 → TC-ALM-02 → TC-EH-02 → TC-ACK-01, 02, 03  
4. TC-AGG-03 → TC-SUM-03 → TC-ALM-03 (partial)  
5. TC-AGG-04 → TC-SUM-04 → TC-ALM-03 → TC-EH-03 → TC-ACK-02 (two cards)  
6. TC-AGG-05 → TC-ALM-04  
7. TC-AGG-06 → TC-AGG-07 → TC-EH-04  
8. TC-ACK-04 (independent)  
9. Complete closure report + deployment checklist  

**Estimated effort:** 6–8 hours for a first-time intern (including evidence capture).

---

*End of QA Test Execution Package*
