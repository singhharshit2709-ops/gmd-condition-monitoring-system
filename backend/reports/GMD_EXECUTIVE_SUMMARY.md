# GMD Condition Monitoring System — Executive Summary

**Date:** 2026-06-12  
**Audience:** Project mentors, plant management, internship reviewers  
**System owner:** General Maintenance Department, Neutral Glass

---

## What This System Does

The GMD Condition Monitoring System digitizes daily engineering inspection rounds for a glass manufacturing plant. Operators record measurements — vibration, temperature, pressure, water quality, and electrical values — for **87 pieces of equipment** across four production tanks (A, E, G, K), the Utility Area, and DM Water systems. Data is stored in **Google Sheets** and visualized through a web dashboard that shows plant health, round completion progress, and active alerts.

---

## Business Value

| Benefit | Description |
|---------|-------------|
| **Operational visibility** | Single dashboard for all areas — no manual spreadsheet consolidation |
| **Round accountability** | Tracks which equipment has been inspected today vs pending |
| **Historical traceability** | Every reading timestamped with operator name and optional photo evidence |
| **Trend analysis** | Parameter charts support early fault detection |
| **Config flexibility** | New equipment added via JSON configuration — no code deployment required |

---

## System Scope (Current Release)

| Module | Status |
|--------|--------|
| Dashboard | ✅ Production use |
| Add Reading (V2 Round Sheet) | ✅ Production use |
| Equipment Monitoring | ✅ Functional |
| Reports | ✅ Functional |
| Trends & Analytics | ✅ Functional |
| Google Sheets integration | ✅ Production use |
| Media upload (Google Drive) | ✅ Production use |

**Plant coverage:** 87 equipment instances, 42 parameter types, 6 dashboard areas.

---

## Architecture (High Level)

A **React** web application communicates with a **Python FastAPI** backend. The backend validates submissions against a central **JSON configuration file** and persists readings to **Google Sheets**. The dashboard reads from the same sheet, ensuring a single source of truth. Optional photos attach via **Google Drive**.

This architecture was chosen for rapid deployment using familiar plant tools (Sheets) while maintaining a path toward industrial IoT integration (OPC-UA, MQTT) in future phases.

---

## Key Metrics Explained

- **Health %** (area cards): Percentage of *today's inspected* equipment in normal status — resets each day.
- **Round completion**: Equipment with at least one reading today ÷ total configured equipment per area.
- **Pending**: Equipment not yet inspected today.
- **Alerts**: Parameters in Warning or Alarm status based on stored sheet data.

---

## Honest Assessment

**Strengths:** Config-driven design scales with plant changes; clean modular codebase; comprehensive test coverage on backend; professional dashboard UX suitable for control-room displays.

**Gaps to address before full Industry 4.0 classification:**

1. Automatic Warning/Alarm status on new submissions (thresholds exist in config but not yet applied on save).
2. User authentication for production deployment.
3. Long-term data storage strategy as sheet row count grows.

**Overall grade:** Production-ready for **internal plant deployment** with Google credentials and network access. Recommended as internship/portfolio centerpiece demonstrating full-stack engineering, industrial domain knowledge, and config-driven architecture.

---

## Documentation Package

| File | Purpose |
|------|---------|
| `GMD_TECHNICAL_DOCUMENTATION.md` | Full 10-part technical reference |
| `GMD_TECHNICAL_DOCUMENTATION_WORD.md` | Word-importable version |
| `GMD_EXECUTIVE_SUMMARY.md` | This document |
| `PLANT_HIERARCHY_APPENDIX.md` | Complete equipment listing |
| `PARAMETER_CATALOGUE.md` | Parameter key reference |
| `PARAMETER_EQUIPMENT_MATRIX.md` | Full parameter-to-equipment map |

---

## Recommended Next Steps

1. Enable threshold-based status on submission (highest ROI for dashboard accuracy).
2. Deploy behind plant VPN with service account credential management.
3. Train operators on Utility Area tag workflow and daily round completion targets.
4. Plan Phase 2 analytics database for multi-year trend retention.

---

*Prepared for manager review, internship documentation, project handover, and developer onboarding.*
