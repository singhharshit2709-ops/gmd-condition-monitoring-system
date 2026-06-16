# Final Deployment Checklist

**GMD Condition Monitoring System — Production Deployment Package**  
**Validation Timestamp:** 2026-06-15 10:24 IST  
**Prepared for:** Management / User Department handoff

---

## Readiness Sign-Off

| Component | Status |
|-----------|--------|
| Frontend | **READY** |
| Backend | **READY** |
| Google Sheets | **READY** |
| Multi-sheet routing | **READY** |
| Dashboard | **READY** |
| Add Reading | **READY** |
| Equipment Monitoring | **READY** |
| Reports | **READY** |
| Trends & Analytics | **READY** |
| Threshold architecture | **READY** |

### Deployment Blocker

| Item | Owner | Blocks Deploy? |
|------|-------|----------------|
| Final Normal / Warning / Alarm limits | User Department | **No** — system deploys with NORMAL status |

---

## Pre-Deployment — Environment

- [ ] `GOOGLE_SHEETS_ENABLED=true`
- [ ] `GOOGLE_SHEET_ID` set to production spreadsheet
- [ ] Google service account JSON configured and shared with spreadsheet (Editor)
- [ ] `GOOGLE_SHEETS_AREA_LAYOUT=multi`
- [ ] `GOOGLE_SHEETS_INCLUDE_LEGACY_READINGS=true` (during migration period)
- [ ] `GMD_THRESHOLD_CLASSIFICATION_ENABLED=false` (until limits approved)
- [ ] `REACT_APP_BACKEND_URL` points to production backend
- [ ] Google Drive folder ID set (if media uploads required)

---

## Pre-Deployment — Google Sheets Setup

- [ ] Confirm worksheets exist or will auto-create on first write:
  - [ ] A Tank
  - [ ] E Tank
  - [ ] G Tank
  - [ ] K Tank
  - [ ] Utility Area
  - [ ] DM Water Electrode Cooling
- [ ] Each worksheet has canonical 17-column header (auto-repaired on init)
- [ ] Run migration if historical data in legacy `Readings` tab:
  ```bash
  cd backend
  python scripts/migrate_readings_to_area_sheets.py --dry-run
  python scripts/migrate_readings_to_area_sheets.py
  ```

---

## Pre-Deployment — Threshold Master Package

- [ ] Share `templates/GMD_Equipment_Parameter_Threshold_Master.xlsx` with User Department
- [ ] Confirm 1,002 rows / 87 equipment / 42 parameter keys
- [ ] User Department completes Final Normal / Warning / Alarm columns
- [ ] User Department completes Approved By / Reviewed By / Approval Date where applicable
- [ ] Engineering imports approved limits into config (post-deploy enhancement)

---

## Pre-Deployment — Automated Verification (Completed)

- [x] Backend pytest: **87/87 PASS**
- [x] Threshold audit: **0 mismatches**
- [x] Sheets area routing: **5/5 physical + DM virtual PASS**
- [x] Sheets row schema: **17 columns PASS**
- [x] V2 preview/submit: **14 tests PASS**
- [x] Dashboard calculations: **35 tests PASS**
- [x] Trends API: **3 tests PASS**
- [x] Threshold export tests: **9 tests PASS**

---

## Post-Deployment — Smoke Tests

### Add Reading (one submission per routing target)

- [ ] A Tank blower reading → row in `A Tank` tab
- [ ] E Tank blower reading → row in `E Tank` tab
- [ ] G Tank blower reading → row in `G Tank` tab
- [ ] K Tank blower reading → row in `K Tank` tab
- [ ] Utility Area reading → row in `Utility Area` tab
- [ ] DM Water category reading → row in `DM Water Electrode Cooling` tab

### Field verification (each smoke row)

- [ ] Correct timestamp format
- [ ] Correct area_tank, category, equipment, tag_no
- [ ] Correct parameter_key, display name, unit, value
- [ ] Correct verified_by and remarks
- [ ] Correct status (NORMAL until thresholds enabled)
- [ ] Media fields populated when attachment uploaded

### Dashboard

- [ ] Plant banner loads
- [ ] KPI cards reflect sheet data
- [ ] Area cards show health
- [ ] Recent readings include smoke submissions
- [ ] Recent alerts display WARNING/ALARM rows (if any)
- [ ] Footer and today's round completion render

### Equipment Monitoring

- [ ] Equipment list populated
- [ ] Latest snapshot shows recent values
- [ ] Historical chart renders for selected parameter

### Reports

- [ ] Area filter works
- [ ] Equipment filter works
- [ ] CSV export downloads

### Trends & Analytics

- [ ] Trend chart generates for numeric parameter
- [ ] Date window filter works
- [ ] Historical aggregation correct

---

## Post-Deployment — Threshold Enablement (After User Department Approval)

- [ ] Import final limits into `gmd_machine_config_v2.json`
- [ ] Re-export and audit threshold master for record
- [ ] Set `GMD_THRESHOLD_CLASSIFICATION_ENABLED=true`
- [ ] Submit test reading above warning limit → verify WARNING/ALARM status
- [ ] Confirm dashboard alarms reflect new classifications

---

## Documentation Package

| Document | Path |
|----------|------|
| Deployment Readiness Report | `backend/reports/DEPLOYMENT_READINESS_REPORT.md` |
| End-to-End Test Report | `backend/reports/END_TO_END_TEST_REPORT.md` |
| Google Sheets Architecture | `backend/reports/GOOGLE_SHEETS_ARCHITECTURE.md` |
| Threshold Master Integrity | `backend/reports/THRESHOLD_MASTER_INTEGRITY_REPORT.md` |
| This Checklist | `backend/reports/FINAL_DEPLOYMENT_CHECKLIST.md` |
| Threshold Master Workbook | `templates/GMD_Equipment_Parameter_Threshold_Master.xlsx` |
| External Dependencies | `backend/reports/REMAINING_EXTERNAL_DEPENDENCIES.md` |

---

## Known Non-Blockers

| Item | Notes |
|------|-------|
| Frontend Jest runner | Pre-existing babel/craco issue — does not affect production runtime |
| Alarm acknowledgement | In-memory only — lost on restart |
| V2 submit status | NORMAL until threshold classification enabled |
| KnowledgeBase page | Exists but not routed in App.js |

---

*Final deployment checklist — verification complete 2026-06-15. No code changes required.*
