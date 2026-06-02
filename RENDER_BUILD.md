# Render build configuration

## Required build command

The web service **must** run the root `build.sh` script (not `pip install` alone):

```bash
chmod +x build.sh && ./build.sh
```

This runs `npm ci`, `npm run build`, and copies `frontend/build/*` → `backend/static/`.

## Blueprint sync

If `render.yaml` changes do not apply automatically:

1. Open [Render Dashboard](https://dashboard.render.com/)
2. **Blueprints** → sync repo blueprint, **or**
3. **condition-monitoring-api** → **Settings** → set **Build Command** to the line above
4. **Manual Deploy** → Deploy latest commit

## Verify after deploy

```bash
curl https://electrical-condition-monitoring-system.onrender.com/health
```

Expect `"dashboard_ready": "True"` and `static_entries` including `index.html`.

```bash
curl -I https://electrical-condition-monitoring-system.onrender.com/
```

Expect `HTTP/1.1 200` and `Content-Type: text/html`.
