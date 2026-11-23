#!/usr/bin/env bash
# Startup command for Azure App Service (Linux, Python).
#
# Two App Service behaviours this file exists to handle:
#
#   1. With build automation on, the deployed code is served from /tmp, NOT
#      /home/site/wwwroot. /tmp is ephemeral, so DATA_DIR left at its default
#      would send every generated overlay to a directory that disappears on the
#      next restart. DATA_DIR and MODEL_DIR therefore point at /home, which is
#      the persistent volume (10 GB on the Basic plan).
#   2. The frontend is served from Vercel, a different origin. A relative
#      STATIC_BASE_URL would resolve against the Vercel domain and 404 every
#      overlay, terrain raster and 3D tile, so the absolute origin is derived
#      from WEBSITE_HOSTNAME, which App Service sets to the app's hostname.
#
# Seed copies are additive (`cp -n`): committed content is restored on deploy,
# and anything the app wrote at runtime (runs, comparisons, storm frames) is
# left alone.
set -euo pipefail

APP_DIR="${APP_PATH:-/home/site/wwwroot}"
HOST="${WEBSITE_HOSTNAME:-localhost:8000}"

# `uvicorn app.main:app` imports `app` from the working directory. App Service
# normally starts here already, but `az webapp ssh` and the log stream do not,
# and the failure ("No module named 'app'") reads like a broken build.
cd "$APP_DIR"

export DATA_DIR="${DATA_DIR:-/home/data}"
export MODEL_DIR="${MODEL_DIR:-/home/model}"
export STATIC_BASE_URL="${STATIC_BASE_URL:-https://${HOST}/static}"

seed() {
  local src="$APP_DIR/$1" dst="$2"
  [ -d "$src" ] || return 0
  mkdir -p "$dst"
  # `-n` never overwrites, `-a` keeps mtimes so a second boot is cheap.
  cp -an "$src/." "$dst/" 2>/dev/null || true
}

seed data "$DATA_DIR"
seed model "$MODEL_DIR"

echo "sandbox-api: data=${DATA_DIR} model=${MODEL_DIR} static=${STATIC_BASE_URL}"

# One worker: the file store has no cross-process locking, and the demo's
# in-process caches assume a single writer.
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers 1 \
  --proxy-headers \
  --forwarded-allow-ips '*'
