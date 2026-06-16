# GMD Equipment Parameter & Threshold Master

| Field | Value |
|-------|-------|
| **Title** | GMD Condition Monitoring System — Equipment Parameter Threshold Master |
| **Prepared By** | Harshit Singh |
| **Version** | 1.0 |
| **Purpose** | To collect finalized Warning and Alarm threshold values from the User Department before production deployment. |

---

## Files

| File | Use |
|------|-----|
| `GMD_Equipment_Parameter_Threshold_Master.xlsx` | **Preferred for sharing** — Instructions sheet + formatted Threshold Master |
| `GMD_Equipment_Parameter_Threshold_Master.csv` | Plain data export (same content as Threshold Master sheet) |
| `GMD_Equipment_Parameter_Threshold_Master_Validation.txt` | Row/equipment count verification |

---

## Important Notes

1. **Proposed Warning Limit** and **Proposed Alarm Limit** are provisional engineering reference values only. They are **not approved** for production classification.

2. **Final Warning Limit** and **Final Alarm Limit** must be completed by the User Department.

3. Complete **Approved By**, **Reviewed By User Department**, and **Approval Date** before returning the document.

4. All values are **subject to approval** before production deployment and before automatic WARNING/ALARM status is enabled in the live system.

5. **Remarks** — leave blank unless equipment-specific clarification is required.

---

## Regeneration

```bash
cd backend
pip install openpyxl
python scripts/export_parameter_threshold_master.py
```

Output is written to this `templates/` folder.
