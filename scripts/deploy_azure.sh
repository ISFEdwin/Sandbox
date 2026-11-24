#!/usr/bin/env bash
# Deploy the FastAPI backend to Azure App Service (Linux, Python).
#
# Why App Service and not Vercel Functions: the zip payload is ~490 MB (476 MB
# of 3D tiles + data + deps), far over Vercel's 250 MB function limit, and the
# file store needs a writable disk between requests.
#
# What this script does, in order, and is safe to re-run:
#   1. creates the resource group and a Linux App Service plan (B1 by default;
#      the Free tier has 1 GB of storage and 60 CPU-minutes a day, which the
#      tiles alone would consume)
#   2. creates the web app with Python 3.13 and points the startup command at
#      backend/startup.sh
#   3. sets the app settings the app reads (everything secret stays out of git)
#   4. zips backend/ WITHOUT .env and the virtualenvs, then deploy-zips it
#
# Usage:
#   bash scripts/deploy_azure.sh                 # full deploy, assets included
#   SKIP_ASSETS=1 bash scripts/deploy_azure.sh   # code-only redeploy
#   DRY_RUN=1 bash scripts/deploy_azure.sh       # build the zip, touch nothing
#
# Prerequisites:
#   brew install azure-cli   # then: az login
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="${APP_NAME:-sandbox-api-t1}"
RESOURCE_GROUP="${RESOURCE_GROUP:-sandbox-rg}"
PLAN_NAME="${PLAN_NAME:-sandbox-plan}"
# Azure for Students applies a "Allowed resource deployment regions" policy to
# the whole subscription: only italynorth, francecentral, belgiumcentral,
# germanywestcentral and southafricanorth are permitted at all. On top of that,
# App Service quota is zero in most of them -- francecentral,
# germanywestcentral and the others report "Current Limit (B1 App Service
# instances): 0" -- so italynorth is the one that actually provisions.
LOCATION="${LOCATION:-italynorth}"
SKU="${SKU:-B1}"
PYTHON_VERSION="${PYTHON_VERSION:-3.13}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-https://sandbox-azure-five.vercel.app}"
SKIP_ASSETS="${SKIP_ASSETS:-0}"
DRY_RUN="${DRY_RUN:-0}"

ZIP="/tmp/${APP_NAME}.zip"

say() { printf '\n==> %s\n' "$*"; }

if [ "$DRY_RUN" != "1" ] && ! command -v az >/dev/null 2>&1; then
  echo "az not found. Install it with: brew install azure-cli" >&2
  exit 1
fi

# --------------------------------------------------------------------------- #
# Package
# --------------------------------------------------------------------------- #
say "Packaging backend/ -> ${ZIP}"

rm -f "$ZIP"

# Excluded, with reasons:
#   .env        holds a real LLM key. The deployment must not inherit it: the
#               public demo runs the keyless deterministic fallback on purpose.
#   .venv*      local interpreters, 250 MB each, wrong platform.
#   tests/      not imported at runtime.
#   data/*.log  runtime noise. The data/ store itself IS shipped below.
# `zip -x` matches names, not directory trees: ".venv" excludes a file called
# .venv, while ".venv/*" excludes its contents. Both forms are listed because a
# nested __pycache__ needs the second one.
EXCLUDES=(
  ".env"
  # Runtime UI override persisted to the data store. It holds the operator's own
  # vendor key, is gitignored, and must never travel in a deploy payload: the
  # public demo is meant to run the keyless deterministic fallback.
  "data/llm_config.json"
  ".venv/*"
  "*/.venv/*"
  ".venv313/*"
  "*/.venv313/*"
  "*/__pycache__/*"
  "*.pyc"
  ".pytest_cache/*"
  "*/.pytest_cache/*"
  # tests/ is excluded, scripts/ is NOT: the API imports scripts as top-level
  # modules (`from _overlay_common import ...`, `from make_wetgrid import ...`
  # in app/services/run_service.py) by putting that directory on sys.path. An
  # earlier exclusion of scripts/* failed at startup with
  # ModuleNotFoundError: No module named '_overlay_common'.
  "tests/*"
  "*.log"
)

if [ "$SKIP_ASSETS" = "1" ]; then
  # A second deploy only needs code: /home/model and /home/data persist and the
  # startup script seeds additively, so the 476 MB never re-uploads.
  EXCLUDES+=("model/*" "data/*")
fi

ZIP_ARGS=()
for pattern in "${EXCLUDES[@]}"; do
  ZIP_ARGS+=(-x "$pattern")
done

(cd "$REPO/backend" && zip -q -r "$ZIP" . "${ZIP_ARGS[@]}")

say "Payload: $(du -h "$ZIP" | cut -f1) ($(unzip -l "$ZIP" | tail -1 | awk '{print $2}') files)"

# `unzip -l | grep -q` is unsafe here: -q exits at the first match, unzip takes
# SIGPIPE, and `set -o pipefail` then reports the whole pipeline as failed even
# though the pattern matched. A here-string reads the listing once instead.
LISTING="$(unzip -l "$ZIP")"

if grep -qE '(^|/)\.env$|data/llm_config\.json$' <<<"$LISTING"; then
  echo "Refusing to deploy: .env or data/llm_config.json is in the zip (credentials)." >&2
  exit 1
fi

# The API imports several top-level modules out of scripts/ at startup, so a
# packaging rule that drops that directory produces a container that dies with
# ModuleNotFoundError before uvicorn binds. Check the few that matter instead of
# discovering it from a failed cold start.
for required in "app/main.py" "scripts/_overlay_common.py" "scripts/make_wetgrid.py"; do
  if ! grep -qE "[[:space:]]${required}$" <<<"$LISTING"; then
    echo "Refusing to deploy: ${required} is missing from the zip." >&2
    exit 1
  fi
done

if [ "$DRY_RUN" = "1" ]; then
  say "DRY_RUN=1: stopping before any Azure call."
  exit 0
fi

# --------------------------------------------------------------------------- #
# Infrastructure
# --------------------------------------------------------------------------- #
say "Resource group ${RESOURCE_GROUP}"
if [ "$(az group exists --name "$RESOURCE_GROUP")" = "true" ]; then
  # A resource group's own location is fixed at creation and is only metadata
  # about where its records live; the resources inside can be in any permitted
  # region. Re-creating it with a different --location is an error, so an
  # existing one is reused rather than fought with.
  echo "    already exists, reusing it"
else
  az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
fi

say "App Service plan ${PLAN_NAME} (${SKU}, Linux, ${LOCATION})"
if az appservice plan show --name "$PLAN_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  echo "    already exists, reusing it"
else
  az appservice plan create \
    --name "$PLAN_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --is-linux \
    --sku "$SKU" \
    --output none
fi

say "Web app ${APP_NAME} (Python ${PYTHON_VERSION})"
if az webapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  echo "    already exists, updating in place"
else
  az webapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --plan "$PLAN_NAME" \
    --runtime "PYTHON:${PYTHON_VERSION}" \
    --output none
fi

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
# DATA_DIR and MODEL_DIR point at /home, not at the deployed content: with build
# automation the code is served from /tmp, which is wiped on every restart.
# CORS_ORIGINS is a JSON array because pydantic-settings parses list fields as
# JSON. It cannot be "*" -- the app sends credentials, and browsers reject a
# wildcard with credentialed CORS.
say "App settings"
az webapp config appsettings set \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    PYTHON_VERSION="$PYTHON_VERSION" \
    PYTHONUNBUFFERED=1 \
    STORE_MODE=file \
    DATA_DIR=/home/data \
    MODEL_DIR=/home/model \
    CORS_ORIGINS="[\"${FRONTEND_ORIGIN}\"]" \
    ANTHROPIC_API_KEY= \
    LLM_BASE_URL= \
    LLM_API_KEY= \
  --output none

say "Startup command"
az webapp config set \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --startup-file "bash startup.sh" \
  --always-on true \
  --min-tls-version 1.2 \
  --output none

# --------------------------------------------------------------------------- #
# Deploy
# --------------------------------------------------------------------------- #
say "Deploying ${ZIP} (Oryx builds the dependencies server-side)"
az webapp deployment source config-zip \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --src "$ZIP" \
  --timeout 1800 \
  --output none

HOST="$(az webapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query defaultHostName -o tsv)"
API="https://${HOST}"

say "Waiting for ${API}/health"
for attempt in $(seq 1 40); do
  if curl -fsS --max-time 10 "${API}/health" >/tmp/health.json 2>/dev/null; then
    cat /tmp/health.json; echo
    say "Live: ${API}"
    say "Point the frontend at it with: vercel env add VITE_API_BASE_URL production"
    exit 0
  fi
  sleep 15
done

echo "Health still failing after 10 minutes." >&2
echo "Next: az webapp log tail -n ${APP_NAME} -g ${RESOURCE_GROUP}" >&2
exit 1
