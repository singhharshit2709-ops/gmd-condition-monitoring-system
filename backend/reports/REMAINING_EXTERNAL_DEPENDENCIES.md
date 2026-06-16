# Remaining External Dependencies

**GMD Condition Monitoring System**  
**Date:** 2026-06-12

---

## Current Remaining Dependency

### Final Limiting Values / Threshold Parameters

**Status:** Pending engineering approval  
**Impact:** Dashboard WARNING/ALARM counts on **new submissions** remain NORMAL until enabled  
**Deployment blocker:** **No**

The system architecture is complete and ready. Threshold values exist in `gmd_machine_config_v2.json` as **provisional** references only. Automatic classification is intentionally disabled until final limits are approved.

---

## Enabling Threshold Classification (Post-Approval)

When final values are available:

1. Update parameter `thresholds` blocks in `gmd_machine_config_v2.json`:
   - Set `provisional: false`
   - Set `enabled: true`
   - Provide `normal_limit`, `warning_limit`, and optionally `alarm_limit`

2. Enable classification at runtime:

```env
GMD_THRESHOLD_CLASSIFICATION_ENABLED=true
GMD_THRESHOLD_ALLOW_PROVISIONAL=false
```

3. Restart backend — no code changes required.

**Data flow when enabled:**

```
Parameter thresholds (config)
  → threshold_service.classify_v2_parameter_status()
  → status written to Google Sheets
  → Dashboard / Reports / Alerts / Analytics
```

---

## Other External Dependencies (Operational)

| Dependency | Purpose | Action Required |
|------------|---------|-----------------|
| Google Service Account | Sheets + Drive API | Share spreadsheet with service account email |
| `GOOGLE_SHEET_ID` | Target spreadsheet | Set in Render/hosting env |
| `GOOGLE_DRIVE_FOLDER_ID` | Media uploads | Optional; set if using attachments |
| Hosting (Render) | Production runtime | Deploy backend + static frontend |
| One-time sheet migration | Legacy Readings → area tabs | Run `migrate_readings_to_area_sheets.py` |

---

## Deployment Statement

**Deployment can be completed immediately** after standard infrastructure configuration (Google credentials, spreadsheet sharing, env vars). Final threshold values can be integrated **without architectural changes** once engineering provides approved limits.

---

*Document generated as part of GMD deployment readiness phase.*
