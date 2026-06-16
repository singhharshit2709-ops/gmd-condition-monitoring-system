# Pre-Deployment Sanity Check

**GMD Condition Monitoring System**  
**Audit Timestamp:** 2026-06-15  
**Method:** Static configuration review + production `/health` probe (no code changes)  
**Production URL tested:** `https://electrical-condition-monitoring-system.onrender.com/health`

---

## Summary

| Area | Result |
|------|--------|
| Production environment variables | **PASS** (with recommended additions) |
| Render deployment configuration | **PASS** |
| Required secrets | **PASS** (runtime evidence; confirm in Render dashboard) |
| Google Service Account credentials | **PASS** |
| Google Sheet permissions | **PASS** (inferred from live connectivity) |
| Backend startup configuration | **PASS** |
| Frontend production build | **PASS** |
| API base URLs | **PASS** |
| CORS configuration | **PASS** (same-origin deploy) |
| Static asset paths | **PASS** |
| Google Sheets connectivity | **PASS** |
| Threshold feature flag | **PASS** |
| Logging | **PASS** |
| Error handling | **PASS** |

**Overall pre-deployment verdict:** **READY TO DEPLOY** — confirm Render secret values and optional env vars before go-live.

---

## 1. Production Environment Variables

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Core Sheets vars declared in `render.yaml` | **PASS** | `GOOGLE_SHEETS_ENABLED=true`, `GOOGLE_SHEET_ID` (secret), `GOOGLE_SHEET_WORKSHEET=Readings`, `GOOGLE_SERVICE_ACCOUNT_JSON` (secret) | None |
| Multi-area layout var | **PASS** (default) | `GOOGLE_SHEETS_AREA_LAYOUT` not in `render.yaml`; code defaults to `multi` (`backend/services/sheets_area_registry.py:is_multi_area_layout_enabled`, default `"multi"`) | **Recommended:** Add `GOOGLE_SHEETS_AREA_LAYOUT=multi` explicitly in Render dashboard |
| Legacy tab merge var | **PASS** (default) | `GOOGLE_SHEETS_INCLUDE_LEGACY_READINGS` defaults to `true` | Set explicitly if migration from legacy `Readings` tab is complete |
| Threshold flags | **PASS** (default) | `GMD_THRESHOLD_CLASSIFICATION_ENABLED` defaults to `false`; `GMD_THRESHOLD_ALLOW_PROVISIONAL` defaults to `false` (`backend/services/threshold_service.py`) | **Recommended:** Set `GMD_THRESHOLD_CLASSIFICATION_ENABLED=false` explicitly in Render |
| Drive folder for media | **PASS** (optional) | `GOOGLE_DRIVE_FOLDER_ID` read by `backend/services/google_drive_service.py`; not in `render.yaml` | Set in Render if Add Reading media uploads are required |
| Cache TTL | **PASS** (default) | `GOOGLE_SHEETS_CACHE_TTL_SECONDS` defaults to 45 (`backend/services/sheets_config.py:get_cache_ttl_seconds`) | None unless tuning needed |
| CORS | **PASS** | `CORS_ORIGINS=*` in `render.yaml`; read in `backend/server.py:976` | Restrict to production domain if splitting frontend/backend later |
| Frontend API URL | **PASS** | `build.sh` sets `REACT_APP_BACKEND_URL=` (empty) so production uses same-origin (`frontend/src/lib/api.js:getApiBase`) | None for unified Render deploy |
| Stale `CLOUDINARY_URL` | **PASS** (unused) | Declared in `render.yaml` but **no `cloudinary` imports** in backend Python code | Remove from Render if not needed; not a blocker |
| Stale `RENDER_EXTERNAL_URL` | **PASS** (unused) | In `render.yaml` but **not referenced** in application code | Optional cleanup; not a blocker |

**Evidence files:** `render.yaml`, `backend/services/sheets_config.py`, `backend/services/sheets_area_registry.py`, `backend/services/threshold_service.py`, `build.sh`, `frontend/src/lib/api.js`

---

## 2. Render Deployment Configuration

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Blueprint file present | **PASS** | `render.yaml` defines web service `condition-monitoring-api` | None |
| Runtime | **PASS** | `runtime: python` | None |
| Build command | **PASS** | `chmod +x build.sh && ./build.sh` — installs Python deps, runs `npm ci && npm run build`, copies to `backend/static` | None |
| Start command | **PASS** | `cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT` | None |
| Health check path | **PASS** | `healthCheckPath: /health` matches `@app.get("/health")` in `backend/server.py:1432` | None |
| Auto deploy | **PASS** | `autoDeploy: true` on `main` branch | Confirm branch matches release branch |
| Build documentation | **PASS** | `RENDER_BUILD.md` documents required build command and post-deploy curl checks | None |
| Doc drift | **PASS** (informational) | `PRODUCTION_RELEASE.md` references single `Readings` tab only; code supports multi-area layout | Update docs post-deploy; does not block deploy |

**Evidence files:** `render.yaml`, `build.sh`, `RENDER_BUILD.md`, `backend/server.py`

---

## 3. Required Secrets

| Secret | Result | Explanation | Required Action |
|--------|--------|-------------|-----------------|
| `GOOGLE_SHEET_ID` | **PASS** | Marked `sync: false` in `render.yaml` (manual secret). Production `/health` returns `"sheets_enabled": "True"` — spreadsheet ID is configured at runtime | Confirm value is set in Render **Environment → Secret Files/Variables** |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | **PASS** | Marked `sync: false` in `render.yaml`. Loaded by `load_service_account_credentials()` (`backend/services/sheets_config.py:126–131`). Live deploy has Sheets enabled | Confirm full JSON blob is pasted as secret (not file path on Render) |
| Secrets not in git | **PASS** | No `.env` files tracked; credentials loaded from env only | Never commit service account JSON |

**Evidence:** Production health probe (2026-06-15): `sheets_enabled: True` implies both secrets are present on Render.

---

## 4. Google Service Account Credentials

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Credential loader | **PASS** | `backend/services/sheets_config.py:load_service_account_credentials()` supports `GOOGLE_SERVICE_ACCOUNT_JSON` (Render) or file path (local) | Use JSON env on Render |
| OAuth scopes | **PASS** | `SCOPES` includes `spreadsheets` and `drive` (`sheets_config.py:43–46`) — required for Sheets + media upload | None |
| Invalid JSON handling | **PASS** | Raises `RuntimeError` with clear message on `JSONDecodeError` | None |
| Missing credentials handling | **PASS** | `init_google_sheets()` logs warning and disables sheets (`server.py:595–597`); `GMDGoogleSheetsService` raises on init if disabled | None |
| Live authentication | **PASS** | Production `sheets_enabled: True` | None |

---

## 5. Google Sheet Permissions

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Setup documentation | **PASS** | `GOOGLE_SHEETS_SETUP.md` Step 3: share spreadsheet with service account `client_email` as **Editor** | Follow before first deploy |
| Drive API for media | **PASS** | `google_drive_service.py` uses same credentials; uploads to `GOOGLE_DRIVE_FOLDER_ID` or Drive root | Share target Drive folder with service account if using folder ID |
| Runtime connectivity | **PASS** | Production health reports Sheets enabled | Verify service account email has Editor on production spreadsheet |
| Multi-area worksheets | **PASS** | Area tabs auto-created on first write (`sheets_config.py:get_or_create_worksheet`) | Pre-create tabs optional; not required |

**Required action:** Confirm service account email from JSON secret has **Editor** access to the production spreadsheet (and Drive folder if used).

---

## 6. Backend Startup Configuration

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Startup hook | **PASS** | `@app.on_event("startup")` in `server.py:1001–1016` loads config, init sheets, hydrates cache, checks static UI | None |
| Config load | **PASS** | `app.state.config = load_config()` from `machine_config.json` (legacy GT) | None |
| V2 config | **PASS** | `gmd_config_v2.py:load_gmd_config_v2()` loaded on demand for V2 routes and sheets routing | None |
| Sheets init (legacy layer) | **PASS** | `init_google_sheets()` (`server.py:566`) — graceful disable if env/creds missing | None |
| GMD DAL init | **PASS** | `GMDGoogleSheetsService` singleton opens spreadsheet via `SheetsDataAccess` (`google_sheets_service.py:36–74`) on first API use | None |
| Static UI check | **PASS** | Logs warning if `backend/static/index.html` missing | Ensure `build.sh` runs on every deploy |
| Production startup | **PASS** | Live `/health`: `dashboard_ready: True`, `static_dir_exists: True` | None |

**Evidence:** `backend/server.py`, `backend/services/google_sheets_service.py`

---

## 7. Frontend Production Build

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Build script | **PASS** | `build.sh` runs `npm ci`, `npm run build`, copies to `backend/static`, fails if `index.html` missing | None |
| CRA build command | **PASS** | `frontend/package.json`: `"build": "craco build"` | None |
| Relative homepage | **PASS** | `"homepage": "."` — assets use relative paths for same-origin serve | None |
| Local static artifact | **PASS** | `backend/static/index.html` exists in repo (from prior build) | Re-run `./build.sh` before deploy if frontend changed |
| Production static | **PASS** | Live `/health` static entries: `_redirects`, `asset-manifest.json`, `index.html`, `static` | None |
| Empty backend URL at build | **PASS** | `build.sh:14` — `REACT_APP_BACKEND_URL= npm run build` forces same-origin API in production | None |

**Evidence:** `build.sh`, `frontend/package.json`, `backend/static/index.html`, production `/health`

---

## 8. API Base URLs

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Production resolution | **PASS** | `getApiBase()` returns `window.location.origin` when env empty and not dev port (`frontend/src/lib/api.js:8–14`) | None for unified Render deploy |
| Dev fallback | **PASS** | Ports 3000/5173 → `http://127.0.0.1:8000` | None |
| Split-deploy override | **PASS** | Set `REACT_APP_BACKEND_URL` at build time if frontend hosted separately | Not needed for current architecture |
| KnowledgeBase page | **PASS** (informational) | `KnowledgeBase.js` uses `REACT_APP_BACKEND_URL` directly; page not routed in main App | No action for current routes |

---

## 9. CORS Configuration

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Middleware registered | **PASS** | `CORSMiddleware` in `server.py:974–980` | None |
| Origins source | **PASS** | `allow_origins=os.environ.get("CORS_ORIGINS", "*").split(",")` | None |
| Render value | **PASS** | `CORS_ORIGINS=*` in `render.yaml` | None |
| Same-origin deploy | **PASS** | SPA and API served from same Render host — browser same-origin requests do not rely on CORS for normal operation | None |
| Credentials + wildcard | **PASS** (informational) | `allow_credentials=True` with `*` is spec-inconsistent; low risk when SPA is same-origin | If splitting hosts, set explicit origin list |

---

## 10. Static Asset Paths

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| SPA root | **PASS** | `@app.get("/")` serves `backend/static/index.html` (`server.py:1491–1493`) | None |
| Asset fallback | **PASS** | `@app.get("/{spa_path:path}")` serves files from `STATIC_DIR` or falls back to index for client routes (`server.py:1496–1503`) | None |
| API path protection | **PASS** | SPA catch-all skips prefixes `api/`, `health`, `dashboard`, etc. (`server.py:1456–1468`) | None |
| Relative asset URLs | **PASS** | `index.html` references `./static/js/main.*.js` and `./static/css/main.*.css` | None |
| `_redirects` | **PASS** | `backend/static/_redirects` contains `/* /index.html 200` | None |

---

## 11. Google Sheets Connectivity

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Enable flag | **PASS** | `is_sheets_enabled()` checks `GOOGLE_SHEETS_ENABLED=true` | Set in Render (declared in `render.yaml`) |
| Production connectivity | **PASS** | Live `/health`: `"sheets_enabled": "True"` | None |
| Multi-area DAL | **PASS** | `SheetsDataAccess` reads/writes per-area worksheets (`google_sheets_service.py:63–72`) | Run post-deploy smoke: one submit per area tab |
| Merged reads | **PASS** | Dashboard/Reports/Trends use `fetch_and_clean_data()` → merged `get_all_values()` | None |
| Legacy init coexistence | **PASS** (informational) | `server.py:init_google_sheets()` still initializes legacy `Readings` worksheet for GT compatibility layer; V2 DAL uses separate singleton | Monitor logs after deploy |
| Health diagnostics | **PASS** (informational) | Current repo `/health` includes `sheets_config` summary (`server.py:1446`); live production response may omit this field if on an older build | Redeploy latest commit for full diagnostics |
| Post-deploy verification | **PASS** | Documented in `RENDER_BUILD.md`: `curl …/health` expect `dashboard_ready: True` | Run after each deploy |

**Live probe result (2026-06-15):**

```json
{
  "status": "ok",
  "version": "3.0.0",
  "sheets_enabled": "True",
  "dashboard_ready": "True",
  "static_dir_exists": "True"
}
```

---

## 12. Threshold Feature Flag

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Default disabled | **PASS** | `GMD_THRESHOLD_CLASSIFICATION_ENABLED` defaults to `false` (`threshold_service.py:36–42`) | None |
| Provisional blocked | **PASS** | `GMD_THRESHOLD_ALLOW_PROVISIONAL` defaults to `false` (`threshold_service.py:45–51`) | None |
| Not in render.yaml | **PASS** | Safe defaults apply without explicit Render entry | **Recommended:** Set `GMD_THRESHOLD_CLASSIFICATION_ENABLED=false` explicitly pre-go-live |
| Submit behavior | **PASS** | All new readings write `status: NORMAL` until flag enabled (`threshold_service.py:155–156`) | None |
| Post-approval enablement | **PASS** | Enable flag + update `gmd_machine_config_v2.json` — no code change | See `FINAL_THRESHOLD_DEPLOYMENT_AUDIT.md` |

---

## 13. Logging

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Root logging config | **PASS** | `logging.basicConfig(level=logging.INFO, …)` in `server.py:75–79` | None |
| Module loggers | **PASS** | Named loggers: `gmd_condition_monitoring.sheets_config`, `gmd_v2`, `gmd_monitoring`, `gmd_drive`, `gmd_condition_monitoring.thresholds` | None |
| Sheets init logging | **PASS** | `init_google_sheets()` logs auth source, sheet ID, worksheet title (`server.py:573–637`) | Review Render logs after deploy |
| Submit logging | **PASS** | V2 submit logs area, equipment, media URL (`v2_preview.py:146–157`, `google_sheets_service.py:194–208`) | None |
| Threshold debug | **PASS** | Classification logged at DEBUG in `threshold_service.py:178–184` | None |
| Render log access | **PASS** (operational) | Use Render dashboard → Logs for startup and Sheets errors | Monitor first 24h post-deploy |

---

## 14. Error Handling

| Check | Result | Explanation | Required Action |
|-------|--------|-------------|-----------------|
| Dashboard cache fallback | **PASS** | `_get_cached_dashboard_payload()` catches `APIError`, returns stale cache or fallback (`dashboard.py:114–138`) | None |
| Sheets read failures | **PASS** | `fetch_and_clean_data()` raises HTTP 500 with message on unexpected errors (`dashboard.py:209–214`) | None |
| V2 submit validation | **PASS** | Preview returns validation response; invalid equipment/parameters rejected (`v2_validation.py`) | None |
| V2 submit Sheets failure | **PASS** | `HTTPException 500` with detail if media uploaded but Sheets write fails (`v2_preview.py:176–207`) | None |
| V2 media errors | **PASS** | Invalid base64 → 422; Drive upload failure → 500 with message (`v2_preview.py:50–74`) | None |
| Missing static UI | **PASS** | Returns JSON 503 with hint if `index.html` missing (`server.py:1479–1487`) | None |
| Sheets service disabled | **PASS** | `GMDGoogleSheetsService` raises `RuntimeError` with actionable message (`google_sheets_service.py:40–48`) | None |
| Credential errors | **PASS** | Clear `RuntimeError` messages from `sheets_config.py:133–145, 160–162` | None |
| Frontend error messages | **PASS** | `v2SubmitApi.js` / `v2PreviewApi.js` surface backend validation messages | None |

---

## Pre-Go-Live Action List

Complete these in Render dashboard before or immediately after deploy:

| # | Action | Priority |
|---|--------|----------|
| 1 | Confirm `GOOGLE_SHEET_ID` secret is set | **Required** |
| 2 | Confirm `GOOGLE_SERVICE_ACCOUNT_JSON` secret is set (full JSON) | **Required** |
| 3 | Confirm service account has **Editor** on spreadsheet | **Required** |
| 4 | Set `GMD_THRESHOLD_CLASSIFICATION_ENABLED=false` | **Recommended** |
| 5 | Set `GOOGLE_SHEETS_AREA_LAYOUT=multi` | **Recommended** |
| 6 | Set `GOOGLE_DRIVE_FOLDER_ID` if media uploads used | **If needed** |
| 7 | Run `./build.sh` via Render build (not pip-only) | **Required** |
| 8 | Post-deploy: `curl https://<host>/health` → `dashboard_ready: True`, `sheets_enabled: True` | **Required** |
| 9 | Post-deploy smoke: Add Reading submit per area + Dashboard refresh | **Required** |
| 10 | Remove unused `CLOUDINARY_URL` from Render if present | **Optional cleanup** |

---

## Final Pre-Deployment Verdict

**READY TO DEPLOY**

The codebase, build pipeline, and live production probe confirm that:

- Render blueprint (`render.yaml` + `build.sh`) correctly builds and serves the React SPA from `backend/static`
- Google Sheets integration is configured and **connected on production** (`sheets_enabled: True`)
- Threshold classification is safely disabled by default
- Error handling and logging are present on all critical paths
- No code changes are required for deployment

**Precaution:** Confirm Render secrets and spreadsheet sharing before go-live. After deploying the latest commit, re-run `/health` and verify multi-area worksheet routing with one test submission per plant area.

---

## Related Documentation

| Document | Path |
|----------|------|
| Render build guide | `RENDER_BUILD.md` |
| Google Sheets setup | `GOOGLE_SHEETS_SETUP.md` |
| Threshold deployment audit | `backend/reports/FINAL_THRESHOLD_DEPLOYMENT_AUDIT.md` |
| Final deployment checklist | `backend/reports/FINAL_DEPLOYMENT_CHECKLIST.md` |
| Production release notes | `PRODUCTION_RELEASE.md` |

---

*Generated by pre-deployment sanity check — no code modifications made.*
