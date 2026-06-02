#!/usr/bin/env bash
# Production build: Python deps + React UI copied into backend/static
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "==> Installing Python dependencies"
pip install -r backend/requirements.txt

echo "==> Building React frontend (npm ci && npm run build)"
cd frontend
npm ci
REACT_APP_BACKEND_URL= npm run build
echo "==> Frontend build output:"
ls -la build/ | head -20

echo "==> Copying UI into backend/static"
rm -rf ../backend/static
mkdir -p ../backend/static
cp -r build/* ../backend/static/

if [[ ! -f ../backend/static/index.html ]]; then
  echo "ERROR: backend/static/index.html missing after build" >&2
  exit 1
fi

echo "==> backend/static contents:"
ls -la ../backend/static/ | head -20
echo "==> Build complete (dashboard ready at /)"
