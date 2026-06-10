# GMD Threshold Collection — Engineering & Maintenance Instructions

**Project:** Neutral Glass — GMD Condition Monitoring System  
**Purpose:** Collect approved Normal and Warning limits before enabling automatic status classification  
**System version:** GMD schema v1.0.0 (25 equipment assets, 89 parameter rows)  
**Classification rule:** `NORMAL` if value &lt; Normal_Limit · `WARNING` if Normal_Limit ≤ value ≤ Warning_Limit · `ALARM` if value &gt; Warning_Limit

---

## Files in This Package

| File | Use |
|------|-----|
| `GMD_Threshold_Collection_Template.csv` | **Blank template** — one row per equipment × parameter (89 rows). Open in Excel, fill limits, return for approval. |
| `GMD_Threshold_Example_MCB-1.csv` | **Worked example** for MCB-1 only — shows expected format and illustrative values. |
| `GMD_Threshold_Collection_Instructions.md` | This document |

---

## Who Should Complete What

| Role | Responsibility |
|------|----------------|
| **Maintenance / Field** | Confirm equipment names, parameters monitored, and typical operating ranges |
| **Electrical / Mechanical Engineering** | Define Normal and Warning limits from OEM manuals, nameplate data, and plant history |
| **Maintenance Lead** | Review completeness (all 89 rows), sign-off in `Approved_By` / `Approval_Date` |
| **IT / GMD Dashboard Team** | Import approved CSV into `gmd_machine_config.json` after sign-off |

---

## Excel Workflow (Recommended)

### Sheet 1 — `Threshold_Matrix` (main data)

Copy columns from `GMD_Threshold_Collection_Template.csv`:

| Column | Required | Description |
|--------|----------|-------------|
| A — Category | Yes (pre-filled) | Must match exactly: `Blowers`, `DM Water Electrode Cooling`, `Cooling Tower Water Monitoring`, `Utility Area Monitoring` |
| B — Equipment | Yes (pre-filled) | Must match exactly (e.g. `MCB-1`, not `MCB1` or `MCB 1`) |
| C — Parameter_Key | Yes (pre-filled) | **System key** — do not rename (e.g. `vertical_vibration`, not `Vertical Vibration`) |
| D — Parameter_Display_Name | Info only | Human-readable label |
| E — Unit | Info only | Engineering unit for limits |
| F — Normal_Limit | **Required** | Upper bound of normal (healthy) zone — values **below** this are NORMAL |
| G — Warning_Limit | **Required** | Upper bound of warning zone — values **above** this are ALARM |
| H — Data_Source | Recommended | OEM manual, nameplate, historical P95, SOP reference |
| I — Approved_By | Required at sign-off | Name / role |
| J — Approval_Date | Required at sign-off | `YYYY-MM-DD` |
| K — Notes | Optional | Assumptions, seasonal variation, bidirectional-limit caveats |

### Sheet 2 — `Validation_Rules` (reference)

Copy the validation rules section from this document for reviewers.

### Sheet 3 — `Parameter_Dictionary` (reference)

Copy the parameter list section from this document.

### Sheet 4 — `Sign_Off` (approval)

| Field | Value |
|-------|-------|
| Document version | 1.0 |
| Plant / Site | Neutral Glass |
| Prepared by | |
| Reviewed by (Engineering) | |
| Approved by (Maintenance Head) | |
| Approval date | |
| Comments | |

---

## Validation Rules for Threshold Values

Apply these rules before submitting. Invalid rows will be rejected at system import.

### Structural rules

1. **Completeness:** All **89 rows** must have numeric `Normal_Limit` and `Warning_Limit` unless explicitly marked N/A with written justification in `Notes` (N/A parameters will not be auto-classified).
2. **Numeric:** Limits must be non-negative numbers (integers or decimals). No text, blanks, or units in limit cells.
3. **Ordering:** `Warning_Limit` must be **strictly greater than** `Normal_Limit` for every row.
4. **Key integrity:** Do not change `Category`, `Equipment`, or `Parameter_Key` values — they must match the bulk-entry form exactly.
5. **One row per parameter:** Do not merge rows or duplicate equipment-parameter pairs.

### Engineering rules

6. **Higher-is-worse assumption:** The system classifies **higher measured values as more severe**. Limits define the upper boundary of each zone. If a parameter is naturally **lower-is-worse** (e.g. under-voltage, low pH), document the issue in `Notes` — engineering may need to supply inverted limits or a separate review before go-live.
7. **OEM precedence:** Prefer manufacturer recommended alarm/warning setpoints where available.
8. **Plant context:** Limits should reflect actual Neutral Glass operating conditions, not generic catalogue values.
9. **Axis-specific vibration:** `vertical_vibration`, `horizontal_vibration`, and `axial_vibration` may have **different** limits per axis — do not assume they are identical unless justified.
10. **Water quality (TDS, pH):** Confirm whether high-only limits are appropriate for your SOP. Bidirectional quality bands may require engineering discussion with the IT team.

### Sign-off rules

11. **Traceability:** Every row should have `Data_Source` filled before approval.
12. **Version control:** Save the approved file as `GMD_Thresholds_Approved_YYYY-MM-DD.csv` and retain prior drafts.

---

## Exact Parameter List Requiring Limits

Ten distinct parameter types are used across the GMD system. Keys must be spelled exactly as shown.

| # | Parameter_Key | Display Name | Unit | Monitored On |
|---|---------------|--------------|------|--------------|
| 1 | `vertical_vibration` | Vertical Vibration | mm/s | Blowers, compressors, cooling tower pump |
| 2 | `horizontal_vibration` | Horizontal Vibration | mm/s | Blowers, compressors, cooling tower pump |
| 3 | `axial_vibration` | Axial Vibration | mm/s | MCB-1/2/3, screw compressor only |
| 4 | `temperature` | Temperature | °C | Mechanical equipment, receivers, DG set, electrode cooling |
| 5 | `water_temperature` | Water Temperature | °C | Cooling tower assets and CT water monitoring |
| 6 | `current` | Current | A | Motors, blowers, compressors, DG set, electrode cooling |
| 7 | `voltage` | Voltage | V | MCB-1/2/3, electrode cooling, DG set |
| 8 | `pressure` | Pressure | bar | Air dryer, air receivers |
| 9 | `tds` | TDS | ppm | Cooling tower water monitoring |
| 10 | `ph` | pH | pH | Cooling tower water monitoring |

**Total collection scope:** 25 equipment assets × 89 equipment-parameter rows.

---

## Equipment-Wise Threshold Matrix (Summary)

### Blowers (9 equipment · 42 rows)

| Equipment | Parameters (count) |
|-----------|---------------------|
| MCB-1 | vertical_vibration, horizontal_vibration, axial_vibration, temperature, current, voltage (6) |
| MCB-2 | same as MCB-1 (6) |
| MCB-3 | same as MCB-1 (6) |
| Gas Blower-1 | vertical_vibration, horizontal_vibration, temperature, current (4) |
| Gas Blower-2 | vertical_vibration, horizontal_vibration, temperature, current (4) |
| Chimney Blower | vertical_vibration, horizontal_vibration, temperature, current (4) |
| Tank Cooling Blower | vertical_vibration, horizontal_vibration, temperature, current (4) |
| Cooling Blower | vertical_vibration, horizontal_vibration, temperature, current (4) |
| Throat Cooling Blower | vertical_vibration, horizontal_vibration, temperature, current (4) |

### DM Water Electrode Cooling (4 equipment · 12 rows)

| Equipment | Parameters (count) |
|-----------|---------------------|
| G Tank Electrode Cooling | temperature, current, voltage (3) |
| K Tank Electrode Cooling | temperature, current, voltage (3) |
| E Tank Electrode Cooling | temperature, current, voltage (3) |
| K & E Tank Batch Charger | temperature, current, voltage (3) |

### Cooling Tower Water Monitoring (3 equipment · 9 rows)

| Equipment | Parameters (count) |
|-----------|---------------------|
| Compressor House CT | water_temperature, tds, ph (3) |
| G Tank CT | water_temperature, tds, ph (3) |
| A Tank CT | water_temperature, tds, ph (3) |

### Utility Area Monitoring (9 equipment · 26 rows)

| Equipment | Parameters (count) |
|-----------|---------------------|
| Screw Compressor | vertical_vibration, horizontal_vibration, axial_vibration, temperature, current (5) |
| Centrifugal Compressor | vertical_vibration, horizontal_vibration, temperature, current (4) |
| Air Dryer | temperature, pressure (2) |
| Cooling Tower Pump | vertical_vibration, horizontal_vibration, temperature (3) |
| Cooling Tower | water_temperature, tds, ph (3) |
| Oil Air Receiver | pressure, temperature (2) |
| Utility Area Receiver | pressure, temperature (2) |
| G Tank Air Receiver | pressure, temperature (2) |
| DG Set | temperature, current, voltage (3) |

Full row-level detail is in `GMD_Threshold_Collection_Template.csv`.

---

## Example Completed Threshold Sheet — MCB-1

**Category:** Blowers · **Equipment:** MCB-1 (Mold Cooling Blower)

> **Disclaimer:** Values below are **illustrative** for format demonstration. Some limits are cross-referenced from the legacy GT `machine_config.json` (MCB1 under Mold Cooling Blower). **Maintenance and engineering must verify and replace all values before production approval.**

| Parameter_Key | Unit | Normal_Limit | Warning_Limit | Data_Source | Notes |
|---------------|------|-------------|---------------|-------------|-------|
| vertical_vibration | mm/s | 6.0 | 10.0 | GT reference / OEM | Verify per-axis if OEM differs |
| horizontal_vibration | mm/s | 6.0 | 10.0 | GT reference / OEM | Verify per-axis if OEM differs |
| axial_vibration | mm/s | 6.0 | 10.0 | GT reference / OEM | Verify per-axis if OEM differs |
| temperature | °C | 60 | 75 | GT reference / OEM | Bearing/winding operating limit |
| current | A | 200 | 240 | GT reference / nameplate | 160 kW motor — confirm nameplate FLA |
| voltage | V | 380 | 440 | **ILLUSTRATIVE** | Confirm nominal line voltage and tolerance band |

**Classification preview (once approved):**

| Sample reading | Parameter | Result |
|----------------|-----------|--------|
| 1.2 | vertical_vibration | NORMAL (&lt; 6.0) |
| 8.0 | vertical_vibration | WARNING (6.0–10.0) |
| 11.5 | vertical_vibration | ALARM (&gt; 10.0) |
| 42 | temperature | NORMAL |
| 68 | temperature | WARNING |
| 80 | temperature | ALARM |
| 12 | current | NORMAL |
| 220 | current | WARNING |
| 250 | current | ALARM |

See `GMD_Threshold_Example_MCB-1.csv` for the import-ready row format.

---

## Engineering Inputs Required Before Implementation

Checklist for the GMD IT team — **all items must be complete before development begins:**

- [ ] Approved CSV with all 89 rows populated (or justified N/A entries)
- [ ] Sign-off sheet with engineering and maintenance lead approval
- [ ] Confirmation that higher-is-worse classification is valid for every parameter (or documented exceptions)
- [ ] Data source traceability for each limit (OEM page, SOP section, or historical basis)
- [ ] Resolution of any bidirectional parameters (pH, TDS, voltage) per plant SOP
- [ ] Agreement on whether MCB-1/2/3 limits match legacy GT Mold Cooling Blower values or require separate GMD-specific values
- [ ] Final CSV saved as `GMD_Thresholds_Approved_YYYY-MM-DD.csv` and delivered to IT

---

## Contact / Return Instructions

1. Open `GMD_Threshold_Collection_Template.csv` in Excel.
2. Fill columns F (`Normal_Limit`) and G (`Warning_Limit`) for all applicable rows.
3. Complete `Data_Source`, `Approved_By`, and `Approval_Date` at sign-off.
4. Run validation rules (Section above) before submission.
5. Return the approved file to the GMD Dashboard / IT team for import into `gmd_machine_config.json`.

---

*Generated from GMD equipment configuration (`equipmentConfig.js` / `gmd_machine_config.json`). Parameter keys must remain synchronized with the bulk-entry form.*
