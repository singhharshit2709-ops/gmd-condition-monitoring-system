# Timestamp / Timezone Audit

**GMD Condition Monitoring System**  
**Audit Date:** 2026-06-16  
**Issue:** New reading timestamps incorrect in Google Sheets and Dashboard / Recent Readings  
**Resolution:** Centralized plant-local timestamps (Asia/Kolkata / IST)

---

## Executive Summary

**Root cause:** V2 Add Reading timestamps were generated on the backend using `datetime.now()` **without a timezone**. On Render (UTC host), this stored **UTC wall-clock time** in Google Sheets as a naive `YYYY-MM-DD HH:MM:SS` string. Plant operators in India expect **IST (UTC+5:30)**, so timestamps appeared ~5.5 hours behind local plant time in both Sheets and Dashboard.

**Fix:** Introduced `backend/services/gmd_datetime.py` — all submission timestamps now use **`Asia/Kolkata`** (configurable via `GMD_PLANT_TIMEZONE`). Read paths parse stored strings as plant-local time consistently.

---

## 1. Add Reading Submit Flow — Where Timestamp Is Generated

| Step | Component | Timestamp source |
|------|-----------|------------------|
| Frontend submit | `frontend/src/lib/v2SubmitApi.js` | **Does not send** a reading timestamp in POST body |
| Frontend console logs | `v2SubmitApi.js` | `new Date().toISOString()` — **logging only**, not persisted |
| Backend validation | `routes/v2_preview.py` → `validate_v2_submission()` | No timestamp generation |
| Backend persistence | `services/google_sheets_service.py` → `append_v2_readings()` | **`log_submission_timestamp("V2 sheet append")`** — **authoritative** |
| Google Sheets row | `ReadingRowRecord.timestamp` | Same string written to column `timestamp` |
| API response | `result["timestamp"]` → `submitted_at` | Same backend-generated string |

**Conclusion:** Timestamp is generated **100% on the backend** at Google Sheets write time. Frontend display issues were a consequence of wrong stored values, not a separate frontend clock.

---

## 2. Backend Search Results (Before Fix)

| Pattern | Location | Usage |
|---------|----------|-------|
| `datetime.now().strftime(...)` | `google_sheets_service.py:144, 205` | **V1/V2 sheet writes — BUG** |
| `datetime.now()` | `dashboard.py` cache TTL, `format_last_updated` | Relative labels used server local time |
| `datetime.now()` | `trends.py` window filter | Server local "now" |
| `datetime.now().strftime(...)` | `gmd_monitoring.py`, `gmd_models.py` | Bulk response defaults |
| `datetime.now(timezone.utc)` | `server.py` legacy GT paths | Legacy motor API only |
| `zoneinfo` / `Asia/Kolkata` | **Not used** before fix | — |
| `pytz` | **Not present** | — |
| Frontend `toISOString` | `v2SubmitApi.js`, `RoundSheetForm.jsx` | Console / non-persisted only |

---

## 3. Google Sheets Write Path

### Before

```python
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

On Render: `2026-06-16 09:30:00` when local IST plant time was `2026-06-16 15:00:00`.

### After

```python
timestamp = log_submission_timestamp("V2 sheet append")
```

Logs on every submission:

```
V2 sheet append timestamp: raw='2026-06-16T15:00:00+05:30' timezone=Asia/Kolkata formatted='2026-06-16 15:00:00'
```

Written to Google Sheets column `timestamp` exactly as `formatted`.

---

## 4. Dashboard Read Path

| Function | Behavior before | Behavior after |
|----------|-----------------|----------------|
| `parse_timestamp()` | Naive `strptime` — interpreted as server local | Delegates to `parse_plant_timestamp()` — **IST-aware** |
| `format_last_updated()` | `datetime.now() - naive timestamp` | `plant_now() - aware IST timestamp` |
| `get_recent_readings()` | Returns raw sheet string unchanged | **No conversion** — passes through stored IST string |
| Sort keys | `datetime.min` naive | `plant_datetime_min()` IST-aware |

**Conclusion:** Dashboard does **not** apply a second timezone conversion on display. It returns the stored string; frontend `parseTimestamp()` in `dashboardAnalytics.js` parses `YYYY-MM-DD HH:MM:SS` as **browser local time**, which matches plant IST when operators use IST devices.

---

## 5. Root Cause

| Factor | Detail |
|--------|--------|
| **Primary** | `datetime.now()` on UTC Render host writes UTC wall time into Sheets |
| **Format** | Naive string with no timezone suffix — ambiguous but treated as plant local by operators |
| **Scope** | Affects V2 Add Reading, V1 append, bulk GMD routes, Trends date windows, relative "Updated Today" labels |
| **Not the cause** | Frontend submit payload (does not include timestamp); Dashboard re-formatting |

---

## 6. Fix Implemented

### New module: `backend/services/gmd_datetime.py`

| Function | Purpose |
|----------|---------|
| `get_plant_timezone()` | Returns `ZoneInfo` (default `Asia/Kolkata`, env `GMD_PLANT_TIMEZONE`) |
| `plant_now()` | Current time in plant TZ (aware) |
| `format_plant_timestamp()` | Format as `YYYY-MM-DD HH:MM:SS` |
| `log_submission_timestamp()` | Generate + log raw ISO, timezone, formatted string |
| `parse_plant_timestamp()` | Parse stored strings as plant-local aware datetimes |
| `parse_plant_date()` | Parse `YYYY-MM-DD` filters in plant TZ |
| `plant_datetime_min()` | Aware sort sentinel |

### Dependency

Added `tzdata>=2024.1` to `backend/requirements.txt` (required for `zoneinfo` on Windows; included on Linux Render images).

### Files changed

| File | Change |
|------|--------|
| `backend/services/gmd_datetime.py` | **New** — plant timezone helpers |
| `backend/services/google_sheets_service.py` | V1/V2 writes use `log_submission_timestamp()` |
| `backend/routes/dashboard.py` | Parse/compare in plant TZ |
| `backend/routes/reports.py` | Date filters in plant TZ |
| `backend/routes/trends.py` | Window filters use `plant_now()` |
| `backend/routes/gmd_monitoring.py` | Bulk response timestamp |
| `backend/models/gmd_models.py` | Default timestamp factory |
| `backend/requirements.txt` | Added `tzdata` |
| `backend/tests/test_gmd_datetime.py` | **New** — unit tests |

### Environment variable (optional)

```env
GMD_PLANT_TIMEZONE=Asia/Kolkata
```

Default is `Asia/Kolkata` if unset.

---

## 7. Before / After Behavior

| Scenario | Before | After |
|----------|--------|-------|
| Submit at 3:00 PM IST on Render | Sheet shows ~9:30 AM | Sheet shows **3:00 PM** |
| Dashboard Recent Readings | Same incorrect UTC wall time | **Matches sheet (IST)** |
| Relative time ("5 minutes ago") | Wrong delta vs UTC-stored time | Correct vs IST `plant_now()` |
| Trends 7-day window | Anchored to UTC server now | Anchored to **IST plant now** |
| Reports date filter | Server-local midnight | **IST midnight** |
| Legacy GT `server.py` motor API | Unchanged (separate path) | Unchanged |

---

## 8. Verification Results

### Automated tests

```
tests/test_gmd_datetime.py ....           4/4 PASS
tests/test_v2_submit.py ......            6/6 PASS
tests/test_tc_agg.py ................    16/16 PASS
tests/test_trends.py ...                  3/3 PASS
```

### Local verification script

```
UTC server time:     2026-06-16T09:xx:xx+00:00
Plant now (IST):     2026-06-16T15:xx:xx+05:30
Formatted for sheet: 2026-06-16 15:xx:xx
Offset hours vs UTC: 5.5
```

### Post-deploy manual checklist

After redeploy to Render:

1. Submit one test reading via Add Reading
2. Confirm Google Sheets `timestamp` column shows **current IST** (not UTC)
3. Confirm Dashboard Recent Readings shows **same timestamp**
4. Confirm Relative Time shows "Just now" / "X minutes ago" correctly
5. Confirm Reports list shows matching timestamp
6. Confirm Render logs contain `V2 sheet append timestamp: raw=... timezone=Asia/Kolkata formatted=...`

### Historical rows

Existing rows written before this fix retain their stored UTC wall-clock values. They are **not migrated**. Only **new submissions** after deploy use IST.

---

## 9. Consistency Across Modules

| Module | Timestamp handling |
|--------|-------------------|
| Add Reading submit | IST via `log_submission_timestamp()` |
| Google Sheets | IST naive string in `timestamp` column |
| Dashboard / Recent Readings | Read-through + IST-aware sort/relative labels |
| Reports | IST date filters + raw timestamp display |
| Trends & Analytics | IST window anchoring + raw timestamp in API |
| Equipment Monitoring | Uses `/reports/readings` — same stored values |

---

## 10. Deployment Notes

1. Redeploy backend (Render runs `pip install -r requirements.txt` — picks up `tzdata`)
2. No frontend rebuild required for this fix
3. No Google Sheets schema migration
4. Optional: set `GMD_PLANT_TIMEZONE=Asia/Kolkata` explicitly in Render env

---

*Audit completed 2026-06-16 — root cause confirmed as UTC `datetime.now()` on Render; fixed with centralized IST plant timestamps.*
