#!/usr/bin/env bash
# One-time setup for .github/workflows/deploy-api.yml.
#
# After this runs, a push to main that passes `ci` deploys the API to Azure App
# Service without anyone touching a laptop. It is safe to re-run: every step
# checks for the thing it is about to create.
#
# What it creates, and why each piece is the narrowest thing that works:
#
#   * an Entra app registration, "sandbox-github-deploy". This is an identity for
#     GitHub Actions, not a human login; it has no password. Its only credential
#     is a trust in tokens minted by GitHub for this repository.
#   * a service principal for it in the subscription.
#   * "Website Contributor" on THIS web app only, not Contributor on the resource
#     group and not on the subscription. A deploy needs to push content and read
#     publish settings for one app; it has no business touching anything else.
#   * a federated credential pinned to a subject. The subject is what stops any
#     other repository, or any branch, from exchanging a token for this identity:
#       repo:Edw1n-F/Sandbox:ref:refs/heads/main
#     A pull request runs `ci` but cannot deploy, because its ref is not main.
#   * three repository *variables* (not secrets). Client id, tenant id and
#     subscription id are not credentials on their own; they only name the
#     identity. Nothing here can be replayed without GitHub's OIDC exchange.
#
# The alternative, a publish profile, is a long-lived key that can push content
# to the app until someone rotates it. It was rejected for that reason.
#
# Usage:
#   az login
#   bash scripts/setup_azure_oidc.sh
#
# Overridable:
#   REPO_SLUG=Edw1n-F/Sandbox APP_NAME=sandbox-api-t1 RESOURCE_GROUP=sandbox-rg
set -euo pipefail

REPO_SLUG="${REPO_SLUG:-Edw1n-F/Sandbox}"
APP_DISPLAY_NAME="${APP_DISPLAY_NAME:-sandbox-github-deploy}"
APP_NAME="${APP_NAME:-sandbox-api-t1}"
RESOURCE_GROUP="${RESOURCE_GROUP:-sandbox-rg}"
BRANCH="${BRANCH:-main}"
FEDERATED_NAME="${FEDERATED_NAME:-github-${BRANCH}}"

say() { printf '\n==> %s\n' "$*"; }

for bin in az gh curl; do
  command -v "$bin" >/dev/null 2>&1 || {
    echo "$bin not found. Install it first." >&2
    exit 1
  }
done

az account show >/dev/null 2>&1 || {
  echo "Not signed in to Azure. Run: az login" >&2
  exit 1
}

gh auth status >/dev/null 2>&1 || {
  echo "Not signed in to GitHub. Run: gh auth login" >&2
  exit 1
}

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
WEBAPP_ID="$(az webapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)"

if [ -z "$WEBAPP_ID" ]; then
  echo "Web app ${APP_NAME} not found in ${RESOURCE_GROUP}. Deploy it once with scripts/deploy_azure.sh first." >&2
  exit 1
fi

say "App registration ${APP_DISPLAY_NAME}"
APP_ID="$(az ad app list --display-name "$APP_DISPLAY_NAME" --query "[0].appId" -o tsv)"
if [ -n "$APP_ID" ]; then
  echo "    already exists: ${APP_ID}"
else
  APP_ID="$(az ad app create \
    --display-name "$APP_DISPLAY_NAME" \
    --sign-in-audience AzureADMyOrg \
    --query appId -o tsv)"
  echo "    created: ${APP_ID}"
fi

say "Service principal"
if az ad sp show --id "$APP_ID" >/dev/null 2>&1; then
  echo "    already exists"
else
  # Directory replication is eventually consistent; an immediate sp create can
  # report "does not exist" for an app that was just made. Retry briefly.
  for attempt in 1 2 3 4 5; do
    if az ad sp create --id "$APP_ID" --output none 2>/dev/null; then
      echo "    created"
      break
    fi
    sleep 5
    [ "$attempt" = "5" ] && { echo "    could not create the service principal" >&2; exit 1; }
  done
fi

say "Role: Website Contributor on ${APP_NAME}"
if az role assignment list --assignee "$APP_ID" --scope "$WEBAPP_ID" --query "[?roleDefinitionName=='Website Contributor'] | length(@)" -o tsv | grep -qx 1; then
  echo "    already assigned"
else
  az role assignment create \
    --assignee "$APP_ID" \
    --role "Website Contributor" \
    --scope "$WEBAPP_ID" \
    --output none
  echo "    assigned"
fi

say "Federated credential: repo:${REPO_SLUG}:ref:refs/heads/${BRANCH}"
CREDENTIAL_JSON="$(mktemp)"
trap 'rm -f "$CREDENTIAL_JSON"' EXIT
cat >"$CREDENTIAL_JSON" <<JSON
{
  "name": "${FEDERATED_NAME}",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:${REPO_SLUG}:ref:refs/heads/${BRANCH}",
  "audiences": ["api://AzureADTokenExchange"]
}
JSON
if az ad app federated-credential list --id "$APP_ID" --query "[?name=='${FEDERATED_NAME}'] | length(@)" -o tsv | grep -qx 1; then
  echo "    already exists"
else
  az ad app federated-credential create \
    --id "$APP_ID" \
    --parameters "$CREDENTIAL_JSON" \
    --output none
  echo "    created"
fi

say "Repository variables on ${REPO_SLUG}"
gh variable set AZURE_CLIENT_ID --repo "$REPO_SLUG" --body "$APP_ID"
gh variable set AZURE_TENANT_ID --repo "$REPO_SLUG" --body "$TENANT_ID"
gh variable set AZURE_SUBSCRIPTION_ID --repo "$REPO_SLUG" --body "$SUBSCRIPTION_ID"

say "Done"
cat <<DONE
The API now deploys itself when \`ci\` passes on ${BRANCH}.

Check it with:
  gh workflow list --repo ${REPO_SLUG}
  gh run watch --repo ${REPO_SLUG}
  curl https://${APP_NAME}.azurewebsites.net/health

Limits of this pipeline, so they are not discovered the hard way:
  * Code only (SKIP_ASSETS=1). Changes under backend/model/ or backend/data/
    still need: bash scripts/deploy_azure.sh
    and even then, startup.sh seeds /home only once, behind a .seeded marker,
    so a committed data change does not replace what is already there.
  * The frontend is a separate deploy. See README, "Deployment".
DONE
