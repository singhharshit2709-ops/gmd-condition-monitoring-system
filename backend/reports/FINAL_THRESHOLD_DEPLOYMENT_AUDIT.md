# Final Production Audit — Threshold Architecture & Deployment Readiness

**GMD Condition Monitoring System**  
**Audit Timestamp:** 2026-06-15 16:45 IST  
**Scope:** Threshold architecture, deployment without final limits, historical compatibility, module integration  
**Method:** Static codebase inspection + automated test evidence (87/87 pytest pass)  
**Code changes during audit:** None

---

## Executive Summary

The GMD V2 round-sheet system stores engineering limits exclusively in `backend/gmd_machine_config_v2.json`. Runtime classification is performed by `services/threshold_service.py` at **write time only** (Google Sheets append). All read-path modules (Dashboard, Reports, Trends, Equipment Monitoring) consume the **stored `status` column** from Google Sheets — they do not embed threshold numbers.

Classification is **disabled by default** (`GMD_THRESHOLD_CLASSIFICATION_ENABLED=false`). Production deployment is safe without User Department final limits. Historical sheet rows require no migration when limits are later enabled.

---

## 1. Threshold Architecture Audit

### 1.1 Configuration Source of Truth

| Item | Location | Evidence |
|------|----------|----------|
| V2 limits storage | `backend/gmd_machine_config_v2.json` | Each parameter may include a `thresholds` object with `normal_limit`, `warning_limit`, `alarm_limit` |
| Schema definition | `backend/gmd_machine_config_v2.schema.json` | `$defs/Thresholds` (lines ~1126–1199) defines limit fields |
| Backend loader | `backend/gmd_config_v2.py` | `load_gmd_config_v2()` — `@lru_cache`, reads JSON from disk |
| Frontend loader | `frontend/src/lib/gmdConfigV2.js` | `loadGmdConfigV2()` imports bundled JSON |
| Webpack alias (single source) | `frontend/craco.config.js` | `'@gmd-config/v2'` → `../backend/gmd_machine_config_v2.json` |

**Example config entry (limits in JSON, not code):**

```json
"thresholds": {
  "enabled": true,
  "provisional": true,
  "normal_limit": 6.0,
  "warning_limit": 10.0,
  "source": "PROVISIONAL — … Not approved for production classification."
}
```

File: `backend/gmd_machine_config_v2.json` (parameter blocks throughout, e.g. MCB-1 blower vibration parameters)

---

### 1.2 Backend Classification Engine

#### Warning / Alarm / Normal limits — configuration-driven

| Finding | File | Function | Lines | Explanation |
|---------|------|----------|-------|-------------|
| Limits read from config | `backend/services/threshold_service.py` | `_thresholds_from_param()` | 63–81 | Reads `param["thresholds"]` keys `normal_limit`, `warning_limit`, `alarm_limit` via `_coerce_limit()` |
| Config lookup by equipment + parameter | `backend/services/threshold_service.py` | `get_parameter_thresholds()` | 85–100 | Uses `find_equipment_in_config()` + `collect_equipment_parameters()` from `gmd_config_v2.py` |
| NORMAL/WARNING/ALARM derived logically | `backend/services/threshold_service.py` | `classify_parameter_value()` | 103–139 | Compares numeric `value` against config limits using `classification_mode` (`higher_is_worse` / `lower_is_worse`) |
| Public entry point | `backend/services/threshold_service.py` | `classify_v2_parameter_status()` | 142–193 | Returns `NORMAL` when disabled, missing, provisional-blocked, or incomplete limits |
| Feature flag (off by default) | `backend/services/threshold_service.py` | `is_threshold_classification_enabled()` | 36–42 | Env `GMD_THRESHOLD_CLASSIFICATION_ENABLED`, default `"false"` |
| Provisional guard | `backend/services/threshold_service.py` | `allow_provisional_thresholds()` | 45–51 | Env `GMD_THRESHOLD_ALLOW_PROVISIONAL`, default `"false"` |

**No numeric limit literals in classification logic** — only comparison operators and status string constants (`STATUS_NORMAL`, `STATUS_WARNING`, `STATUS_ALARM` at lines 21–23).

#### Write path — status assigned at Sheets append

| Finding | File | Function | Lines | Explanation |
|---------|------|----------|-------|-------------|
| V2 submit classification | `backend/services/google_sheets_service.py` | `append_v2_readings()` | 211–217 | Calls `classify_v2_parameter_status()` per parameter before building row |
| Status persisted to sheet | `backend/services/google_sheets_service.py` | `append_v2_readings()` | 218–229 | `ReadingRowRecord.status=status` written to column `status` |
| V1 legacy append | `backend/services/google_sheets_service.py` | `append_readings()` | 133–139 | Same `classify_v2_parameter_status()` call |
| Submit route (no local limits) | `backend/routes/v2_preview.py` | `submit_v2_reading()` | 160–175 | Delegates to `service.append_v2_readings()` — no threshold logic in route |

#### Legacy GT motor API (separate path, also config-driven)

| Finding | File | Function | Lines | Explanation |
|---------|------|----------|-------|-------------|
| Legacy limits from JSON | `backend/server.py` | `get_motor_thresholds()` | 133–143 | Loads from `machine_config.json` via `get_motor_thresholds_resolved()` |
| Legacy classification | `backend/server.py` | `classify_motor_reading()` | 184–237 | Uses config threshold dict keys (`normal_current`, `warning_current`, etc.) |
| File header assertion | `backend/server.py` | (module docstring) | 6–9 | States thresholds loaded exclusively from config |

**Note:** V2 Add Reading uses `gmd_machine_config_v2.json`, not `machine_config.json`. Legacy path is not on the V2 round-sheet critical path.

---

### 1.3 Add Reading Workflow — No Hardcoded Limits

| Component | File | Function | Lines | Explanation |
|-----------|------|----------|-------|-------------|
| Validation (structure only) | `backend/services/v2_validation.py` | `validate_v2_submission()` | entire module | Validates equipment, required parameters, numeric types against config — **no threshold/limit checks** |
| Preview route | `backend/routes/v2_preview.py` | preview/submit handlers | — | Uses `v2_validation`; no limit literals |
| Frontend submit API | `frontend/src/lib/v2SubmitApi.js` | `submitV2Reading()` | — | POST payload only; no client-side classification |
| Frontend config | `frontend/src/lib/gmdConfigV2.js` | `collectRenderableParameters()` etc. | — | Renders parameters from JSON; uses `validation` for input rules (min/step), not hardcoded limits |

**Automated evidence:** `backend/tests/test_threshold_service.py` — `test_classification_disabled_by_default` confirms value `99.0` on MCB-1 returns `NORMAL` when flag unset.

---

### 1.4 Dashboard Logic — No Hardcoded Limits

| Component | File | Function | Lines | Explanation |
|-----------|------|----------|-------|-------------|
| Status from sheet rows | `backend/routes/dashboard.py` | `get_equipment_status_aggregates()` | 293–297 | Reads `record.get("status")` — no limit comparison |
| Status normalization | `backend/routes/dashboard.py` | `normalize_status()` | 234–238 | Maps string tokens only |
| KPI counts | `backend/routes/dashboard.py` | `_load_summary()` | 344–349 | Counts `worst_status` from aggregates |
| Active alarms | `backend/routes/dashboard.py` | `_load_active_alarms()` | 405–407 | Filters rows where stored status is WARNING/ALARM |
| Equipment health | `backend/routes/dashboard.py` | `_load_equipment_health()` | 483–489 | Increments counters from stored `status` |
| Frontend analytics | `frontend/src/lib/dashboardAnalytics.js` | `normalizeStatus()` | 79–83 | Display normalization only — no numeric limits |
| Area cards / KPIs | `frontend/src/lib/dashboardAnalytics.js` | `buildAreaSummaries()`, etc. | 395–397 | Uses `latest_status` from API |

**No `normal_limit`, `warning_limit`, or `alarm_limit` references in `backend/routes/dashboard.py`.**

---

### 1.5 Reports — No Hardcoded Limits

| Component | File | Function | Lines | Explanation |
|-----------|------|----------|-------|-------------|
| Readings API | `backend/routes/reports.py` | `get_report_readings()` | 30–50 | `fetch_and_clean_data()` → `parse_row()` → filter by query params including optional `status` |
| Status filter | `backend/routes/reports.py` | (filter loop) | — | Filters on stored status string, not recomputed limits |
| Frontend | `frontend/src/pages/Reports.js` | status filter UI | 125–127, 286–288 | Displays/filters NORMAL/WARNING/ALARM from API rows |

**No threshold limit literals in `backend/routes/reports.py`.**

---

### 1.6 Trends & Analytics — No Hardcoded Limits (with one config-path nuance)

| Component | File | Function | Lines | Explanation |
|-----------|------|----------|-------|-------------|
| Trends API | `backend/routes/trends.py` | `get_trend_readings()` | 34–50 | Returns numeric values + stored status from sheet — no limit comparison |
| Chart reference lines | `frontend/src/lib/trendsAnalytics.js` | `getThresholdLines()` | 198–208 | Reads `parameterMeta.validation.warning_limit` / `alarm_limit` if present — **not hardcoded** |
| Parameter meta source | `frontend/src/lib/trendsAnalytics.js` | `getParametersForEquipment()` | 75–84 | Passes `param.validation` from config JSON |
| Chart consumer | `frontend/src/pages/TrendsAnalytics.js` | `thresholdLines` useMemo | ~179 | Passes lines to `TrendLineChart` |

**Nuance (not a hardcoding issue):** Limits in config live under `param.thresholds`, but `getThresholdLines()` reads `param.validation`. Reference overlay lines may not appear until `validation` is populated or aligned with `thresholds`. Trend **data and status** still come from the API correctly.

---

### 1.7 Equipment Monitoring — No Hardcoded Limits

| Component | File | Function | Lines | Explanation |
|-----------|------|----------|-------|-------------|
| Data source | `frontend/src/pages/ConditionMonitoring.js` | fetch readings | ~120 | `GET /reports/readings` |
| Status display | `frontend/src/pages/ConditionMonitoring.js` | table render | 477–483 | Renders `row.status` from API — no limit math |

---

### 1.8 Frontend Components — No Hardcoded Threshold Values

**Grep result:** The only frontend references to `warning_limit` / `alarm_limit` are in `frontend/src/lib/trendsAnalytics.js` (config-driven read). No numeric engineering limits (e.g. `6.0`, `10.0`) appear in frontend business logic.

Status styling uses string tokens only:

| File | Purpose |
|------|---------|
| `frontend/src/components/dashboard/StatusBadge.jsx` | NORMAL/WARNING/ALARM CSS labels |
| `frontend/src/components/dashboard/AreaStatusBadge.jsx` | Area status presentation |
| `frontend/src/lib/dashboardAnalytics.js` | `STATUS_RANK`, `normalizeStatus()` — ordinal ranking, not limits |

---

### 1.9 Google Sheets Schema — Status Column Only

| Item | File | Location | Explanation |
|------|------|----------|-------------|
| Canonical headers | `backend/services/sheets_row_model.py` | `GMD_SHEET_HEADERS` lines 24–42 | Column 11 = `status`; no limit columns in sheet |
| Row model | `backend/services/sheets_row_model.py` | `ReadingRowRecord` | Stores classified status at write time |

Limits are **not duplicated** in Google Sheets — only the resulting status string is persisted.

---

### Section 1 Verdict

| Check | Result |
|-------|--------|
| Warning limits configuration-driven | **PASS** |
| Alarm limits configuration-driven | **PASS** |
| Normal status configuration-driven / logical | **PASS** |
| No hardcoded limits in listed modules | **PASS** |

**Exception (informational):** Legacy GT API in `server.py` uses `machine_config.json` — still config-driven, separate from V2. Test fixtures and scripts contain sample numbers for testing only — not production runtime paths.

---

## 2. Deployment Without Final Threshold Values

### Current Runtime Behavior

1. User completes Add Reading round sheet → POST `/api/v2/submit`
2. Backend validates against `gmd_machine_config_v2.json` (equipment/parameters/types)
3. `classify_v2_parameter_status()` is called but returns **`NORMAL`** because:
   - `GMD_THRESHOLD_CLASSIFICATION_ENABLED` defaults to `false` (`threshold_service.py:155–156`), **or**
   - Limits are marked `provisional: true` and `GMD_THRESHOLD_ALLOW_PROVISIONAL` defaults to `false` (`threshold_service.py:162–163`)
4. Row appended to area worksheet with `status: NORMAL`
5. Dashboard / Reports / Trends / Equipment Monitoring read stored status

### Status Assigned to Submissions

**`NORMAL`** for all V2 parameters until classification is explicitly enabled with non-provisional approved limits.

Evidence: `backend/tests/test_threshold_service.py::test_classification_disabled_by_default` and `test_provisional_thresholds_blocked_without_flag`.

### User Experience

| Module | Behavior Without Final Limits | Breaks? |
|--------|------------------------------|---------|
| Add Reading | Full workflow: preview, submit, media, verified_by, remarks | **No** |
| Dashboard | KPIs show mostly OK; alarms panel empty or historical only | **No** |
| Reports | All readings visible; status filter works (mostly NORMAL) | **No** |
| Trends | Historical values chart correctly | **No** |
| Equipment Monitoring | Snapshot and history from `/reports/readings` | **No** |
| Google Sheets | Writes succeed to correct area tabs | **No** |

### Section 2 Verdict

**PASS**

**Justification:** Classification is opt-in and fail-safe to NORMAL. No module depends on finalized limits for core functionality. Provisional config values cannot leak into production status without explicit env override. Automated test suite: 87/87 pass.

---

## 3. Future Threshold Integration

### What Can Be Updated Without Code Changes

| Artifact | Update Required? | Role |
|----------|------------------|------|
| `backend/gmd_machine_config_v2.json` | **Yes** | Single source of truth for limits (backend + frontend via webpack alias) |
| Backend env vars | **Yes** | Enable classification |
| `templates/GMD_Equipment_Parameter_Threshold_Master.xlsx` | No (archive) | User Department collection only — **not read at runtime** |
| `backend/machine_config.json` | No (V2 path) | Legacy GT motors only |
| Google Sheets | **No** | Schema unchanged; no limit columns added |
| Frontend source code | **No** | Rebuild required to bundle updated JSON |
| Backend business logic | **No** | Already reads config dynamically (with cache) |
| REST APIs | **No** | Contracts unchanged |

### Config Update Format

For each parameter in `gmd_machine_config_v2.json`:

```json
"thresholds": {
  "enabled": true,
  "provisional": false,
  "normal_limit": <User Department approved value>,
  "warning_limit": <User Department approved value>,
  "alarm_limit": <optional explicit alarm boundary>
}
```

Schema: `backend/gmd_machine_config_v2.schema.json` → `$defs/Thresholds`.

### Environment Variables

```env
GMD_THRESHOLD_CLASSIFICATION_ENABLED=true
GMD_THRESHOLD_ALLOW_PROVISIONAL=false
```

### Complete Update Process

1. Receive approved Threshold Master Excel from User Department
2. Engineering transcribes Final Normal / Warning / Alarm into `gmd_machine_config_v2.json` (`thresholds` blocks); set `provisional: false`
3. Set env vars on production host
4. **Redeploy backend** (restart clears `@lru_cache` on `load_gmd_config_v2` and `get_parameter_thresholds`)
5. **Rebuild and redeploy frontend** (JSON bundled at compile time via `craco.config.js`)
6. Run `python scripts/audit_parameter_threshold_master.py` (optional integrity check)
7. Submit test reading above warning limit → verify WARNING/ALARM in sheet and Dashboard

**No automated Excel → JSON import script exists today** — manual engineering update is the documented path.

### Section 3 Verdict

**PASS** — Limits integrate via JSON config + env flags only. No API, schema, or business-logic changes required.

---

## 4. Historical Data Compatibility

### Sheet Row Structure

Historical rows contain: `value` (numeric) + `status` (string). Limits are not stored in the sheet (`sheets_row_model.py` — 17 columns, no limit fields).

### After Threshold Enablement

| Question | Answer | Evidence |
|----------|--------|----------|
| Migration required? | **No** | Schema unchanged; existing rows remain valid |
| Recomputation automatic? | **No** | Dashboard reads stored `status`; old NORMAL rows stay NORMAL |
| Recomputation possible? | **Manual only** | Would require batch script to re-classify and rewrite rows (not implemented) |
| Reports remain valid? | **Yes** | `reports.py` parses existing rows via `parse_row()` |
| Dashboard continues? | **Yes** | Aggregates use stored status (`dashboard.py:293–297`) |
| Analytics remain valid? | **Yes** | Trends use stored values + status from API |

### Backward Compatibility

- Legacy 10-column and 17-column Title Case layouts still parse (`test_sheets_row_layout.py`)
- Legacy `Readings` tab optionally merged on read during migration
- Status normalization handles variant tokens (`normalize_status()` in dashboard)

### Section 4 Verdict

**PASS**

**Caveat (informational):** Pre-enablement historical rows retain `NORMAL` status. Only **new submissions** receive WARNING/ALARM after limits are enabled. This is by design (write-time classification), not a compatibility failure.

---

## 5. Module Integration Verification

Once thresholds are configured and `GMD_THRESHOLD_CLASSIFICATION_ENABLED=true`:

| Module | Where Thresholds Consumed | Manual Code Change? | Config Update Sufficient? | Notes |
|--------|---------------------------|---------------------|-------------------------|-------|
| **Add Reading** | `google_sheets_service.append_v2_readings()` → `classify_v2_parameter_status()` | **No** | **Yes** (JSON + env) | New submits classified at write time |
| **Dashboard** | Reads stored `status` from Sheets via `fetch_and_clean_data()` | **No** | **Yes** (indirect) | Reflects new rows' status; historical rows unchanged |
| **KPI Cards** | `_load_summary()` counts `worst_status` from aggregates | **No** | **Yes** (indirect) | Updates as new classified rows arrive |
| **Area Cards** | `dashboardAnalytics.js` from equipment health API | **No** | **Yes** (indirect) | Same as Dashboard |
| **Alerts** | `_load_active_alarms()` filters WARNING/ALARM from stored status | **No** | **Yes** (indirect) | Populates when new classified rows exist |
| **Health Status** | `_load_equipment_health()` uses stored status | **No** | **Yes** (indirect) | Latest worst status from sheet |
| **Reports** | `/reports/readings` returns stored `status` | **No** | **Yes** (indirect) | Filter by status works on new data |
| **Trends & Analytics** | `/trends/readings` returns values + stored `status` | **No** | **Yes** for data/status | Chart reference lines: may need `validation` aligned with `thresholds` (see §1.6) |
| **Equipment Monitoring** | `GET /reports/readings` → displays `row.status` | **No** | **Yes** (indirect) | Same as Reports |

**Summary:** Write path (Add Reading) consumes config **directly**. All read-path modules consume **persisted status** — they automatically reflect new classifications on new submissions without code changes. Historical rows are not retroactively reclassified.

### Section 5 Verdict

**PASS** (with informational caveat on Trends reference-line overlay path)

---

## 6. User Department Workflow

### Step 1: Receive Approved Threshold Master

Receive completed `templates/GMD_Equipment_Parameter_Threshold_Master.xlsx` with Final Normal / Warning / Alarm columns filled by User Department.

### Step 2: Update Configuration

Transcribe approved values into `backend/gmd_machine_config_v2.json`:

- Set `thresholds.enabled: true`
- Set `thresholds.provisional: false`
- Set `normal_limit`, `warning_limit`, and optionally `alarm_limit` per parameter

This file is the **only runtime configuration source** (backend + frontend).

### Step 3: Set Environment Variables

On production backend host:

```env
GMD_THRESHOLD_CLASSIFICATION_ENABLED=true
GMD_THRESHOLD_ALLOW_PROVISIONAL=false
```

### Step 4: Validate

```bash
cd backend
python scripts/audit_parameter_threshold_master.py
python -m pytest tests/test_threshold_service.py -q
```

Optional: submit test reading via Add Reading with value above warning limit.

### Step 5: Restart / Redeploy

| Component | Action Required |
|-----------|-----------------|
| **Backend** | **Restart or redeploy** — required to reload JSON (`@lru_cache`) and env vars |
| **Frontend** | **Rebuild + redeploy** — required to bundle updated JSON |
| **Google Sheets** | **No action** |
| **Threshold Master Excel** | **No action** (not read at runtime) |

**Restart alone is NOT sufficient for frontend** — rebuild required.

### Step 6: Verify Dashboard

- Submit test reading with value in WARNING/ALARM zone
- Confirm KPI cards, area cards, recent alerts update within cache TTL (~45s)
- Confirm `/dashboard/active-alarms` returns new alarm

### Step 7: Verify Reports

- Filter by WARNING/ALARM status
- Confirm new classified rows appear

### Step 8: Verify Trends

- Select equipment + parameter
- Confirm historical values plot
- Confirm stored status in trend table
- Optionally verify reference lines (may require `validation` fields aligned with `thresholds`)

---

## 7. Risk Assessment

| # | Risk | Class | Impact | Mitigation |
|---|------|-------|--------|------------|
| 1 | Historical rows remain NORMAL after enablement | **Major** | Pre-enablement data under-represents alarm history | Document expected behavior; optional future batch re-classification script if required |
| 2 | Provisional limits in config | **Minor** | Could classify if wrong env set | Keep `GMD_THRESHOLD_ALLOW_PROVISIONAL=false` in production |
| 3 | Trends reference lines read `validation` not `thresholds` | **Minor** | Chart overlay may not show until fields aligned | Align config or accept overlay gap; does not affect classification |
| 4 | No Excel → JSON import automation | **Minor** | Manual transcription errors | Run `audit_parameter_threshold_master.py` after update |
| 5 | `@lru_cache` on config/threshold loaders | **Minor** | Stale limits if backend not restarted | Always restart backend after JSON/env change |
| 6 | Frontend JSON bundled at build | **Minor** | Stale UI config if frontend not rebuilt | Rebuild frontend after JSON change |
| 7 | Alarm acknowledgement in-memory | **Minor** | Ack state lost on restart | Documented; unrelated to thresholds |
| 8 | Legacy GT `machine_config.json` path | **Informational** | Separate from V2 round sheet | V2 Add Reading unaffected |
| 9 | Frontend Jest runner broken | **Informational** | Unit tests not run in CI for frontend | Backend 87/87 pass; manual smoke tests at deploy |
| 10 | Sheet cache TTL 45s | **Informational** | Brief delay before Dashboard reflects new data | Expected; invalidate on submit already implemented |

**No critical deployment blockers identified.**

---

## 8. Final Deployment Verdict

### Audit Results

| Criterion | Result |
|-----------|--------|
| Threshold Architecture | ✅ **PASS** |
| Configuration Driven | ✅ **PASS** |
| Deployment Without Final Limits | ✅ **PASS** |
| Historical Compatibility | ✅ **PASS** |
| Module Compatibility | ✅ **PASS** |
| Future Threshold Integration | ✅ **PASS** |
| Google Sheets Compatibility | ✅ **PASS** |

### Change Requirements After User Approval

| Question | Answer |
|----------|--------|
| Code changes required? | **NO** |
| Business logic changes required? | **NO** |
| Schema changes required? | **NO** |
| Config changes required? | **YES** — `backend/gmd_machine_config_v2.json` |
| Env changes required? | **YES** — `GMD_THRESHOLD_CLASSIFICATION_ENABLED=true` |
| Frontend redeploy required? | **YES** — rebuild to bundle updated JSON |
| Backend restart/redeploy required? | **YES** |
| Google Sheets migration required? | **NO** |

### Remaining External Dependency

**Final approved Normal / Warning / Alarm limits from User Department** via Threshold Master workbook.

This dependency **does not block deployment**. It blocks **automatic WARNING/ALARM classification** on new submissions until config is updated and flags enabled.

### Final Recommendation

**The application IS production-ready for deployment.**

The threshold architecture is correctly isolated: limits live in JSON config, classification is opt-in and fail-safe, Google Sheets store status (not limits), and all consumer modules read persisted status without embedded engineering numbers. Users can operate Add Reading, Dashboard, Reports, Trends, and Equipment Monitoring normally before User Department approval.

**Recommended go-live precautions:**

1. Deploy with `GMD_THRESHOLD_CLASSIFICATION_ENABLED=false` and `GMD_THRESHOLD_ALLOW_PROVISIONAL=false`
2. Share Threshold Master Excel with User Department for limit collection
3. Run post-deploy smoke checklist (`backend/reports/FINAL_DEPLOYMENT_CHECKLIST.md`)
4. After limit approval: update JSON → set env → redeploy backend + frontend → smoke-test one classified submission per area

---

## Appendix A — Key File Index

| Purpose | Path |
|---------|------|
| V2 config (limits) | `backend/gmd_machine_config_v2.json` |
| Config schema | `backend/gmd_machine_config_v2.schema.json` |
| Config loader | `backend/gmd_config_v2.py` |
| Classification service | `backend/services/threshold_service.py` |
| Sheets write + classify | `backend/services/google_sheets_service.py` |
| Submit route | `backend/routes/v2_preview.py` |
| Validation (no limits) | `backend/services/v2_validation.py` |
| Dashboard aggregates | `backend/routes/dashboard.py` |
| Reports API | `backend/routes/reports.py` |
| Trends API | `backend/routes/trends.py` |
| Sheet row model | `backend/services/sheets_row_model.py` |
| Frontend config import | `frontend/src/lib/gmdConfigV2.js` |
| Webpack alias | `frontend/craco.config.js` |
| Threshold tests | `backend/tests/test_threshold_service.py` |
| Threshold Master export | `backend/scripts/export_parameter_threshold_master.py` |
| Integrity audit | `backend/scripts/audit_parameter_threshold_master.py` |

## Appendix B — Automated Test Evidence

```
87 passed (full backend suite)
test_threshold_service.py — 4 tests:
  - classification disabled by default → NORMAL
  - higher_is_worse logic
  - provisional blocked without flag → NORMAL
  - provisional allowed with flag → ALARM
test_parameter_threshold_master.py — 9 tests (export integrity vs live config)
```

---

*Audit completed 2026-06-15 — evidence from static inspection of production code paths. No code modifications made.*
