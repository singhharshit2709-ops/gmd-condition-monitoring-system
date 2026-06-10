# GMD Condition Monitoring Dashboard — Manual QA Execution Plan

**Document version:** 1.0  
**Role:** QA Lead — Phase 2 manual validation  
**Scope:** 7 remaining UI / integration test cases (Phase 1 automates the other 17)  
**Prerequisite:** Phase 1 pytest suite passing (`python -m pytest` → 35 passed)

---

## Table of Contents

1. [Execution overview](#1-execution-overview)
2. [Shared prerequisites](#2-shared-prerequisites)
3. [Manual test cases (7)](#3-manual-test-cases-7)
4. [Manual execution tracker](#4-manual-execution-tracker)
5. [Final QA summary template](#5-final-qa-summary-template)

---

## 1. Execution overview

### What Phase 1 already covers (do not re-test manually unless UI fails)

| Area | Automated cases | Manual focus |
|------|-----------------|--------------|
| Aggregation logic | TC-AGG-01 – 07 | None |
| Summary counts | TC-SUM-01 – 04 | None |
| Active alarms API | TC-ALM-01 – 04 (API) | **UI cards only** for TC-ALM-02 – 04 |
| Equipment health API | TC-EH-01 – 03 (API) | **UI card** for TC-EH-04 |
| Acknowledge API | TC-ACK-01 | **UI flow + network** for TC-ACK-02 – 04 |

### Recommended execution order (minimizes sheet resets)

| Order | Test case | Data set | Est. time |
|-------|-----------|----------|-----------|
| 1 | TC-ALM-02 | DATA-SET-B | 12 min |
| 2 | TC-ACK-03 | DATA-SET-B (reuse) | 10 min |
| 3 | TC-ALM-03 | DATA-SET-D | 12 min |
| 4 | TC-ACK-02 | DATA-SET-D (reuse) | 15 min |
| 5 | TC-ALM-04 | DATA-SET-E | 12 min |
| 6 | TC-EH-04 | DATA-SET-G | 15 min |
| 7 | TC-ACK-04 | No sheet data (code/console) | 8 min |

**Total estimated manual time:** **~1 hour 24 minutes** (84 min)

### Evidence folder

```
QA_Evidence/YYYY-MM-DD/manual/
├── screenshots/
├── api-responses/
└── network/
```

---

## 2. Shared prerequisites

Complete once before starting manual cases.

| Step | Action | Pass criteria |
|------|--------|---------------|
| P1 | Run automated suite | `cd backend && python -m pytest -q` → **35 passed** |
| P2 | Health check | `GET {BASE}/health` → `status: ok`, `dashboard_ready: true`, Sheets enabled |
| P3 | Open dashboard | Navigate to `{UI}/` (production or local) |
| P4 | Open DevTools | F12 → **Network** tab (preserve log ON) + **Console** tab |
| P5 | Google Sheet access | Edit access to GMD Readings tab; 10-column header present |
| P6 | Archive prior MCB-1 QA rows | Move old test rows to `QA_Archive` tab or delete to avoid ambiguity |
| P7 | Same backend session | Do **not** restart API server during TC-ACK-02 / TC-ACK-03 (ack state is in-memory) |

**Environment URLs**

| Resource | Production | Local |
|----------|------------|-------|
| UI | https://electrical-condition-monitoring-system.onrender.com/ | http://localhost:3000/ |
| API | https://electrical-condition-monitoring-system.onrender.com | http://127.0.0.1:8000 |

**Known UI limitation (not a fail unless undocumented):** Active alarm cards always display a red **ALARM** badge in the top-right of each card, even when the API `status` is `WARNING`. Verify severity via API and parameter/value on the card.

---

## 3. Manual test cases (7)

---

### TC-ALM-02 — One WARNING produces one alarm card (UI)

| Field | Detail |
|-------|--------|
| **Category** | Active Alarms — UI validation |
| **Phase 1 status** | API logic covered by `test_tc_alm.py` |
| **Estimated time** | **12 minutes** |

#### 1. Exact setup steps

1. In Google Sheet, insert **DATA-SET-B** (3 rows for MCB-1). See [Test data](#test-data-required-1) below.
2. Confirm column G (Status): `NORMAL`, `WARNING`, `NORMAL` respectively.
3. Wait ≤60 seconds **or** open dashboard and click **Refresh** (Recent readings section).
4. Hard-refresh browser (`Ctrl+Shift+R`) if cards do not appear.
5. Keep DevTools Network tab open.

#### 2. Test data required

**DATA-SET-B**

| Timestamp | Category | Equipment | Parameter | Value | Status |
|-----------|----------|-----------|-----------|-------|--------|
| 2026-06-08 10:00:00 | Blowers | MCB-1 | temperature | 42 | NORMAL |
| 2026-06-08 10:00:00 | Blowers | MCB-1 | current | 12 | WARNING |
| 2026-06-08 10:00:00 | Blowers | MCB-1 | vertical_vibration | 1.2 | NORMAL |

#### 3. API responses to verify

```http
GET {BASE}/dashboard/active-alarms
```

Expected (cross-check only — already automated):

```json
[
  {
    "equipment": "MCB-1",
    "parameter": "current",
    "value": "12",
    "status": "WARNING",
    "category": "Blowers",
    "id": "<16-character hex string>"
  }
]
```

- Array length = **1**
- `id` is non-empty

Save as `api-responses/TC-ALM-02_active_alarms.json`.

#### 4. UI behavior to verify

| # | UI element | Expected |
|---|------------|----------|
| 1 | Active alarms banner | Red banner visible; text **"1 active alarm — immediate action required"** |
| 2 | Alarm card count | Exactly **1** card with `data-testid="alarm-card"` |
| 3 | Card — equipment | **MCB-1** |
| 4 | Card — category | **Blowers** |
| 5 | Card — parameter | **current** (monospace, red) |
| 6 | Card — value | **12** |
| 7 | Card — Acknowledge button | Visible and clickable |
| 8 | Summary — Warning card | Shows **1** |
| 9 | Area health — MCB-1 | **0%** health (red) |

**Note:** Card badge may show **ALARM** (red) despite API `WARNING` — do not fail on badge alone.

#### 5. Screenshots to capture

| Filename | Content |
|----------|---------|
| `TC-ALM-02_sheet_rows.png` | Google Sheet DATA-SET-B rows |
| `TC-ALM-02_api.json` | active-alarms response |
| `TC-ALM-02_alarm_card.png` | Full alarm banner + single card |
| `TC-ALM-02_summary_warning.png` | Summary cards showing Warning = 1 |

#### 6. Pass / Fail criteria

| Result | Condition |
|--------|-----------|
| **PASS** | API returns 1 WARNING record for MCB-1/current; UI shows exactly 1 alarm card with correct equipment, parameter, value, and Acknowledge button |
| **FAIL** | Wrong card count; wrong parameter; missing Acknowledge; API empty but UI shows card (or reverse) |
| **BLOCKED** | Sheets not updating; dashboard not loading; cannot edit Status column |

#### 7. Estimated execution time

**12 minutes** (5 min sheet setup, 2 min cache wait, 5 min UI + evidence)

---

### TC-ALM-03 — WARNING + ALARM produces two parameter-level cards (UI)

| Field | Detail |
|-------|--------|
| **Category** | Active Alarms — UI validation |
| **Phase 1 status** | API logic covered by `test_tc_alm.py` |
| **Estimated time** | **12 minutes** |

#### 1. Exact setup steps

1. Remove or archive DATA-SET-B rows for MCB-1.
2. Insert **DATA-SET-D** (3 rows).
3. Wait ≤60s or click dashboard **Refresh**.
4. Verify active alarms section before screenshots.

#### 2. Test data required

**DATA-SET-D**

| Timestamp | Parameter | Value | Status |
|-----------|-----------|-------|--------|
| 2026-06-08 10:00:00 | temperature | 42 | NORMAL |
| 2026-06-08 10:00:00 | current | 12 | WARNING |
| 2026-06-08 10:00:00 | vertical_vibration | 8.0 | ALARM |

*(Category: Blowers, Equipment: MCB-1 for all rows)*

#### 3. API responses to verify

```http
GET {BASE}/dashboard/active-alarms
```

Expected:

- Array length = **2** (MCB-1 only; other equipment unaffected)
- Record 1: `parameter: current`, `status: WARNING`
- Record 2: `parameter: vertical_vibration`, `status: ALARM`
- Distinct non-empty `id` on each

Save as `api-responses/TC-ALM-03_active_alarms.json`.

#### 4. UI behavior to verify

| # | UI element | Expected |
|---|------------|----------|
| 1 | Banner text | **"2 active alarms — immediate action required"** |
| 2 | Alarm cards | Exactly **2** cards |
| 3 | Card A | MCB-1, parameter **current**, value **12**, Acknowledge visible |
| 4 | Card B | MCB-1, parameter **vertical_vibration**, value **8.0**, Acknowledge visible |
| 5 | Summary — Alarm card | Shows **1** (one equipment in alarm state) |
| 6 | Summary — Warning card | Shows **0** |

#### 5. Screenshots to capture

| Filename | Content |
|----------|---------|
| `TC-ALM-03_sheet.png` | DATA-SET-D in sheet |
| `TC-ALM-03_two_cards.png` | Both alarm cards visible in grid |
| `TC-ALM-03_api.json` | API response |

#### 6. Pass / Fail criteria

| Result | Condition |
|--------|-----------|
| **PASS** | API shows 2 records (current/WARNING + vertical_vibration/ALARM); UI shows 2 cards with matching parameters and values |
| **FAIL** | Card count ≠ 2; parameters mismatch API; only one severity shown when API has two |
| **BLOCKED** | Cannot load DATA-SET-D; server error on active-alarms |

#### 7. Estimated execution time

**12 minutes**

---

### TC-ALM-04 — Three ALARM parameters produce three cards (UI)

| Field | Detail |
|-------|--------|
| **Category** | Active Alarms — UI validation |
| **Phase 1 status** | API logic covered by `test_tc_alm.py` |
| **Estimated time** | **12 minutes** |

#### 1. Exact setup steps

1. Remove/archive MCB-1 rows from prior tests.
2. Insert **DATA-SET-E** (3 rows, all ALARM).
3. Wait ≤60s or click **Refresh**.
4. Count alarm cards before capturing evidence.

#### 2. Test data required

**DATA-SET-E**

| Timestamp | Parameter | Value | Status |
|-----------|-----------|-------|--------|
| 2026-06-08 10:00:00 | temperature | 90 | ALARM |
| 2026-06-08 10:00:00 | current | 20 | ALARM |
| 2026-06-08 10:00:00 | vertical_vibration | 9.0 | ALARM |

#### 3. API responses to verify

```http
GET {BASE}/dashboard/active-alarms
```

Expected:

- Array length = **3**
- Parameters: `temperature`, `current`, `vertical_vibration`
- All `status: ALARM`
- All `equipment: MCB-1`
- Three unique `id` values

Save as `api-responses/TC-ALM-04_active_alarms.json`.

#### 4. UI behavior to verify

| # | UI element | Expected |
|---|------------|----------|
| 1 | Banner text | **"3 active alarms — immediate action required"** |
| 2 | Alarm cards | Exactly **3** cards in grid |
| 3 | Parameters visible | temperature (90), current (20), vertical_vibration (9.0) |
| 4 | Each card | Acknowledge button present |
| 5 | Summary — Alarm | **1** (equipment-level, not 3) |

#### 5. Screenshots to capture

| Filename | Content |
|----------|---------|
| `TC-ALM-04_sheet.png` | DATA-SET-E rows |
| `TC-ALM-04_three_cards.png` | All three cards in one view (scroll if needed) |
| `TC-ALM-04_api.json` | API response |

#### 6. Pass / Fail criteria

| Result | Condition |
|--------|-----------|
| **PASS** | API returns 3 ALARM records; UI shows 3 cards with correct parameters/values; summary alarm count = 1 |
| **FAIL** | Card count ≠ 3; summary alarm = 3 (incorrect equipment-level counting) |
| **BLOCKED** | Sheet/API unavailable |

#### 7. Estimated execution time

**12 minutes**

---

### TC-EH-04 — `last_updated` reflects most recent parameter timestamp (UI)

| Field | Detail |
|-------|--------|
| **Category** | Equipment Health — UI + timestamp validation |
| **Phase 1 status** | Aggregation logic for DATA-SET-G covered by `test_tc_agg.py` |
| **Estimated time** | **15 minutes** |

#### 1. Exact setup steps

1. Remove/archive prior MCB-1 QA rows.
2. Insert **DATA-SET-G** with **two different timestamps** (09:00 and 10:00).
3. Wait ≤60s or click **Refresh**.
4. Scroll to **Area health overview** section.
5. Locate MCB-1 card (`data-testid="area-health-MCB-1"`).

#### 2. Test data required

**DATA-SET-G**

| Timestamp | Parameter | Value | Status |
|-----------|-----------|-------|--------|
| 2026-06-08 09:00:00 | vertical_vibration | 8.0 | ALARM |
| 2026-06-08 10:00:00 | temperature | 42 | NORMAL |
| 2026-06-08 10:00:00 | current | 8.5 | NORMAL |

#### 3. API responses to verify

```http
GET {BASE}/dashboard/equipment-health
```

Find MCB-1 object:

```json
{
  "equipment": "MCB-1",
  "latest_status": "ALARM",
  "health_percentage": 0.0,
  "latest_parameter": "vertical_vibration",
  "latest_timestamp": "2026-06-08 10:00:00",
  "last_updated": "Updated Today"
}
```

Key assertions:

- `latest_status` = **ALARM** (vibration ALARM must not be masked)
- `latest_timestamp` = **2026-06-08 10:00:00** (most recent reading across all parameters)
- `health_percentage` = **0.0**

Save as `api-responses/TC-EH-04_equipment_health.json`.

#### 4. UI behavior to verify

| # | UI element | Expected |
|---|------------|----------|
| 1 | MCB-1 health % | **0%** displayed in red |
| 2 | `last_updated` subtitle | **"Updated Today"** (if test run on same calendar day as 2026-06-08 data, use the relative label shown; if using live today's date in sheet, expect "Updated Today") |
| 3 | Equipment still in alarm state | 0% confirms ALARM aggregation despite newer NORMAL params |
| 4 | Summary — Alarm card | **1** |

**Tester note:** If sheet timestamps use today's date instead of `2026-06-08`, adjust expected `last_updated` accordingly. The critical check is: **recent timestamp + ALARM status coexist**.

#### 5. Screenshots to capture

| Filename | Content |
|----------|---------|
| `TC-EH-04_sheet_timestamps.png` | Rows showing 09:00 and 10:00 timestamps |
| `TC-EH-04_api.json` | MCB-1 excerpt from equipment-health |
| `TC-EH-04_area_health_card.png` | MCB-1 card with % and "Updated …" subtitle |

#### 6. Pass / Fail criteria

| Result | Condition |
|--------|-----------|
| **PASS** | API: `latest_status=ALARM`, `latest_timestamp` matches newest row (10:00); UI: 0% health and plausible `last_updated` text |
| **FAIL** | API shows NORMAL; `latest_timestamp` reflects 09:00 only; UI shows 100% |
| **BLOCKED** | MCB-1 card not visible in area health grid |

#### 7. Estimated execution time

**15 minutes**

---

### TC-ACK-02 — Acknowledged card disappears after refresh (UI)

| Field | Detail |
|-------|--------|
| **Category** | Alarm Acknowledgement — UI workflow |
| **Phase 1 status** | API ack contract covered by `test_tc_ack.py` |
| **Estimated time** | **15 minutes** |

#### 1. Exact setup steps

1. Use fresh **DATA-SET-D** (or re-insert if TC-ALM-03 already loaded it).
2. Confirm **2 alarm cards** visible.
3. **Do not restart** the backend server.
4. Click **Acknowledge** on the **current / WARNING** card only.
5. Wait for UI to refresh (auto-refresh up to 30s, or click **Refresh**).
6. Re-check card count and API.

#### 2. Test data required

**DATA-SET-D** (same as TC-ALM-03)

#### 3. API responses to verify

**Before acknowledge:**

```http
GET {BASE}/dashboard/active-alarms
```

→ 2 records

**After acknowledging current/WARNING card:**

```http
GET {BASE}/dashboard/active-alarms
```

→ 1 record remaining (`vertical_vibration` / ALARM)

Acknowledged `id` must not appear in response.

Save:

- `api-responses/TC-ACK-02_before.json`
- `api-responses/TC-ACK-02_after.json`

#### 4. UI behavior to verify

| # | Step | Expected |
|---|------|----------|
| 1 | Before ack | 2 alarm cards |
| 2 | Click Acknowledge on current card | No console error `POST FAILED` |
| 3 | After refresh | **1 card** remains (vertical_vibration) |
| 4 | Remaining card | Still shows Acknowledge button |
| 5 | Banner | **"1 active alarm — immediate action required"** |

#### 5. Screenshots to capture

| Filename | Content |
|----------|---------|
| `TC-ACK-02_before_two_cards.png` | Two cards before ack |
| `TC-ACK-02_after_one_card.png` | One card after ack |
| `TC-ACK-02_api_after.json` | API showing 1 remaining alarm |

#### 6. Pass / Fail criteria

| Result | Condition |
|--------|-----------|
| **PASS** | Acknowledged card removed from UI and API; unacknowledged card persists; no POST errors |
| **FAIL** | Both cards disappear; neither disappears; POST 404/500 |
| **BLOCKED** | Server restarted during test (ack state lost); no alarm cards to acknowledge |

#### 7. Estimated execution time

**15 minutes**

---

### TC-ACK-03 — Frontend calls correct acknowledge endpoint (Network)

| Field | Detail |
|-------|--------|
| **Category** | Alarm Acknowledgement — network validation |
| **Phase 1 status** | API path exists; this case validates **frontend wiring** |
| **Estimated time** | **10 minutes** |

#### 1. Exact setup steps

1. **Restart backend** OR use a new unacknowledged alarm (re-insert DATA-SET-B if prior tests acknowledged the alarm).
2. Load **DATA-SET-B** (1 alarm card).
3. Open DevTools → **Network** tab.
4. Filter by `acknowledge` or `dashboard`.
5. Clear network log.
6. Click **Acknowledge** on the MCB-1 card.
7. Inspect the captured POST request.

#### 2. Test data required

**DATA-SET-B** (one WARNING alarm on current)

#### 3. API responses to verify

Network request (primary evidence):

```http
POST {BASE}/dashboard/acknowledge-alarm/{16-char-id}
```

| Check | Expected |
|-------|----------|
| Method | `POST` |
| URL contains | `/dashboard/acknowledge-alarm/` |
| URL must NOT contain | `/acknowledge-alarm/` without `dashboard` prefix (legacy path) |
| Status code | `200` |
| Response body | `{"status":"ok","id":"<same-id>"}` |

Save network HAR or screenshot as `network/TC-ACK-03_post_request.png`.

#### 4. UI behavior to verify

| # | Expected |
|---|----------|
| 1 | Card disappears after successful POST |
| 2 | Console shows no `POST FAILED` error |
| 3 | Green "All systems normal" banner appears if no other alarms |

#### 5. Screenshots to capture

| Filename | Content |
|----------|---------|
| `TC-ACK-03_network_tab.png` | DevTools showing POST URL with `/dashboard/acknowledge-alarm/` |
| `TC-ACK-03_response_200.png` | Response preview with `status: ok` |

#### 6. Pass / Fail criteria

| Result | Condition |
|--------|-----------|
| **PASS** | POST goes to `/dashboard/acknowledge-alarm/{id}`; 200 response; card removed |
| **FAIL** | POST to legacy `/acknowledge-alarm/`; POST to `.../undefined`; 4xx/5xx response |
| **BLOCKED** | No network request fired; alarm already acknowledged |

#### 7. Estimated execution time

**10 minutes**

---

### TC-ACK-04 — Missing `id` does not send broken request (Guard)

| Field | Detail |
|-------|--------|
| **Category** | Alarm Acknowledgement — edge case / defensive coding |
| **Phase 1 status** | Not automated until Phase 2 (RTL) |
| **Estimated time** | **8 minutes** |

#### 1. Exact setup steps

**Method A — Source verification (recommended for intern)**

1. Open `frontend/src/pages/Dashboard.js`.
2. Locate `acknowledgeAlarm` function.
3. Confirm guard: `if (!alarmId) { console.error("Cannot acknowledge alarm without id"); return; }`.
4. Document line number in test evidence.

**Method B — Runtime verification (optional)**

1. Load dashboard with DATA-SET-B (1 alarm card).
2. Open DevTools → **Console** + **Network** (preserve log).
3. If card renders with valid `id` from API, confirm normal ack still uses valid id (sanity check).
4. Verify in source that button calls `acknowledgeAlarm(alarm.id)` — if `id` were missing, guard prevents POST.

**Method C — Advanced (optional)**

1. Use React DevTools to simulate alarm object without `id` (QA lead only).

#### 2. Test data required

None required for Method A.  
**DATA-SET-B** optional for Method B sanity check.

#### 3. API responses to verify

| Check | Expected |
|-------|----------|
| No request | `POST .../acknowledge-alarm/undefined` must **not** appear |
| Server health | `GET {BASE}/health` → still `ok` after test |

#### 4. UI behavior to verify

| # | Expected |
|---|----------|
| 1 | Application does not crash |
| 2 | Console logs `Cannot acknowledge alarm without id` when guard path triggered (Method C) |
| 3 | No unhandled exception in console |

#### 5. Screenshots to capture

| Filename | Content |
|----------|---------|
| `TC-ACK-04_source_guard.png` | Dashboard.js showing guard clause |
| `TC-ACK-04_console.png` | Console tab (if Method B/C used) |
| `TC-ACK-04_network_no_undefined.png` | Network tab showing no `undefined` POST |

#### 6. Pass / Fail criteria

| Result | Condition |
|--------|-----------|
| **PASS** | Guard clause present in source; no POST with `undefined` id; app remains stable |
| **FAIL** | Missing guard; POST to `/acknowledge-alarm/undefined` observed; UI crash |
| **BLOCKED** | Cannot access source code |

#### 7. Estimated execution time

**8 minutes** (Method A only: ~5 min)

---

## 4. Manual execution tracker

| Test Case | Title | Status | Evidence folder | Tester | Date | Remarks |
|-----------|-------|--------|-----------------|--------|------|---------|
| TC-ALM-02 | One WARNING → one UI card | ☐ Pass ☐ Fail ☐ Blocked | | | | |
| TC-ALM-03 | WARNING + ALARM → two UI cards | ☐ Pass ☐ Fail ☐ Blocked | | | | |
| TC-ALM-04 | Three ALARMs → three UI cards | ☐ Pass ☐ Fail ☐ Blocked | | | | |
| TC-EH-04 | last_updated + ALARM persistence | ☐ Pass ☐ Fail ☐ Blocked | | | | |
| TC-ACK-02 | Acknowledged card disappears | ☐ Pass ☐ Fail ☐ Blocked | | | | |
| TC-ACK-03 | Correct acknowledge endpoint | ☐ Pass ☐ Fail ☐ Blocked | | | | |
| TC-ACK-04 | Missing id guard | ☐ Pass ☐ Fail ☐ Blocked | | | | |

---

## 5. Final QA summary template

Copy and complete after automated + manual execution. Submit with evidence folder to QA Lead / Manager.

---

# Final QA Summary — GMD Condition Monitoring Dashboard

| Field | Value |
|-------|-------|
| **Report date** | |
| **Release / build** | v1.0.0 |
| **Environment tested** | ☐ Local ☐ Production ☐ Both |
| **Tester** | |
| **QA Lead** | |
| **Test period** | to |

---

### A. Test scope

| Layer | Cases | Method |
|-------|-------|--------|
| **Automated (Phase 1)** | 17 QA cases / 35 pytest tests | `python -m pytest` — mocked Sheets |
| **Manual (Phase 2)** | 7 QA cases | UI, network, timestamp validation |
| **Total QA coverage** | **24 unique functional cases** | 17 auto + 7 manual |

*Note: Full QA program originally defined 23 cases; TC-ACK-01 is automated; manual set is 7 UI/integration cases.*

---

### B. Automated test results (Phase 1)

| Metric | Value |
|--------|-------|
| Command | `cd backend && python -m pytest -v` |
| Date executed | |
| Tests collected | 35 |
| **Passed** | |
| **Failed** | |
| **Skipped** | |
| **Duration** | |
| **Result** | ☐ All pass (expected: **35 passed**) |

#### Automated case mapping

| QA ID | pytest file | Automated result |
|-------|-------------|------------------|
| TC-AGG-01 – 07 | `test_tc_agg.py` | ☐ Pass |
| TC-SUM-01 – 04 | `test_tc_sum.py` | ☐ Pass |
| TC-ALM-01 – 04 (API) | `test_tc_alm.py` | ☐ Pass |
| TC-EH-01 – 03 | `test_tc_eh.py` | ☐ Pass |
| TC-ACK-01 | `test_tc_ack.py` | ☐ Pass |

**Automated subtotal:** ___ / 17 cases (via 35 tests)

---

### C. Manual test results (Phase 2)

| Test Case | Result | Evidence | Remarks |
|-----------|--------|----------|---------|
| TC-ALM-02 | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ALM-03 | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ALM-04 | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-EH-04 | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ACK-02 | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ACK-03 | ☐ Pass ☐ Fail ☐ Blocked | | |
| TC-ACK-04 | ☐ Pass ☐ Fail ☐ Blocked | | |

**Manual subtotal:** ___ / 7 cases

---

### D. Defect summary

| Defect ID | Test case | Severity | Title | Status | Blocker? |
|-----------|-----------|----------|-------|--------|----------|
| | | ☐ Critical ☐ High ☐ Medium ☐ Low | | ☐ Open ☐ Fixed | ☐ |
| | | | | | ☐ |

| Severity | Count |
|----------|-------|
| Critical | |
| High | |
| Medium | |
| Low | |
| **Open blockers** | |

---

### E. Overall pass rate

| Category | Passed | Total | Rate |
|----------|--------|-------|------|
| Automated QA cases | | 17 | % |
| Manual QA cases | | 7 | % |
| **Combined functional QA** | | **24** | **%** |

**Calculation:**

```
Overall pass rate = (Automated cases passed + Manual cases passed) / 24 × 100
```

| Metric | Value |
|--------|-------|
| Automated cases passed | / 17 |
| Manual cases passed | / 7 |
| **Overall** | / 24 = **%** |

---

### F. Known limitations (accepted)

| # | Limitation | Affects | Accepted? |
|---|------------|---------|-----------|
| 1 | Alarm card badge always shows ALARM styling for WARNING | TC-ALM-02 | ☐ Yes |
| 2 | Acknowledgements reset on server restart | TC-ACK-02, TC-ACK-03 | ☐ Yes |
| 3 | Dashboard API cache 30–60s | All manual cases | ☐ Yes |
| 4 | Threshold auto-classification not enabled | Out of scope | ☐ Yes |

---

### G. Evidence package checklist

| Item | Included? |
|------|-----------|
| pytest output log (35 passed) | ☐ |
| `QA_Evidence/.../manual/screenshots/` (7 cases) | ☐ |
| API JSON files for manual cross-checks | ☐ |
| TC-ACK-03 network capture | ☐ |
| TC-ACK-04 source guard screenshot | ☐ |
| Manual execution tracker (Section 4) | ☐ |

---

### H. Deployment recommendation

Select **one**:

| Option | Criteria met |
|--------|--------------|
| ☐ **Approve for deployment** | 35/35 automated tests pass; 7/7 manual pass; zero open Critical/High defects |
| ☐ **Approve with conditions** | Minor UI issues documented; no functional blockers; limitations accepted |
| ☐ **Do not approve** | Automated failures; manual failures on ACK or ALM UI; open Critical/High defects |

**Recommendation summary (2–3 sentences):**

---

**Conditions / waivers (if conditional approve):**

---

### I. Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Tester (Intern) | | | |
| QA Lead | | | |
| Technical Lead | | | |
| Project Manager | | | |

**Deployment target:** https://electrical-condition-monitoring-system.onrender.com/

---

*End of Manual QA Execution Plan & Final QA Summary Template*
