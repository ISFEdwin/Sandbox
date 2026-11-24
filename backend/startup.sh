#!/usr/bin/env bash
# Startup command for Azure App Service (Linux, Python).
#
# Three App Service behaviours this file exists to handle, each learned the hard
# way on this deployment:
#
#   1. With build automation on, the code is extracted to /tmp (APP_PATH) and
#      served from there, NOT from /home/site/wwwroot. /tmp is ephemeral, so
#      DATA_DIR and MODEL_DIR are pinned to /home, which is the persistent
#      volume (10 GB on Basic).
#   2. Oryx installs dependencies into `antenv` and only activates it for the
#      default startup path. A custom startup command inherits a bare PATH, so
#      `uvicorn` is "command not found" (exit 127) unless the venv is sourced
#      explicitly.
#   3. `app/main.py` mounts /static/model only if the directory exists at import
#      time. Both directories are therefore created BEFORE uvicorn starts; the
#      476 MB tile copy runs afterwards in the background so it cannot blow the
#      startup probe's budget.
#
# The copy is guarded by a marker so a restart does not re-copy 476 MB, and so
# a redeploy still restores committed content that the app has not written over.
set -euo pipefail

APP_DIR="${APP_PATH:-/home/site/wwwroot}"
HOST="${WEBSITE_HOSTNAME:-localhost:8000}"

export DATA_DIR="${DATA_DIR:-/home/data}"
export MODEL_DIR="${MODEL_DIR:-/home/model}"
export STATIC_BASE_URL="${STATIC_BASE_URL:-https://${HOST}/static}"
export PYTHONPATH="$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"

# `uvicorn app.main:app` imports `app` from the working directory.
cd "$APP_DIR"

for venv in "$APP_DIR/antenv" "/home/site/wwwroot/antenv"; do
  if [ -f "$venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    . "$venv/bin/activate"
    break
  fi
done

mkdir -p "$DATA_DIR" "$MODEL_DIR"

# A runtime LLM override (saved from the config panel to data/llm_config.json)
# outranks the environment baseline and carries the operator's own vendor key.
# This deployment is meant to run the keyless deterministic fallback, so the file
# is removed unless ALLOW_LLM_OVERRIDES=1 says otherwise -- including the copy a
# previous deploy may have seeded into /home.
if [ "${ALLOW_LLM_OVERRIDES:-0}" != "1" ] && [ -f "$DATA_DIR/llm_config.json" ]; then
  echo "sandbox-api: removing seeded LLM override ($DATA_DIR/llm_config.json)"
  rm -f "$DATA_DIR/llm_config.json"
fi

seed() {
  local src="$APP_DIR/$1" dst="$2" marker="$2/.seeded"
  [ -d "$src" ] || return 0
  # Already seeded: skip. `-n` anyway, so a redeploy never overwrites a run
  # the demo just produced.
  [ -f "$marker" ] && return 0
  echo "sandbox-api: seeding ${dst}"
  cp -an "$src/." "$dst/" 2>/dev/null || true
  touch "$marker"
}

# The 12 MB data store is cheap and the API is useless without it.
seed data "$DATA_DIR"

# The tile store is ~476 MB. Run it detached: uvicorn must bind and answer the
# startup probe first, and /static/model serves files as they appear.
( seed model "$MODEL_DIR" ) &

echo "sandbox-api: data=${DATA_DIR} model=${MODEL_DIR} static=${STATIC_BASE_URL}"

# One worker: the file store has no cross-process locking, and the demo's
# in-process caches assume a single writer.
exec python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers 1 \
  --proxy-headers \
  --forwarded-allow-ips '*'
