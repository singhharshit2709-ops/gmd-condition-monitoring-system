# GMD Condition Monitoring Dashboard — Internship Project Documentation

**Organization context:** Neutral Glass — General Maintenance Department (GMD)  
**Project:** GMD Condition Monitoring Dashboard  
**Version:** 1.0.0  
**Production URL:** https://electrical-condition-monitoring-system.onrender.com/  
**Repository:** https://github.com/singhharshit2709-ops/electrical-condition-monitoring-system  
**Document date:** June 2026

---

## Table of Contents

1. [Internship Project Summary](#1-internship-project-summary)
2. [Project Objectives](#2-project-objectives)
3. [Problem Statement](#3-problem-statement)
4. [System Architecture](#4-system-architecture)
5. [Industry 4.0 Concepts Applied](#5-industry-40-concepts-applied)
6. [Technical Challenges Solved](#6-technical-challenges-solved)
7. [QA and Validation Activities](#7-qa-and-validation-activities)
8. [Deployment Readiness Activities](#8-deployment-readiness-activities)
9. [Future Scope](#9-future-scope)
10. [Key Achievements](#10-key-achievements)
11. [Resume Bullet Points](#11-resume-bullet-points)
12. [LinkedIn Project Description](#12-linkedin-project-description)
13. [Interview Talking Points](#13-interview-talking-points)
14. [Internship Report Summary](#14-internship-report-summary)

---

## 1. Internship Project Summary

The **GMD Condition Monitoring Dashboard** is a production-deployed web application built for Neutral Glass’s General Maintenance Department to digitize equipment health monitoring across plant utility and production support systems.

The system replaces manual, paper-based condition monitoring with a **cloud-hosted React dashboard** backed by a **FastAPI REST API** and **Google Sheets** as the operational data store. Maintenance technicians submit readings through a structured bulk-entry form; engineers and supervisors view real-time equipment health, active alarms, trend analytics, and historical reports from any browser.

During this internship, development reached production-ready status: core features were implemented, **equipment status aggregation** was enhanced to correctly compute worst-case health per asset, an **alarm acknowledgement workflow** was added, a **multi-layer validation framework** was introduced, and a structured **QA program** was executed — including **35 automated pytest tests** and a **7-case manual UI validation plan**.

The application monitors **25 configured GMD equipment items** across four categories (Blowers, DM Water Electrode Cooling, Cooling Tower Water Monitoring, Utility Area Monitoring), with a parallel GT legacy configuration supporting **42 motors across 10 plant areas**. The system is live on **Render** with health-check monitoring, Swagger API documentation, and documented deployment procedures.

**Threshold-based auto-classification for the GMD bulk-entry path** is architecturally prepared but pending approved threshold values from engineering stakeholders.

---

## 2. Project Objectives

| # | Objective | Status |
|---|-----------|--------|
| O1 | Digitize condition monitoring data capture for GMD field equipment | ✅ Complete |
| O2 | Provide a centralized real-time dashboard for equipment health visibility | ✅ Complete |
| O3 | Store readings in a cloud-accessible, auditable datastore (Google Sheets) | ✅ Complete |
| O4 | Classify equipment status as Normal, Warning, or Alarm based on operating limits | ⚠️ GT legacy path complete; GMD path pending approved thresholds |
| O5 | Enable maintenance teams to acknowledge and track active alarms | ✅ Complete |
| O6 | Aggregate multi-parameter readings into a single equipment health status | ✅ Complete |
| O7 | Support historical reporting and trend analysis | ✅ Complete |
| O8 | Deploy a production-ready, cloud-hosted application | ✅ Complete |
| O9 | Establish QA automation and manual validation for release confidence | ✅ Complete |
| O10 | Design for future predictive maintenance and AI-assisted analysis | 🔜 Architecture prepared |

---

## 3. Problem Statement

### Business context

In glass manufacturing plants, auxiliary systems — blowers, compressors, cooling towers, electrode cooling loops — run continuously. Degradation in **current**, **temperature**, and **vibration** often precedes costly unplanned downtime. Before this project, GMD condition monitoring relied on:

- Manual logbooks and disconnected spreadsheet entries
- No single view of which equipment needed attention
- Delayed visibility for supervisors and reliability engineers
- Inconsistent validation of field readings
- No structured alarm acknowledgement workflow

### Technical gap

Maintenance data existed in silos. There was no unified system to:

1. Validate technician submissions against a canonical equipment registry
2. Compute equipment-level health from multiple parameter readings
3. Surface parameter-level alarms with stable identifiers for acknowledgement
4. Serve a responsive dashboard from a cloud API with persistent storage
5. Verify correctness through automated regression tests before deployment

### Project response

The GMD Condition Monitoring Dashboard addresses these gaps by providing a **config-driven**, **API-first**, **cloud-deployed** monitoring platform with documented QA and deployment readiness processes suitable for industrial operations.

---

## 4. System Architecture

### 4.1 Technology stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 (CRA + Craco), React Router, Axios, Recharts, Tailwind CSS, Phosphor Icons |
| Backend | FastAPI, Uvicorn, Pydantic v2, Python 3.11 |
| Data store | Google Sheets (10-column GMD schema, `Readings` worksheet) |
| Auth / access | Google Service Account (Sheets API) |
| Image storage | Cloudinary (field photo uploads) |
| Deployment | Render Web Service (`condition-monitoring-api`), `render.yaml`, `build.sh` |
| API docs | OpenAPI / Swagger at `/docs` |
| QA automation | pytest, FastAPI TestClient, mocked Sheets dependency |

### 4.2 High-level architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Browser (Desktop / Mobile)                   │
│  React SPA: Dashboard · Bulk Entry · Equipment Monitoring ·      │
│             Reports · Trends & Analytics                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS / REST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Render — FastAPI (server.py + routes)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ /dashboard/*│  │ /gmd/*       │  │ /reports · /trends   │ │
│  │ summary      │  │ bulk entry   │  │ /config/* (GT legacy)  │ │
│  │ active-alarms│  │ validation   │  │ condition-monitoring │ │
│  │ equip-health │  │              │  │                      │ │
│  │ acknowledge  │  │              │  │                      │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
│         │                 │                      │              │
│         └─────────────────┼──────────────────────┘              │
│                           ▼                                      │
│              Aggregation · Caching · Validation                  │
│         (dashboard.py · gmd_config.py · gmd_models.py)          │
└────────────────────────────┬────────────────────────────────────┘
                             │ gspread API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           Google Sheets — Readings tab (append-only)             │
│  Timestamp · Category · Equipment · Parameter · Value · Status │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Application routes (frontend)

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Dashboard | Summary cards, active alarms, area health, recent readings |
| `/add-reading` | Bulk Entry | Category/equipment parameter submission |
| `/equipment-monitoring` | Equipment Monitoring | Per-equipment charts and tables |
| `/reports` | Reports | Filterable readings history |
| `/trends-analytics` | Trends & Analytics | Time-series analysis (7/30/90-day windows) |

### 4.4 Core API endpoints (GMD dashboard)

| Method | Endpoint | Function |
|--------|----------|----------|
| GET | `/dashboard/summary` | Equipment counts: total, ok, warning, alarm |
| GET | `/dashboard/active-alarms` | Unacknowledged WARNING/ALARM parameter rows |
| GET | `/dashboard/equipment-health` | Per-equipment health metrics and history counts |
| GET | `/dashboard/recent-readings` | Latest sheet rows |
| POST | `/dashboard/acknowledge-alarm/{id}` | Acknowledge alarm by stable SHA256-based ID |
| POST | `/gmd/condition-monitoring/bulk` | Submit validated bulk readings to Sheets |
| GET | `/health` | Liveness, Sheets status, dashboard readiness |

### 4.5 Configuration model

| Config file | Scope | Contents |
|-------------|-------|----------|
| `gmd_machine_config.json` | GMD UI (25 equipment) | 4 categories, equipment lists, schema v1.0.0 |
| `machine_config.json` | GT legacy (42 motors) | 10 areas, per-motor threshold limits v3.0.0 |

### 4.6 Equipment status aggregation logic

Implemented in `backend/routes/dashboard.py`:

1. Read all rows from Google Sheets
2. For each **(equipment, parameter)** pair, retain the **newest timestamp** row
3. Compute equipment **worst status** across parameters: `ALARM > WARNING > NORMAL`
4. Select a **representative parameter** (highest severity; tie-break by newest timestamp)
5. Summary counts: `total = 25` (from config); `ok = total − warning − alarm`
6. Active alarms: parameter-level WARNING and ALARM rows with stable 16-char `id`
7. Response caching: 30–60 seconds per endpoint

### 4.7 Data schema (GMD Sheets — 10 columns)

`Timestamp · Category · Equipment · Parameter · Location · Value · Status · Verified By · Remarks · Entry Source`

---

## 5. Industry 4.0 Concepts Applied

| Concept | Application in this project |
|---------|----------------------------|
| **Cyber-physical systems** | Field equipment parameters (vibration, temperature, current) digitized and linked to cloud dashboard |
| **Industrial IoT (IIoT) pattern** | Sensor/readings → API gateway (FastAPI) → cloud datastore (Sheets) → visualization layer (React), mirroring IoT pipeline architecture |
| **Real-time operations dashboard** | Live equipment health, 30-second auto-refresh, active alarm surfacing for immediate operator response |
| **Condition-based maintenance (CBM)** | Status classification (Normal/Warning/Alarm) supports maintenance triggered by equipment condition rather than fixed schedules |
| **Digital twin (foundational)** | Per-equipment health percentage, parameter history counts, and trend charts provide a digital representation of physical asset state |
| **Data-driven decision making** | Reports and trends enable engineers to analyze degradation patterns before failure |
| **Cloud manufacturing** | Render-hosted deployment enables remote access for engineering and management without on-premise infrastructure |
| **Interoperability / open APIs** | REST + OpenAPI documentation allows future integration with PLC, OPC-UA, or MES systems |
| **Quality 4.0 / validation at source** | Pydantic models + `validate_gmd_submission()` enforce data quality at ingestion |
| **Predictive maintenance readiness** | Historical data in Sheets, structured APIs, and planned AI analysis module lay groundwork for ML-based anomaly detection |

---

## 6. Technical Challenges Solved

### 6.1 Multi-parameter equipment status aggregation

**Challenge:** A single piece of equipment (e.g., MCB-1) can have multiple parameters with different severities and timestamps. A naive “latest row wins” approach incorrectly cleared ALARM states when newer NORMAL readings arrived for other parameters.

**Solution:** Implemented per-parameter latest-row tracking, then worst-status aggregation (`ALARM > WARNING > NORMAL`) with representative parameter selection. Regression case TC-AGG-07 validates that an older ALARM on `vertical_vibration` persists when newer NORMAL rows exist for `temperature` and `current`.

### 6.2 Dual monitoring schemas (GMD + GT legacy)

**Challenge:** The codebase evolved to support both a new GMD 10-column Sheets schema (25 equipment) and a legacy GT 22-column schema (42 motors with threshold math).

**Solution:** Separated configuration (`gmd_machine_config.json` vs `machine_config.json`), dedicated route modules (`/dashboard/*` vs `/condition-monitoring/*`), and clear API boundaries so the current React UI uses the GMD path without breaking GT compatibility endpoints.

### 6.3 Alarm acknowledgement with stable identifiers

**Challenge:** Alarms needed dismissible UI cards without deleting underlying sheet data; IDs had to be deterministic for API acknowledgement.

**Solution:** SHA256 hash of `equipment|parameter|timestamp|status` truncated to 16 characters; in-memory acknowledgement set with cache invalidation; frontend guard preventing POST with missing `id`.

### 6.4 Google Sheets as production datastore

**Challenge:** Sheets API latency, rate limits, and lack of transactional queries.

**Solution:** Service-layer caching (45s Sheets TTL, 30–60s dashboard TTL), graceful fallback to stale cache on API errors, append-only writes, and mock-based pytest tests that eliminate live Sheets dependency in CI.

### 6.5 Full-stack deployment on Render

**Challenge:** Single Render web service must serve both React SPA and FastAPI API; client-side routes require server fallback.

**Solution:** `build.sh` pipeline (npm build → copy to `backend/static/`), SPA catch-all routes in `server.py`, `render.yaml` blueprint, `/health` endpoint with `dashboard_ready` flag.

### 6.6 Validation framework (defense in depth)

**Challenge:** Invalid category/equipment names or negative readings could corrupt monitoring data.

**Solution:** Three-layer validation — Pydantic `GMDReadingsRequest`, business rules in `validate_gmd_submission()`, and route-level HTTP 422 error handling against `gmd_machine_config.json`.

### 6.7 QA automation without live infrastructure

**Challenge:** 17 functional test cases depended on Google Sheets data that is slow and non-deterministic in CI.

**Solution:** Phase 1 pytest suite with `MockGMDGoogleSheetsService` and FastAPI `dependency_overrides` — 35 tests passing in ~24 seconds with no live Sheets connection.

---

## 7. QA and Validation Activities

### 7.1 QA program structure

| Artifact | Purpose |
|----------|---------|
| `QA_TEST_EXECUTION_PACKAGE.md` | 23 test cases, step-by-step manual guide, tracker, defect template, closure report, deployment checklist |
| `MANUAL_QA_EXECUTION_PLAN.md` | 7 remaining UI/integration cases after automation |
| `backend/tests/` | Phase 1 pytest automation (35 tests) |

### 7.2 Test coverage summary

| Layer | Cases | Method | Result |
|-------|-------|--------|--------|
| Equipment aggregation | TC-AGG-01 – 07 | pytest unit tests | ✅ Automated |
| Dashboard summary | TC-SUM-01 – 04 | TestClient + mock Sheets | ✅ Automated |
| Active alarms API | TC-ALM-01 – 04 | TestClient + mock Sheets | ✅ Automated |
| Equipment health API | TC-EH-01 – 03 | TestClient + mock Sheets | ✅ Automated |
| Alarm acknowledge API | TC-ACK-01 | TestClient + mock Sheets | ✅ Automated |
| UI alarm cards | TC-ALM-02 – 04 | Manual + screenshots | 📋 Planned |
| UI timestamp display | TC-EH-04 | Manual | 📋 Planned |
| UI ack workflow | TC-ACK-02 – 04 | Manual + DevTools | 📋 Planned |

**Automated:** 35 tests passing · **Manual:** 7 cases (~84 minutes) · **Total functional cases:** 24

### 7.3 Test data strategy

Seven reusable data sets (DATA-SET-A through G) targeting test equipment **MCB-1** (Blowers category), covering NORMAL, WARNING, ALARM, mixed severity, missing parameters, and timestamp regression scenarios.

### 7.4 Validation framework tested

- Pydantic request model validation (required fields, numeric ≥ 0)
- Category/equipment registry validation against `gmd_machine_config.json`
- Aggregation severity ordering and per-parameter latest-row selection
- Alarm ID stability and acknowledgement API contract

---

## 8. Deployment Readiness Activities

| Activity | Deliverable | Status |
|----------|-------------|--------|
| Production release documentation | `PRODUCTION_RELEASE.md` | ✅ |
| Release notes v1.0.0 | `RELEASE_NOTES_v1.0.0.md` | ✅ |
| Render build procedure | `RENDER_BUILD.md`, `render.yaml`, `build.sh` | ✅ |
| Google Sheets setup guide | `GOOGLE_SHEETS_SETUP.md`, `READY_TO_ENABLE_SHEETS.md` | ✅ |
| Environment variable specification | `backend/.env.example` | ✅ |
| Health check endpoint | `GET /health` → `status`, `dashboard_ready`, `sheets_enabled` | ✅ |
| Post-deploy verification script | `backend/scripts/verify_all_machines.py` | ✅ |
| Live production deployment | https://electrical-condition-monitoring-system.onrender.com/ | ✅ |
| QA closure + deployment sign-off templates | Section 7 of QA package | ✅ |
| Swagger API documentation | `/docs` on production | ✅ |

### Deployment checklist highlights

- Run `./build.sh` on deploy (frontend → `backend/static`)
- Configure Render secrets: `GOOGLE_SHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`
- Confirm `dashboard_ready: true` after deploy
- Execute pytest suite (35 passed) before release
- Complete 7-case manual UI smoke for final sign-off

---

## 9. Future Scope

| Priority | Enhancement | Description |
|----------|-------------|-------------|
| **P1** | GMD threshold integration | Apply approved Normal/Warning/Alarm limits on bulk entry; auto-write Status column (currently defaults to NORMAL) |
| **P2** | Phase 2 QA automation | Jest/React Testing Library for TC-ACK-04; Playwright E2E for TC-ACK-02, TC-ALM UI cases |
| **P3** | CI/CD pipeline | GitHub Actions: pytest on every PR, optional Render deploy hook |
| **P4** | Persistent acknowledgement store | Move `_acknowledged_alarm_ids` from in-memory to Sheets or lightweight DB |
| **P5** | PLC / OPC-UA integration | Stream live readings to `/readings` endpoint (architecture noted in `server.py`) |
| **P6** | AI analysis module | Anomaly detection and predictive maintenance recommendations (nav placeholder exists) |
| **P7** | Role-based access | Technician vs engineer vs supervisor permissions |
| **P8** | Email/SMS alerting | Notify supervisors on new ALARM status |
| **P9** | Mobile-optimized field app | PWA or native wrapper for bulk entry with offline queue |
| **P10** | Multi-plant support | Extend `gmd_machine_config.json` for additional plants beyond GT |

---

## 10. Key Achievements

| # | Achievement |
|---|-------------|
| 1 | Delivered and deployed a production cloud dashboard for GMD condition monitoring on Render |
| 2 | Implemented correct multi-parameter equipment status aggregation with ALARM > WARNING > NORMAL precedence |
| 3 | Built alarm acknowledgement workflow end-to-end (API + React UI + stable alarm IDs) |
| 4 | Established config-driven validation for 25 equipment items across 4 categories |
| 5 | Integrated Google Sheets as operational datastore with caching and error resilience |
| 6 | Created full-stack application: 5 React pages, 10+ REST endpoints, OpenAPI docs |
| 7 | Authored comprehensive QA program: 23 test cases, execution guides, closure templates |
| 8 | Implemented Phase 1 QA automation: **35 pytest tests passing** with zero live Sheets dependency |
| 9 | Documented deployment readiness: build pipeline, health checks, environment configuration |
| 10 | Prepared architecture for Industry 4.0 extensions: trends, reports, future AI/PLC integration |

---

## 11. Resume Bullet Points

Use 3–5 of these tailored to the role:

- Developed and deployed a **cloud-based condition monitoring dashboard** (React, FastAPI, Google Sheets) for a glass manufacturing plant, monitoring **25 GMD equipment assets** with real-time health, alarms, and trend analytics — live at `electrical-condition-monitoring-system.onrender.com`

- Engineered **equipment status aggregation logic** that computes worst-case health across multiple parameters (`ALARM > WARNING > NORMAL`) with per-parameter timestamp resolution, preventing false-normal states on industrial monitoring data

- Built **RESTful APIs** (`/dashboard/summary`, `/active-alarms`, `/equipment-health`, `/acknowledge-alarm`) with FastAPI, Pydantic validation, response caching, and OpenAPI documentation

- Implemented **QA automation** with pytest and FastAPI TestClient using dependency-injected mocks — **35 automated tests** covering aggregation, summary, alarms, health, and acknowledgement workflows

- Designed **deployment pipeline** for Render (`build.sh`, `render.yaml`) serving React SPA from FastAPI with health-check monitoring and Google Service Account integration

- Authored **technical documentation and QA execution packages** (23 test cases, manual UI plan, deployment sign-off checklists) supporting internship deliverables and production release approval

- Applied **Industry 4.0 principles** — condition-based maintenance, cloud manufacturing, IIoT-style data pipelines, and digital equipment health scoring — to digitize manual maintenance logging

---

## 12. LinkedIn Project Description

**GMD Condition Monitoring Dashboard | Neutral Glass | Industry 4.0**

Built a full-stack condition monitoring platform for a glass manufacturing plant’s General Maintenance Department — replacing manual logbooks with a live cloud dashboard.

**What I built:**
- React dashboard with real-time equipment health, active alarms, bulk field entry, reports, and trend analytics
- FastAPI backend with Google Sheets integration, Pydantic validation, and config-driven equipment registry (25 assets, 4 categories)
- Equipment status aggregation engine: multi-parameter worst-status logic (ALARM > WARNING > NORMAL) with alarm acknowledgement workflow
- Production deployment on Render with automated build pipeline, health checks, and Swagger API docs

**QA & engineering rigor:**
- 35 automated pytest tests (mocked Sheets, FastAPI TestClient) — zero live infrastructure dependency
- 23-case QA program with manual UI validation plan and deployment sign-off templates

**Stack:** React · FastAPI · Python · Google Sheets API · Pydantic · Render · Recharts · Tailwind CSS · pytest

**Impact:** Enables maintenance technicians and engineers to capture, validate, and visualize equipment condition data (current, temperature, vibration) from any browser — supporting proactive maintenance and future predictive analytics.

🔗 Live: https://electrical-condition-monitoring-system.onrender.com/

---

## 13. Interview Talking Points

### Elevator pitch (30 seconds)

*"I built a production condition monitoring dashboard for a glass plant’s maintenance department. Technicians enter equipment readings through a React app; a FastAPI backend validates the data, stores it in Google Sheets, and aggregates multiple parameters into a single health status. The dashboard shows alarms in real time, supports acknowledgement, and is deployed on Render. I also wrote 35 automated tests and a full QA program for release confidence."*

### Technical depth questions

**Q: How does equipment status aggregation work?**  
A: For each equipment asset, I keep the latest row per parameter from Google Sheets. I then take the worst status across all parameters — ALARM beats WARNING beats NORMAL. The representative parameter is the highest-severity one, with newest timestamp as tie-breaker. This fixed a regression where a newer NORMAL temperature reading incorrectly masked an older ALARM on vibration.

**Q: How did you test without live Google Sheets?**  
A: I created `MockGMDGoogleSheetsService` returning fixture rows and used FastAPI’s `dependency_overrides` to replace `get_sheets_service`. Unit tests call aggregation functions directly; API tests use TestClient. 35 tests run in about 24 seconds.

**Q: Why Google Sheets instead of a database?**  
A: Operational constraint — maintenance teams already use spreadsheets; Sheets provides immediate auditability and zero DBA overhead. I mitigated latency with TTL caching and designed the service layer so swapping to PostgreSQL later would only change the repository implementation.

**Q: What was the hardest bug or challenge?**  
A: The aggregation regression in TC-AGG-07 — equipment looked NORMAL because we were taking the latest row globally instead of per parameter. Fixing it required rethinking the data model to track latest-per-(equipment, parameter) before applying worst-status logic.

**Q: How is acknowledgement implemented?**  
A: Each active alarm gets a stable 16-character ID from SHA256 of equipment, parameter, timestamp, and status. POST to `/dashboard/acknowledge-alarm/{id}` adds it to an in-memory set and invalidates the alarm cache. The React UI re-fetches after ack. Trade-off: resets on server restart — documented as a known limitation with Sheets as source of truth.

**Q: What’s pending / future work?**  
A: Threshold auto-classification on the GMD bulk-entry path — the GT legacy system already has threshold math from `machine_config.json`, but GMD is waiting on approved limit values from engineering. Next steps: enable auto-Status on write, Playwright E2E for UI cases, and CI pipeline.

### Behavioral questions

**Q: How did you ensure quality before deployment?**  
A: Three layers — 35 automated tests for backend logic, a 23-case QA test plan with step-by-step intern guides, and deployment checklists covering health checks, environment variables, and smoke tests. I classified tests by automation feasibility so manual effort focused on UI-only cases.

**Q: How did you document your work?**  
A: Created QA execution packages, manual plans, production release docs, and this internship documentation — so the project is maintainable after the internship ends.

---

## 14. Internship Report Summary

### Introduction

This internship project involved the end-to-end development, validation, and deployment of the **GMD Condition Monitoring Dashboard** for Neutral Glass’s General Maintenance Department. The objective was to digitize equipment condition monitoring — covering parameters such as current, temperature, and vibration — and provide a centralized, cloud-accessible platform for maintenance technicians, engineers, and supervisors.

### Work performed

1. **Requirements and design** — Studied existing manual monitoring workflows; defined equipment registry (25 GMD assets in 4 categories); designed REST API contracts and 10-column Google Sheets schema.

2. **Backend development** — Implemented FastAPI routes for dashboard summary, active alarms, equipment health, alarm acknowledgement, bulk entry, reports, and trends. Built aggregation logic, caching, and Pydantic/config validation.

3. **Frontend development** — Built React pages for dashboard, bulk entry, equipment monitoring, reports, and trends analytics with responsive layout and 30-second auto-refresh.

4. **Integration** — Connected Google Sheets via service account; configured Cloudinary for photo uploads; implemented SPA deployment through `build.sh`.

5. **Enhancement** — Improved equipment status aggregation (worst-status across parameters); implemented alarm acknowledgement workflow with stable IDs.

6. **Quality assurance** — Defined 23 test cases; automated 17 cases as 35 pytest tests; authored manual UI plan for 7 remaining cases; created defect and closure report templates.

7. **Deployment** — Deployed to Render; verified health endpoint; documented environment setup and post-deploy verification procedures.

### Results

- Application is **live in production** and accessible to maintenance teams via browser
- **35 automated tests passing**, providing regression safety for core monitoring logic
- **Documented QA and deployment packages** suitable for manager review and release sign-off
- Architecture supports future threshold integration, PLC streaming, and predictive analytics

### Learning outcomes

- Full-stack development with React and FastAPI in an industrial context
- Designing aggregation logic for multi-sensor equipment health data
- Test-driven QA with pytest, dependency injection, and mock services
- Cloud deployment (Render) with CI-ready build pipelines
- Industry 4.0 concepts: condition-based maintenance, IIoT data pipelines, digital equipment health
- Technical writing for QA plans, release notes, and internship documentation

### Conclusion

The GMD Condition Monitoring Dashboard successfully digitizes a critical maintenance workflow for Neutral Glass. The project demonstrates practical application of Industry 4.0 principles, production-grade software engineering, and structured quality assurance — delivering a deployable system with a clear roadmap for threshold automation, expanded test coverage, and predictive maintenance capabilities.

---

*End of Internship Project Documentation*
