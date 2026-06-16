# Threshold Master Integrity Report

**GMD Equipment Parameter & Threshold Master**  
**Validation Timestamp:** 2026-06-15 10:24 IST  
**Audit Script:** `backend/scripts/audit_parameter_threshold_master.py`  
**Export Script:** `backend/scripts/export_parameter_threshold_master.py`  
**Config Source:** `backend/gmd_machine_config_v2.json` (same as frontend `@gmd-config/v2`)  
**Result:** PASS — 0 mismatches vs live dashboard configuration

---

## Executive Summary

The Threshold Master is a **1:1 representation** of the live Add Reading configuration. All areas, categories, equipment, tag numbers, parameters, and units match the V2 machine config exactly. Proposed limits are sourced from config where defined; Final limit columns remain blank pending User Department approval.

---

## Row Counts & Integrity Summary

| Metric | Count |
|--------|------:|
| **Total Areas (physical Area / Tank)** | **5** |
| **Total Categories** | **5** |
| **Total Equipment** | **87** |
| **Total Unique Parameter Keys** | **42** |
| **Total Threshold Rows** | **1,002** |
| Config vs export mismatches | 0 |
| DM Water as Area/Tank (must be 0) | 0 |
| Repetitive provisional remarks | 0 |

### Physical Areas

A Tank, E Tank, G Tank, K Tank, Utility Area

### Categories

Blowers, Cooling Tower Water Monitoring, DM Water Batch Charger, DM Water Electrode Cooling, Utility Area Monitoring

---

## Area-wise Breakdown

### A Tank

| Category | Equipment | Parameters |
|----------|----------:|-----------:|
| Blowers | 13 | 208 |
| Cooling Tower Water Monitoring | 1 | 3 |
| DM Water Batch Charger | 1 | 1 |
| DM Water Electrode Cooling | 1 | 3 |

### E Tank

| Category | Equipment | Parameters |
|----------|----------:|-----------:|
| Blowers | 12 | 192 |
| DM Water Electrode Cooling | 1 | 3 |

### G Tank

| Category | Equipment | Parameters |
|----------|----------:|-----------:|
| Blowers | 13 | 208 |
| Cooling Tower Water Monitoring | 1 | 3 |
| DM Water Electrode Cooling | 1 | 3 |

### K Tank

| Category | Equipment | Parameters |
|----------|----------:|-----------:|
| Blowers | 11 | 176 |
| DM Water Batch Charger | 1 | 1 |
| DM Water Electrode Cooling | 1 | 3 |

### Utility Area

| Category | Equipment | Parameters |
|----------|----------:|-----------:|
| Cooling Tower Water Monitoring | 1 | 3 |
| Utility Area Monitoring | 29 | 195 |

---

## Column Verification (17 columns)

| Column | Present | Notes |
|--------|---------|-------|
| Area / Tank | PASS | Physical areas only — DM Water is Category |
| Category | PASS | Matches Add Reading categories |
| Equipment | PASS | 87 instances incl. utility disambiguation |
| Tag No | PASS | Utility tags where configured |
| Parameter Key | PASS | Stable V2 keys |
| Parameter Display Name | PASS | Human-readable labels |
| Unit | PASS | Engineering units from config |
| Proposed Normal Limit | PASS | From config where defined; blank otherwise |
| Proposed Warning Limit | PASS | From config where defined |
| Proposed Alarm Limit | PASS | From config where defined |
| Final Normal Limit | PASS | **Blank — User Department to complete** |
| Final Warning Limit | PASS | **Blank — User Department to complete** |
| Final Alarm Limit | PASS | **Blank — User Department to complete** |
| Approved By | PASS | Column present — blank |
| Reviewed By User Department | PASS | Column present — blank |
| Approval Date | PASS | Column present — blank |
| Remarks | PASS | Column present — no fabricated provisional text |

---

## Add Reading Alignment Verification

| Check | Result |
|-------|--------|
| All configured areas represented | PASS |
| All 87 equipment instances covered | PASS |
| Parameter keys match V2 config | PASS |
| MCB-1 vertical vibration key present | PASS |
| Utility LP/HP disambiguated (`display_name (equipment_kind)`) | PASS |
| No legacy placeholder equipment (Compressor C1, etc.) | PASS |
| Export source is `gmd_machine_config_v2.json` only | PASS |
| Automated tests (`test_parameter_threshold_master.py`) | 9/9 PASS |

---

## Key Equipment Verification

| Equipment | Status |
|-----------|--------|
| MCB-1 | PASS |
| MCB-2 | PASS |
| MCB-3 | PASS |
| Chimney Blowers | PASS |
| Cooling Blowers | PASS |
| Block Cooling Blowers | PASS |
| Comp-1 | PASS |
| Comp-2 | PASS |
| Pilot Air | PASS |
| Air Dryer LP | PASS |
| Air Dryer HP | PASS |
| Centac | PASS |
| Cooling Towers | PASS |
| DM Water Electrode Cooling | PASS |

---

## DM Water Architecture Check

**Requirement:** DM Water appears as **Category under each Tank**, NOT as a separate Area / Tank column value.

| Check | Result |
|-------|--------|
| Rows with DM Water as Area / Tank | 0 (PASS) |
| A Tank: DM Water Batch Charger + Electrode Cooling | PASS |
| E Tank: DM Water Electrode Cooling | PASS |
| G Tank: DM Water Electrode Cooling | PASS |
| K Tank: DM Water Batch Charger + Electrode Cooling | PASS |

---

## Output Artifacts

| File | Location |
|------|----------|
| Excel workbook (Instructions + Threshold Master) | `templates/GMD_Equipment_Parameter_Threshold_Master.xlsx` |
| CSV export | `templates/GMD_Equipment_Parameter_Threshold_Master.csv` |
| Validation summary | `templates/GMD_Equipment_Parameter_Threshold_Master_Validation.txt` |
| Integrity audit (machine-readable) | `templates/GMD_Equipment_Parameter_Threshold_Master_Integrity_Audit.txt` |
| Instructions | `templates/GMD_Equipment_Parameter_Threshold_Master_Instructions.md` |

**Do not use:** `GMD_Threshold_Collection_Template.csv` (legacy placeholder data)

---

## Post-Approval Workflow

1. User Department completes **Final Normal / Warning / Alarm** columns
2. Engineering imports approved limits into `gmd_machine_config_v2.json`
3. Set `GMD_THRESHOLD_CLASSIFICATION_ENABLED=true` in production
4. Re-run audit script to confirm config ↔ master alignment

---

*Integrity audit PASS — ready to share with management and User Department — 2026-06-15.*
