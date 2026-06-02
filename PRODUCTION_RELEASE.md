# G Tank Electrical Condition Monitoring — Production Release

**Plant:** GT (Neutral Glass G Tank)  
**API version:** 3.0.0  
**Repository:** https://github.com/singhharshit2709-ops/electrical-condition-monitoring-system

---

## Deployment summary

| Component | Technology | Host |
|-----------|------------|------|
| Frontend | React (CRA + Craco) | Served from `backend/static` on Render |
| Backend | FastAPI + Uvicorn | Render Web Service `condition-monitoring-api` |
| Persistence | Google Sheets (`Readings` tab) + in-memory cache | Google Cloud |
| Config | `backend/machine_config.json` v3.0.0 | Git |

**Build:** `./build.sh` or `render.yaml` `buildCommand` (installs Python deps, `npm ci`, `npm run build`, copies `frontend/build` → `backend/static`).

**Start:** `cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT`

**Required env (Render):**

- `GOOGLE_SHEETS_ENABLED=true`
- `GOOGLE_SHEET_ID` — spreadsheet ID (set in Render dashboard)
- `GOOGLE_SERVICE_ACCOUNT_JSON` — service account JSON (secret)
- `GOOGLE_SHEET_WORKSHEET=Readings` (optional)

---

## Architecture summary

```
[Browser]
    |  HTTPS
    v
[Render: FastAPI]
    |-- /, /add-readings, /view-data  --> React SPA (static)
    |-- /docs, /config/*, /condition-monitoring/*  --> API
    |-- readings_cache (latest per motor)
    v
[Google Sheets: Readings tab]  append-only rows
```

- **Bulk Entry:** `POST /condition-monitoring/bulk` — strict validation; all motors must match `machine_config.json`.
- **Dashboard:** polls `/machine-health/GT`, `/active-alarms`, `/condition-monitoring/recent`.
- **Alarms:** threshold classification Normal / Warning / Alarm from config limits.

---

## Equipment coverage (GT)

| Area | Equipment count | Motors |
|------|-----------------|--------|
| G1 Lehr | 8 | Lehr Fan 1–6, Lehr Belt, Cleaning Conveyor |
| G2 Lehr | 8 | same as G1 Lehr |
| G3 Lehr | 8 | same as G1 Lehr |
| Furnace Cooling Blower | 2 | Drive, Star Delta |
| Mold Cooling Blower | 3 | MCB1, MCB2, MCB3 |
| Combustion Blower | 3 | CB1, CB2, CB3 |
| Block Air Fan | 3 | BAF1, BAF2, BAF3 |
| Injector Blower | 3 | IB1, IB2, IB3 |
| Electrode Cooling Blower | 1 | ECB1 |
| Electrode Water Pump | 3 | EWP1, EWP2, EWP3 |
| **Total** | **42** | |

---

## Verification

```bash
# All areas (local or production)
python backend/scripts/verify_all_machines.py --base-url https://electrical-condition-monitoring-system.onrender.com

# Health (dashboard_ready should be "True" after deploy)
curl https://electrical-condition-monitoring-system.onrender.com/health
```

---

## Manager handover (summary)

**Implemented:** G Tank ECM for plant GT — current, temperature, vibration monitoring; bulk field entry; live dashboard; Google Sheets audit log; strict bulk API to prevent partial saves.

**Tested:** All 10 areas / 42 motors via `verify_all_machines.py`; Furnace Drive + Star Delta; alarm thresholds; Sheets enabled on production.

**Verified:** API `/health`, `/docs`, `/config/plants`; bulk insert counts; config name resolution (`config_resolve.py`).

**Production readiness:** Ready after Render deploy runs `build.sh` / `render.yaml` build and `dashboard_ready` is `True` on `/health`.
