# DM Water Electrode Cooling — Shared Equipment Mapping Audit

**Date:** 2026-06-17  
**Issue:** DM Water readings visible under virtual **DM Water Electrode Cooling** area but not under physical tank areas (A/E/G/K Tank)  
**Resolution:** Canonical dual-area mapping in frontend analytics layer  
**Google Sheets schema change:** None

---

## Root Cause

DM Water equipment exists in **two logical places**:

| View | Config source | Example |
|------|---------------|---------|
| Physical tank round | `equipment.area = "A Tank"` | A Tank Electrode Cooling |
| Virtual aggregation bucket | `resolveDashboardArea()` → DM Water Electrode Cooling | Same equipment |

**Before fix:**

1. `buildConfigLookups()` registered DM Water equipment **only** in `areaEquipment["DM Water Electrode Cooling"]`.
2. `resolveReadingArea()` routed DM category readings **only** to the virtual bucket.
3. Area-scoped logic (`getTodayTouchedByArea`, `computeRoundCompletion`, filters, Equipment Monitoring) used **single-area equality** → physical tanks never saw DM Water readings.

**Not duplicate IDs:** Equipment names are unique (`A Tank Electrode Cooling`, `E Tank Electrode Cooling`, etc.). The bug was **visibility fragmentation**, not conflicting sheet rows.

**Sheets write path (unchanged):** DM categories route to worksheet `DM Water Electrode Cooling` via `sheets_area_registry.resolve_area_worksheet()` while preserving `area_tank` column (e.g. `A Tank`).

---

## Fix — Canonical Mapping Layer

New exports in `frontend/src/lib/dashboardAnalytics.js`:

| Function | Purpose |
|----------|---------|
| `getPhysicalTankAreaForReading(row, lookups)` | Physical tank from `area_tank` for DM Water rows |
| `getDashboardAreasForReading(row, lookups)` | **Both** virtual DM bucket + physical tank |
| `readingVisibleInDashboardArea(row, area, lookups)` | Shared visibility check |
| `appendUniqueEquipmentMeta()` | Dual-register equipment in lookup maps |

**Dual registration in `buildConfigLookups()`:**  
Each DM Water meta is indexed under:

- Virtual bucket: `DM Water Electrode Cooling`
- Physical tank: `A Tank` / `E Tank` / `G Tank` / `K Tank` (from `meta.area`)

**Updated consumers:**

- `getTodayTouchedByArea`
- `computeAreaSummaries`
- `computeRoundCompletion`
- `computeTodayMetrics` (counts once per physical equipment)
- `filterDashboardData` / `rowMatchesFilters`
- `EquipmentSummaryDrawer`
- `ConditionMonitoring.js` (`readingMatchesEquipment`)

**Unchanged (already correct):**

- `resolveReadingArea()` — primary display area remains virtual bucket for Recent Readings cards
- Google Sheets write/read — `area_tank` + category preserved in row
- Backend `/reports/readings`, `/trends/readings` — filter by `area_tank` when provided
- Equipment health / active alarms — keyed by unique `equipment` name
- Add Reading — `collectEquipmentByArea()` already includes DM Water under each tank

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/lib/dashboardAnalytics.js` | Canonical mapping + dual registration + area attribution |
| `frontend/src/lib/dashboardAnalytics.test.js` | A/E/G/K tank visibility tests |
| `frontend/src/pages/ConditionMonitoring.js` | Use `readingVisibleInDashboardArea` |
| `frontend/src/components/dashboard/EquipmentSummaryDrawer.jsx` | Area drill-down filter fix |

---

## API Impact

**None.** No backend route, schema, or response shape changes.

Backend equipment health aggregates by **equipment name** (unique per tank instance). DM Water rows already stored with correct `area_tank`, `category`, `equipment` columns.

---

## Frontend Impact

| Module | Before | After |
|--------|--------|-------|
| Dashboard area cards (A Tank) | Pending / no reading | Shows today's DM Water electrode reading |
| Round completion (A Tank) | DM equipment excluded from total/completed | Included in configured count + completion |
| Recent Readings filter (Area = A Tank) | DM rows hidden | DM rows visible |
| Equipment drill-down drawer | Empty for DM equipment under tank | Shows latest reading |
| Equipment Monitoring (Area = A Tank) | No historical rows | Same rows as DM virtual view |
| Recent Readings card label | Still shows **DM Water Electrode Cooling** as area | Unchanged (primary resolve path) |

---

## Backend Impact

**None required.** Reference modules (unchanged):

- `services/sheets_area_registry.py` — DM write routing
- `routes/dashboard.py` — health/alarms by equipment name
- `routes/reports.py`, `routes/trends.py` — `area_tank` query filters

---

## Test Evidence

### Automated (`frontend/src/lib/dashboardAnalytics.test.js`)

- `DM water readings are visible in physical tank and virtual DM area` — **A, E, G, K tanks**
- `DM water round completion counts toward physical tank and DM virtual area`
- `matchConfiguredEquipmentInArea` succeeds for both `"A Tank"` and `"DM Water Electrode Cooling"`
- Updated E Tank blower test uses dynamic configured equipment count (includes dual-registered DM assets)

Run:

```bash
cd frontend
npm test -- --watchAll=false dashboardAnalytics.test.js
```

### Manual validation checklist

| Action | Expected |
|--------|----------|
| Submit A Tank Electrode Cooling via Add Reading | Row in Sheets worksheet `DM Water Electrode Cooling`, `area_tank=A Tank` |
| Dashboard → A Tank area card | Has today readings; electrode cooling counted |
| Dashboard → DM Water area card | Same reading visible |
| Filter Recent Readings → A Tank | Reading appears |
| Equipment Monitoring → A Tank → A Tank Electrode Cooling | Historical + latest snapshot populated |
| Reports / Trends with `area_tank=A Tank` | Rows returned (backend unchanged) |

Repeat for E, G, K Tank electrode cooling equipment.

---

## Historical Data Compatibility

- Existing Google Sheets rows retain `area_tank`, `category`, `equipment` values.
- No migration script required.
- Rows missing `area_tank` still resolve to virtual DM bucket only (legacy edge case).

---

## Final Confirmation

Shared DM Water Electrode Cooling equipment readings are now attributed to **both** the virtual **DM Water Electrode Cooling** dashboard area and the corresponding **physical tank area**, using the same underlying sheet rows and unique equipment names across:

- Dashboard (summaries, round completion, filters, drill-down)
- Equipment Monitoring
- Recent Readings (when filtered by tank)
- Reports & Trends (via existing `area_tank` column — no change)

*Audit completed 2026-06-17.*
