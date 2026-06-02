# Release Notes — v1.0.0

**Product:** Neutral Glass — G Tank Electrical Condition Monitoring  
**Release date:** May 2026  
**Production commit:** `a594a83`  
**API schema:** `machine_config.json` v3.0.0  

## Summary

First production release of the G Tank ECM system: hosted dashboard on Render, FastAPI backend, Google Sheets audit log, bulk field entry, and real-time alarm/warning classification for 10 areas and 42 motors (plant GT).

## Features

- **Dashboard** — area health, active alarms, recent readings (5s refresh)
- **Bulk entry** — all motors per area in one submission
- **View data** — per-area monitoring and charts
- **Alarms & warnings** — three-zone thresholds (current, temperature, vibration)
- **Google Sheets** — append-only `Readings` tab
- **Strict bulk API** — rejects partial or mismatched equipment names
- **Config-driven** — all limits in `machine_config.json` (no hardcoded thresholds)

## Equipment

10 areas, 42 motors: G1 Lehr, G2 Lehr, G3 Lehr, Furnace Cooling Blower, Mold Cooling Blower, Combustion Blower, Block Air Fan, Injector Blower, Electrode Cooling Blower, Electrode Water Pump.

## Deployment

- **Host:** Render (`condition-monitoring-api`)
- **UI:** React build in `backend/static/`
- **Build:** `./build.sh` (see `render.yaml`, `RENDER_BUILD.md`)

## Key commits

| SHA | Description |
|-----|-------------|
| `cedee1b` | G Tank migration (GT plant, vibration) |
| `e15df47` | Bulk/Sheets fixes, `gtConfig.js` |
| `ba91e3f` | FastAPI SPA route fix |
| `a28b27c` | Production release (build.sh, strict bulk) |
| `a594a83` | Hosted dashboard on Render |

## Known limitations (v1.0.0)

- Readings cache is in-memory (resets on service restart; Sheets is source of truth)
- AI Analysis nav item has no dedicated page route
- Render free tier may sleep after inactivity (cold start delay)
- UI static files are committed until Render `build.sh` is synced in dashboard

## Upgrade path

Set Render **Build Command** to `chmod +x build.sh && ./build.sh` for UI rebuilds without committing `backend/static/`.
