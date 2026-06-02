# Neutral Glass — G Tank Electrical Condition Monitoring

**Version 1.0.0** · Plant **GT** · 10 areas · 42 motors

Electrical condition monitoring for the G Tank: current, temperature, and vibration readings with dashboard, bulk entry, alarms, and Google Sheets logging.



| Item | URL |
|------|-----|
| **Live dashboard** | https://electrical-condition-monitoring-system.onrender.com/ |
| **GitHub repository** | https://github.com/singhharshit2709-ops/electrical-condition-monitoring-system |
| **Latest release commit** | https://github.com/singhharshit2709-ops/electrical-condition-monitoring-system/commit/a594a83 |
| **API documentation (Swagger)** | https://electrical-condition-monitoring-system.onrender.com/docs |
| **Health check** | https://electrical-condition-monitoring-system.onrender.com/health |
| **Google Sheet (Readings)** | https://docs.google.com/spreadsheets/d/1BLjtK2ds_cMN5H13gkfntxL6YcKDZMyXfjlS3X54VgQ/edit |
| **Render service dashboard** | https://dashboard.render.com/ (open service **condition-monitoring-api**) |

Further detail: [PRODUCTION_RELEASE.md](./PRODUCTION_RELEASE.md) · [RELEASE_NOTES_v1.0.0.md](./RELEASE_NOTES_v1.0.0.md) · [RENDER_BUILD.md](./RENDER_BUILD.md)

## Quick links (production)

| Resource | URL |
|----------|-----|
| Dashboard | https://electrical-condition-monitoring-system.onrender.com/ |
| Add readings | https://electrical-condition-monitoring-system.onrender.com/add-readings |
| View data | https://electrical-condition-monitoring-system.onrender.com/view-data |
| API docs | https://electrical-condition-monitoring-system.onrender.com/docs |
| Health | https://electrical-condition-monitoring-system.onrender.com/health |

See [PRODUCTION_RELEASE.md](./PRODUCTION_RELEASE.md) for deployment, architecture, and equipment coverage.

## Local development

```bash
# Terminal 1 — API
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# Terminal 2 — UI (hot reload)
cd frontend
set REACT_APP_BACKEND_URL=http://127.0.0.1:8000
npm install
npm start
```

Or serve UI from the API:

```bash
./build.sh
cd backend && uvicorn server:app --port 8000
# Open http://127.0.0.1:8000/
```

## Production build (Render)

`render.yaml` runs the same steps as `build.sh`. Ensure the Render service uses this blueprint or set **Build Command** to:

```bash
./build.sh
```

After deploy, confirm `GET /health` returns `"dashboard_ready": "True"`.
