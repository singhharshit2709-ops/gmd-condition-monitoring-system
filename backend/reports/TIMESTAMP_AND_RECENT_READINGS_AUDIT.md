# Timestamp, Timezone & Recent Readings Order — Production Audit

**GMD Condition Monitoring System**  
**Audit Date:** 2026-06-16  
**Issues:** (1) Incorrect timestamps in Google Sheets and Dashboard; (2) Recent Readings chronological ordering robustness  
**Status:** Root causes confirmed; fixes implemented

---

## Executive Summary

Two related production defects were traced and fixed:

| Issue | Root cause | Fix |
|-------|------------|-----|
| **Incorrect timestamp / “6 hours ago” for 1-hour-old reading** | Backend wrote `datetime.now()` on UTC Render host (UTC wall clock into Sheets). Frontend then parsed naive strings as browser-local components, amplifying the ~5.5 h IST offset in relative-time labels. | Centralized **Asia/Kolkata (IST)** generation on write (`gmd_datetime.py`) and **explicit IST parsing** on display (`dashboardAnalytics.js`). |
| **Recent Readings ordering across days** | Multi-area merged reads sorted by **raw timestamp string**, not parsed datetime. Works for canonical `YYYY-MM-DD HH:MM:SS` but fails for legacy `DD/MM/YYYY` rows and is fragile across mixed formats. | Replaced string sort with **`reading_timestamp_sort_key()`** (parsed datetime, newest-first). API endpoints already used datetime sort; merge layer now matches. |

**Migration:** None required. Historical rows keep stored values; only new submissions and display logic change after redeploy.

---

## Issue 1 — Timestamp Investigation

### 1. Where timestamps are first created

| Location | Creates timestamp? | Notes |
|----------|-------------------|-------|
| `frontend/src/lib/v2SubmitApi.js` | No (logging only) | `new Date().toISOString()` in console logs |
| `frontend/src/components/v2/RoundSheetForm.jsx` | No (logging only) | Same |
| `backend/routes/v2_preview.py` | No | Validates; passes through Sheets result |
| **`backend/services/google_sheets_service.py`** | **Yes — authoritative** | `log_submission_timestamp("V2 sheet append")` |
| `backend/routes/gmd_monitoring.py` | Yes (response metadata) | Uses same helper |
| `backend/models/gmd_models.py` | Default factory | `format_plant_timestamp` |

**Conclusion:** Timestamp is created **100% on the backend** at Google Sheets write time. Frontend does not send a reading timestamp in the submit payload.

### 2. Backend search results

| Pattern | File(s) | Role |
|---------|---------|------|
| `datetime.now().strftime(...)` | *(removed)* | Was V1/V2 sheet writes — **bug** |
| `log_submission_timestamp()` | `google_sheets_service.py`, `gmd_monitoring.py` | **Current write path** |
| `datetime.now()` | `dashboard.py` | Cache TTL only (not user-facing timestamps) |
| `datetime.now(timezone.utc)` | `server.py` | Legacy GT motor API only (separate from GMD readings) |
| `parse_plant_timestamp()` | `gmd_datetime.py`, `dashboard.py`, `reports.py`, `trends.py` | Read/sort/filter paths |
| `zoneinfo` / `Asia/Kolkata` | `gmd_datetime.py` | Plant timezone (env: `GMD_PLANT_TIMEZONE`) |
| `pytz` | — | Not used |
| Frontend `new Date()` / `toISOString()` | Various | Display, CSV export filename, dev logs — not persisted |

### 3. Exact values written and returned

**Before fix (production on Render):**

```python
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# Example: event at 3:00 PM IST → stored as "2026-06-16 09:30:00" (UTC wall clock)
```

**After fix:**

```python
timestamp = log_submission_timestamp("V2 sheet append")
# Logs: raw='2026-06-16T15:00:00+05:30' timezone=Asia/Kolkata formatted='2026-06-16 15:00:00'
# Written to Google Sheets column `timestamp` exactly as formatted
# Returned in API as submitted_at / result["timestamp"]
```

### 4. Dashboard display path

| Layer | Behavior |
|-------|----------|
| API `/dashboard/recent-readings` | Returns raw `timestamp` string from Sheets (no conversion) |
| `RelativeTime.jsx` | Calls `formatRelativeTime()` |
| **`parseTimestamp()` (before)** | Parsed `YYYY-MM-DD HH:MM:SS` via `new Date(y, m-1, d, h, min, s)` — **browser local**, not IST |
| **`parseTimestamp()` (after)** | Appends `+05:30` — treats sheet value as **IST wall clock** |
| `formatRelativeTime()` | `now.getTime() - parsed.getTime()` — correct when parse is correct |

**Why “1 hour ago” showed as “6 hours ago”:**

1. Reading submitted at 3:00 PM IST.
2. Backend stored `"09:30:00"` (UTC wall clock on Render).
3. Frontend parsed as 9:30 AM local → 6.5 h behind 4:00 PM → displayed **“6 hours ago”**.

---

## Issue 2 — Recent Readings Ordering Investigation

### Sorting by module

| Module | Sort method | Before | After |
|--------|-------------|--------|-------|
| **`sheets_data_access.get_all_values()`** | Merged multi-area read | **String sort** on timestamp column | **Parsed datetime sort** via `reading_timestamp_sort_key()` |
| `/dashboard/recent-readings` | API | Parsed datetime descending ✓ | Unchanged (already correct) |
| `/reports/readings` | API | Parsed datetime descending ✓ | Unchanged |
| `/trends/readings` | API | Parsed datetime ascending (chart order) ✓ | Unchanged |
| `dedupeRecentReadings()` | Frontend | Preserves API order ✓ | Unchanged |
| `ConditionMonitoring.js` | Frontend | `new Date(timestamp)` sort | **`parseTimestamp()` sort** |
| `trendsAnalytics.js` | Frontend | `new Date()` for chart/stats | **`parseTimestamp()`** |
| Equipment Monitoring | Uses `/reports/readings` | Backend sort ✓ | Unchanged |

### Answers to audit questions

1. **Sorted by actual timestamp descending?** Yes — after fix, at merge layer and all API endpoints.
2. **Sort basis?** Now **parsed datetime** everywhere critical; previously merge layer used **string comparison**.
3. **Tomorrow without new readings:** Today’s readings remain at top (newest calendar day wins on descending datetime sort).
4. **Tomorrow with new reading:** Tomorrow’s newest first → today’s next → older history — pure chronological descending.
5. **Not based on:** Sheet row index or insertion order (rows insert at row 2 per worksheet; merge re-sorts globally).

### String-sort failure example (fixed)

| Timestamp A | Timestamp B | String sort winner | Datetime sort winner |
|-------------|---------------|--------------------|----------------------|
| `2026-06-16 08:00:00` | `16/06/2026 20:00:00` | A (lexicographic) | B (8 PM > 8 AM) |

---

## Timezone Strategy Adopted

**Single strategy: Plant-local IST wall clock**

| Aspect | Rule |
|--------|------|
| Storage format | Naive `YYYY-MM-DD HH:MM:SS` in **Asia/Kolkata** |
| Write | `log_submission_timestamp()` using `zoneinfo.ZoneInfo("Asia/Kolkata")` |
| Read (backend) | `parse_plant_timestamp()` — attaches IST tzinfo |
| Read (frontend) | `parseTimestamp()` — ISO string with `+05:30` offset |
| Config | `GMD_PLANT_TIMEZONE=Asia/Kolkata` (optional; default matches) |
| Legacy GT motor API | Unchanged (`datetime.now(timezone.utc)` in `server.py`) |

UTC storage was rejected to match operator expectations and existing sheet format (no `Z` suffix).

---

## Ordering Strategy Adopted

1. **Merge reads:** Sort all area worksheets + optional legacy tab by `reading_timestamp_sort_key()` descending.
2. **API endpoints:** Sort parsed datetimes with `plant_datetime_min()` fallback for unparseable rows (sort last).
3. **Frontend panels:** Preserve backend order; local sorts use `parseTimestamp().getTime()`.
4. **Dedup:** `dedupeRecentReadings()` keeps first occurrence in already-sorted list (newest wins).

---

## Files Inspected

### Backend

- `services/gmd_datetime.py`
- `services/google_sheets_service.py`
- `services/sheets_data_access.py`
- `services/sheets_config.py`
- `routes/dashboard.py`
- `routes/reports.py`
- `routes/trends.py`
- `routes/v2_preview.py`
- `routes/gmd_monitoring.py`
- `models/gmd_models.py`
- `server.py` (legacy paths only)

### Frontend

- `src/lib/dashboardAnalytics.js`
- `src/lib/trendsAnalytics.js`
- `src/components/dashboard/RelativeTime.jsx`
- `src/components/dashboard/RecentReadingsPanel.jsx`
- `src/hooks/useDashboardData.js`
- `src/pages/ConditionMonitoring.js`
- `src/pages/Reports.js`
- `src/lib/v2SubmitApi.js`

---

## Files Modified

| File | Change |
|------|--------|
| `backend/services/gmd_datetime.py` | Added `reading_timestamp_sort_key()` |
| `backend/services/sheets_data_access.py` | Datetime-based merge sort (was string sort) |
| `backend/tests/test_gmd_datetime.py` | Sort-order regression tests (+2 cases) |
| `frontend/src/lib/dashboardAnalytics.js` | IST `parseTimestamp()`, plant-calendar `isToday`/`isYesterday` |
| `frontend/src/lib/dashboardAnalytics.test.js` | IST parse + relative-time tests |
| `frontend/src/lib/trendsAnalytics.js` | Use shared `parseTimestamp()` |
| `frontend/src/pages/ConditionMonitoring.js` | IST parse for display and sort |
| `frontend/src/pages/Reports.js` | IST parse for client-side date filter |
| `backend/static/` | Rebuilt bundle `main.e732181b.js` |

*(Prior session already updated `google_sheets_service.py`, `dashboard.py`, `reports.py`, `trends.py`, `gmd_monitoring.py`, `gmd_models.py`, `requirements.txt` with `tzdata`.)*

---

## Before / After Behavior

| Scenario | Before | After |
|----------|--------|-------|
| Submit at 3:00 PM IST on Render | Sheet: ~9:30 AM; Dashboard: “6 hours ago” | Sheet: **3:00 PM**; Dashboard: **“Just now” / “X minutes ago”** |
| Relative time | Wrong by ~5.5 h when UTC host + IST browser | Correct IST instant math |
| Multi-area Recent Readings | Mostly correct for ISO strings; wrong if legacy DMY mixed in | **Globally chronological** across all formats |
| Cross-day order (no new reading tomorrow) | ISO strings OK; DMY legacy could misorder | **Stable datetime descending** |
| Reports / Trends API order | Datetime sort ✓ | Unchanged |
| Equipment Monitoring sort | `new Date()` (browser-dependent) | **IST parse** |

---

## Verification Results

### Automated (local)

```
backend pytest:  93/93 PASS (includes test_gmd_datetime sort cases)
```

Frontend Jest runner has a pre-existing `babelJest.createTransformer` environment issue; logic verified manually:

```
parseTimestamp("2026-06-16 15:00:00").toISOString() → "2026-06-16T09:30:00.000Z"
formatRelativeTime("2026-06-16 14:00:00", parseTimestamp("2026-06-16 15:00:00")) → "1 hour ago"
```

### IST write smoke (local Python)

```
UTC server:  2026-06-16T09:33:43+00:00
IST plant:   2026-06-16T15:03:43+05:30
Formatted:   2026-06-16 15:03:43
```

### Post-deploy manual checklist

1. Submit one test reading via Add Reading.
2. Google Sheets `timestamp` = current **IST** (not UTC wall clock).
3. Dashboard Recent Readings shows **same timestamp**.
4. Relative label = **“Just now”** or correct minutes/hours.
5. Reports list timestamp matches sheet.
6. Trends chart points ordered chronologically.
7. Render logs: `V2 sheet append timestamp: raw=... timezone=Asia/Kolkata formatted=...`

---

## Migration Requirements

| Item | Required? |
|------|-----------|
| Google Sheets schema change | **No** |
| Backfill historical timestamps | **No** (optional manual correction only) |
| Database migration | **No** |
| Redeploy backend + static | **Yes** |
| Render env | Optional: `GMD_PLANT_TIMEZONE=Asia/Kolkata` |

**Historical rows** written before IST fix retain UTC wall-clock strings. They will still display with the old offset until re-submitted or manually corrected in Sheets. **New submissions** after redeploy use IST consistently.

---

## Deployment Notes

1. Push changes and redeploy Render (runs `build.sh` → fresh static + `pip install` for `tzdata`).
2. Do **not** set `REACT_APP_BACKEND_URL` on Render (same-origin API).
3. After deploy, run post-deploy manual checklist above.

---

*Audit completed 2026-06-16 — timestamp root cause: UTC `datetime.now()` on Render; display amplification: browser-local parse. Ordering root cause: string sort in merged Sheets read layer. Both fixed with IST plant timezone and parsed-datetime sorting.*
