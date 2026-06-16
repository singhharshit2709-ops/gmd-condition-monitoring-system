# Post-Deployment Threshold Update Audit

**GMD Condition Monitoring System — Critical Production Audit**  
**Audit Timestamp:** 2026-06-15  
**Method:** Code-level inspection only (no modifications)  
**Objective:** Confirm deployment can proceed now; User Department approved limits can be integrated later without architectural changes

---

## Executive Answer

**The system CAN be deployed now.** Approved Normal / Warning / Alarm limits CAN be integrated post-deployment by updating `backend/gmd_machine_config_v2.json`, setting environment flags, and redeploying via the existing Render pipeline — **without changing application source logic, APIs, or Google Sheets schema.**

The Threshold Master Excel is a **collection artifact only** — no runtime import path exists in the codebase.

---

## 1. Configuration Audit

### Where limits are stored

All V2 round-sheet limits live in **one file**, nested under each parameter definition:

| Limit | Storage location | JSON key |
|-------|------------------|----------|
| **Normal** | `backend/gmd_machine_config_v2.json` | `parameters[].thresholds.normal_limit` |
| **Warning** | `backend/gmd_machine_config_v2.json` | `parameters[].thresholds.warning_limit` |
| **Alarm** | `backend/gmd_machine_config_v2.json` | `parameters[].thresholds.alarm_limit` (optional; may fall back to warning) |

**Example (MCB-1 blower vertical vibration):**

```359:365:backend/gmd_machine_config_v2.json
                          "thresholds": {
                            "enabled": true,
                            "provisional": true,
                            "normal_limit": 6.0,
                            "warning_limit": 10.0,
                            "source": "PROVISIONAL — GT machine_config.json MCB1 reference only. Not approved for production classification."
                          },
```

**Schema contract:**

```1126:1155:backend/gmd_machine_config_v2.schema.json
    "Thresholds": {
      "type": "object",
      "description": "Threshold limits for automatic status classification.",
      ...
        "normal_limit": {
          "type": "number",
          "description": "Upper bound of NORMAL zone for higher_is_worse and lower_is_worse modes."
        },
        "warning_limit": {
          "type": "number",
          ...
        },
        "alarm_limit": {
```

---

### How limits are read at runtime

| Step | File | Function | Lines | Explanation |
|------|------|----------|-------|-------------|
| Load JSON from disk | `backend/gmd_config_v2.py` | `load_gmd_config_v2()` | 13–19 | Reads `gmd_machine_config_v2.json`; cached with `@lru_cache` |
| Extract parameter thresholds | `backend/services/threshold_service.py` | `_thresholds_from_param()` | 63–81 | Reads `normal_limit`, `warning_limit`, `alarm_limit` from `param["thresholds"]` |
| Lookup by equipment + key | `backend/services/threshold_service.py` | `get_parameter_thresholds()` | 85–100 | Uses `find_equipment_in_config()` + `collect_equipment_parameters()` |
| Classify value | `backend/services/threshold_service.py` | `classify_parameter_value()` | 103–139 | Compares reading to config limits (logic only — no numeric constants) |
| Gate classification | `backend/services/threshold_service.py` | `classify_v2_parameter_status()` | 142–193 | Enabled only when env flag set and limits approved |

**Limit extraction (configuration-driven, not hardcoded):**

```63:70:backend/services/threshold_service.py
def _thresholds_from_param(param: dict[str, Any]) -> ParameterThresholds | None:
    thresholds = param.get("thresholds")
    if not isinstance(thresholds, dict):
        return None

    normal_limit = _coerce_limit(thresholds.get("normal_limit"))
    warning_limit = _coerce_limit(thresholds.get("warning_limit"))
    alarm_limit = _coerce_limit(thresholds.get("alarm_limit"))
```

Module docstring explicitly states design intent:

```1:7:backend/services/threshold_service.py
"""
Config-driven threshold classification for V2 parameter readings.

Threshold values live in gmd_machine_config_v2.json — nothing is hardcoded here.
Classification is opt-in via GMD_THRESHOLD_CLASSIFICATION_ENABLED until final
engineering limits are approved.
"""
```

---

### Where limits are NOT stored

| Location | Evidence |
|----------|----------|
| Google Sheets | `GMD_SHEET_HEADERS` has `status` column only — no limit columns (`backend/services/sheets_row_model.py:24–42`) |
| V2 validation | `backend/services/v2_validation.py` — **zero** references to `threshold`, `limit`, `WARNING`, or `ALARM` (grep confirmed) |
| Dashboard routes | `backend/routes/dashboard.py` — reads stored `status`, no limit comparison |
| Reports / Trends routes | `backend/routes/reports.py`, `backend/routes/trends.py` — no threshold imports |
| Threshold Master Excel | Export-only; `export_parameter_threshold_master.py` reads config → Excel; **no import script exists** |

---

### Classification: hardcoded vs configuration-driven vs dynamic

| Aspect | Verdict | Evidence |
|--------|---------|----------|
| Normal / Warning / Alarm **numeric values** | **Configuration-driven** | Stored in JSON; loaded by `_thresholds_from_param()` |
| Comparison **rules** (e.g. higher-is-worse) | **Logic in code** (not limit values) | `classify_parameter_value()` lines 110–139 |
| Status **strings** (`NORMAL`, `WARNING`, `ALARM`) | **Constants in code** | `threshold_service.py:21–23` — labels only, not engineering limits |
| Runtime loading | **Dynamic read from file** | `load_gmd_config_v2()` + `get_parameter_thresholds()` on each classification call (cached) |

**Legacy GT path (separate, not V2 Add Reading):** `backend/server.py` loads limits from `machine_config.json` via `get_motor_thresholds_resolved()` — also configuration-driven, not relevant to V2 threshold update workflow.

---

## 2. Post-Deployment Threshold Update

**Question:** After deployment on Render, can Normal / Warning / Alarm limits be updated **without changing application code**?

| Limit | Answer | Evidence |
|-------|--------|----------|
| Normal limits | **YES** | Update `thresholds.normal_limit` in JSON; consumed by `_thresholds_from_param()` |
| Warning limits | **YES** | Update `thresholds.warning_limit` in JSON |
| Alarm limits | **YES** | Update `thresholds.alarm_limit` in JSON (optional) |

**Additional requirements (configuration/ops, not code):**

1. Set `thresholds.provisional: false` and `thresholds.enabled: true` per parameter
2. Set Render env: `GMD_THRESHOLD_CLASSIFICATION_ENABLED=true`
3. Redeploy (see Section 6) to reload JSON cache and bundled frontend config

**No Python or JavaScript source file edits are required** — only JSON content and environment variables.

---

## 3. Exact Update Procedure (Codebase-Based)

This is the **actual** process derived from repository files. There is **no** automated Excel → JSON import in the codebase (only `export_parameter_threshold_master.py` and `audit_parameter_threshold_master.py` exist).

### Step 1: Receive approved Threshold Master Excel

User Department returns `templates/GMD_Equipment_Parameter_Threshold_Master.xlsx` with **Final Normal / Warning / Alarm** columns completed.

### Step 2: Transcribe approved values into JSON

Edit `backend/gmd_machine_config_v2.json` for each applicable parameter:

```json
"thresholds": {
  "enabled": true,
  "provisional": false,
  "normal_limit": <approved>,
  "warning_limit": <approved>,
  "alarm_limit": <approved or omit>
}
```

**Source of truth:** This single file is used by both backend (`gmd_config_v2.py`) and frontend (`@gmd-config/v2` alias).

### Step 3: Validate JSON format

- Confirm valid JSON syntax (file must parse)
- Optional: validate against `backend/gmd_machine_config_v2.schema.json`
- Run integrity audit:

```bash
cd backend
python scripts/audit_parameter_threshold_master.py
```

This compares export expectations against live config (0 mismatches expected after correct update).

Optional unit tests:

```bash
cd backend
python -m pytest tests/test_threshold_service.py tests/test_parameter_threshold_master.py -q
```

### Step 4: Commit changes

Commit the updated `backend/gmd_machine_config_v2.json` to the repository branch tracked by Render (`main` per `render.yaml:5`).

### Step 5: Push to GitHub

Push commit to remote. `render.yaml` has `autoDeploy: true` — Render will trigger a new deploy automatically.

### Step 6: Set production environment flags (Render dashboard)

Before or after deploy, set in Render **Environment**:

```env
GMD_THRESHOLD_CLASSIFICATION_ENABLED=true
GMD_THRESHOLD_ALLOW_PROVISIONAL=false
```

These are **not** declared in `render.yaml` today; they must be added manually in Render. Defaults keep classification off until this step.

### Step 7: Render deployment runs automatically

Render executes (`render.yaml:8–9`):

```yaml
buildCommand: chmod +x build.sh && ./build.sh
startCommand: cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT
```

`build.sh` rebuilds frontend with updated JSON bundled in:

```11:14:build.sh
echo "==> Building React frontend (npm ci && npm run build)"
cd frontend
npm ci
REACT_APP_BACKEND_URL= npm run build
```

### Step 8: Verify health endpoint

```bash
curl https://<render-host>/health
```

Expect `"status": "ok"`, `"dashboard_ready": "True"`, `"sheets_enabled": "True"`.

### Step 9: Verify Add Reading + classification

Submit a test reading with a value in the WARNING or ALARM zone. Confirm:

- Row written to correct area worksheet
- `status` column in Google Sheets reflects classification (not `NORMAL`)

Write path evidence:

```211:229:backend/services/google_sheets_service.py
        for parameter_key, value in readings.items():
            status = classify_v2_parameter_status(
                value=float(value),
                equipment=equipment,
                category=category,
                parameter_key=parameter_key,
            )
            record = ReadingRowRecord(
                ...
                status=status,
```

### Step 10: Verify Dashboard

- KPI cards, area cards, recent alerts should reflect **new submissions** with WARNING/ALARM status
- Dashboard reads stored status from Sheets (`dashboard.py:293–297`), not live re-classification

### Step 11: Verify Reports

`GET /reports/readings` — filter by status WARNING/ALARM; confirm new classified rows appear.

### Step 12: Verify Trends & Analytics

`GET /trends/readings` — historical values and stored status returned. Chart reference lines read `parameterMeta.validation` (`trendsAnalytics.js:198–208`), not `thresholds` — overlay may require aligning `validation` fields (informational, not a blocker for classification).

---

## 4. Impact Analysis

After threshold values are updated and `GMD_THRESHOLD_CLASSIFICATION_ENABLED=true`:

| Module | Result | Explanation |
|--------|--------|-------------|
| **Dashboard** | **PASS** | `_load_summary()`, `_load_active_alarms()`, `_load_equipment_health()` aggregate stored `status` from Sheets. New submissions carry classified status automatically. |
| **Add Reading** | **PASS** | Submit calls `append_v2_readings()` → `classify_v2_parameter_status()` using updated JSON after redeploy. No route changes needed. |
| **Equipment Monitoring** | **PASS** | `ConditionMonitoring.js` fetches `GET /reports/readings`; displays `row.status` from API. |
| **Reports** | **PASS** | `reports.py:get_report_readings()` filters/parses stored status; no limit logic in route. |
| **Trends & Analytics** | **PASS** | `trends.py:get_trend_readings()` returns values + stored status. Reference-line overlay is optional UI (see caveat above). |
| **Google Sheets** | **PASS** | Schema unchanged (17 columns). Only `status` field on **new rows** reflects new limits. |
| **Area Cards** | **PASS** | Frontend `dashboardAnalytics.js` derives area status from equipment health API (stored status). |
| **KPI Cards** | **PASS** | Backend `_load_summary()` counts worst_status per equipment from Sheets. |
| **Alerts** | **PASS** | `_load_active_alarms()` surfaces rows with stored WARNING/ALARM. |
| **Health Status** | **PASS** | `_load_equipment_health()` uses stored status counts and worst_status aggregate. |

**Important behavioral note (not a FAIL):** Historical rows written before enablement retain their original `status` (typically `NORMAL`). Dashboard/alerts reflect **stored** status, not retroactive re-classification.

---

## 5. Historical Data

| Question | Answer |
|----------|--------|
| Remain accessible? | **YES** |
| Remain valid? | **YES** |
| Remain readable? | **YES** |
| Remain compatible? | **YES** |
| Migration required? | **NO** |

**Evidence:**

1. **Schema unchanged** — limits are not stored in Sheets; only `value` and `status` columns exist (`sheets_row_model.py:24–42`).
2. **Read path unchanged** — `parse_row()` / `fetch_and_clean_data()` parse existing rows regardless of when limits were configured.
3. **No rewrite on config change** — `classify_v2_parameter_status()` runs only at **write time** in `append_v2_readings()`; no batch re-classification job exists in the codebase.
4. **Legacy layout support** — `test_sheets_row_layout.py` confirms legacy 10/17-column rows still parse.

**Section 5 verdict: PASS — migration NO.**

---

## 6. Frontend Build Dependency

| Action | Required? | Why (code evidence) |
|--------|-----------|---------------------|
| **Frontend rebuild** | **YES** | Webpack alias imports JSON at **compile time**: `'@gmd-config/v2': '../backend/gmd_machine_config_v2.json'` (`frontend/craco.config.js:38`). Frontend imports it statically: `import gmdMachineConfigV2 from "@gmd-config/v2"` (`frontend/src/lib/gmdConfigV2.js:1`). `build.sh` runs `npm run build` and copies output to `backend/static`. |
| **Backend restart** | **YES** | `load_gmd_config_v2()` uses `@lru_cache(maxsize=1)` (`gmd_config_v2.py:13–14`). `get_parameter_thresholds()` uses `@lru_cache(maxsize=256)` (`threshold_service.py:84–85`). Process must restart to reload JSON and env vars. |
| **Render redeploy** | **YES** | Render `buildCommand` runs full `build.sh` (Python + npm + static copy). Env var changes (`GMD_THRESHOLD_CLASSIFICATION_ENABLED`) require service restart. `autoDeploy: true` on git push satisfies this. |

**Consequence of bundled JSON:** If only backend is restarted without frontend rebuild, Add Reading UI (equipment/parameters from config) may show **stale** hierarchy/labels until frontend is rebuilt. Classification on submit uses **backend** JSON (after restart), but frontend config-driven UI will not match until rebuild.

**Restart alone is NOT sufficient** — full Render deploy (build + start) is required.

---

## 7. Future Maintenance

**Scenario:** After deployment, Warning changes `60 → 65`, Alarm changes `75 → 80`.

| Question | Answer |
|----------|--------|
| Only configuration updates required? | **YES** |
| Source code modifications required? | **NO** |

**Evidence:**

1. Limits are read from `thresholds.warning_limit` / `thresholds.alarm_limit` in JSON (`threshold_service.py:68–70`).
2. No numeric `60`, `65`, `75`, or `80` literals exist in classification logic — only comparison operators in `classify_parameter_value()`.
3. Changing JSON + redeploying applies new limits to **future submissions** automatically via existing `classify_v2_parameter_status()` path.

**Operational steps for limit change:** Edit JSON → commit → push → Render redeploy → (optional) verify with test submit.

**No Python/JS source edits** for limit value changes.

---

## 8. Remaining Risks

| # | Risk | Category | Impact | Mitigation |
|---|------|----------|--------|------------|
| 1 | No Excel → JSON import automation | **Major** | Manual transcription errors when User Department returns workbook | Use `audit_parameter_threshold_master.py`; peer-review JSON edits |
| 2 | Historical rows not retroactively reclassified | **Major** | Pre-enablement data stays NORMAL; alarm history incomplete until new rounds | Document expected behavior; optional future batch script if required |
| 3 | Frontend JSON bundled at build | **Minor** | UI config stale if backend-only restart | Always run full `build.sh` deploy path |
| 4 | `@lru_cache` on config loaders | **Minor** | Stale limits if process not restarted | Redeploy/restart after JSON change |
| 5 | `GMD_THRESHOLD_*` not in `render.yaml` | **Minor** | Classification could be enabled accidentally via Render UI if mis-set | Explicitly set `GMD_THRESHOLD_CLASSIFICATION_ENABLED=false` until approval |
| 6 | Provisional limits in JSON | **Minor** | Blocked unless `GMD_THRESHOLD_ALLOW_PROVISIONAL=true` | Keep provisional flag false after approval |
| 7 | Trends reference lines read `validation.*` not `thresholds.*` | **Minor** | Chart overlay may not update with limit changes | Align fields in JSON or accept overlay gap; does not affect classification |
| 8 | Threshold Master Excel not read at runtime | **Informational** | Excel is collection only | Transcribe to JSON manually |
| 9 | Legacy GT `machine_config.json` separate path | **Informational** | Unrelated to V2 round sheet limits | V2 workflow unaffected |

**No critical deployment blockers identified.**

---

## 9. Final Management Conclusion

### Deployment and integration verdict

| Statement | Verdict |
|-----------|---------|
| ✓ Safe to Deploy Now | **YES** — classification disabled by default; all modules functional with `NORMAL` status |
| ✓ User Department Threshold Values Can Be Added Later | **YES** — via JSON update + env flags + redeploy |
| ✓ No Backend Logic Changes Required | **YES** — `threshold_service.py` already reads config dynamically |
| ✓ No Frontend Logic Changes Required | **YES** — no code edits; rebuild required to bundle updated JSON |
| ✓ No Google Sheets Schema Changes Required | **YES** — 17-column schema unchanged; limits not stored in sheet |
| ✓ No Database Migration Required | **YES** — persistence is Google Sheets; no SQL/NoSQL migration path |
| ✓ Existing Data Remains Compatible | **YES** — historical rows valid; stored status preserved |
| ✓ Only Configuration Update + Required Restart/Redeploy | **YES** — see Section 6 |

### Exceptions (operational, not architectural)

1. **Manual step:** Approved Excel values must be transcribed into `backend/gmd_machine_config_v2.json` (no import script in repo).
2. **Redeploy required:** Full Render build (`build.sh`) — not backend restart alone.
3. **Env flags required:** Set `GMD_THRESHOLD_CLASSIFICATION_ENABLED=true` in Render when limits are approved.
4. **Historical status:** Old rows are **not** automatically reclassified; only new submissions use new limits.

### Recommended management decision

**Approve production deployment now.** Final limiting values from the User Department can be integrated as a **configuration-only change** after go-live, without architectural rework, API changes, or Google Sheets migration.

---

## Appendix — Key Evidence Index

| Topic | File | Symbol / Lines |
|-------|------|----------------|
| Limit storage | `backend/gmd_machine_config_v2.json` | `thresholds.normal_limit`, `.warning_limit`, `.alarm_limit` |
| Limit loader | `backend/services/threshold_service.py` | `_thresholds_from_param` (63–81), `get_parameter_thresholds` (85–100) |
| Write-time classify | `backend/services/google_sheets_service.py` | `append_v2_readings` (211–229) |
| Config file loader | `backend/gmd_config_v2.py` | `load_gmd_config_v2` (13–19) |
| Frontend config import | `frontend/src/lib/gmdConfigV2.js` | line 1 |
| Webpack JSON bundle | `frontend/craco.config.js` | line 38 |
| Production build | `build.sh` | lines 11–21 |
| Render deploy | `render.yaml` | lines 5–9 |
| Sheet schema (no limits) | `backend/services/sheets_row_model.py` | `GMD_SHEET_HEADERS` (24–42) |
| Dashboard reads status | `backend/routes/dashboard.py` | `get_equipment_status_aggregates` (293–297) |
| Export-only script | `backend/scripts/export_parameter_threshold_master.py` | reads config → Excel |
| Audit script | `backend/scripts/audit_parameter_threshold_master.py` | validates config ↔ export |
| Automated tests | `backend/tests/test_threshold_service.py` | classification behavior |

---

*Report generated from code inspection — no assumptions beyond repository evidence.*
