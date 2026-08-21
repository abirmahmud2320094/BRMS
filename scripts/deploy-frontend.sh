#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$ROOT/frontend"
EXPECTED_API_URL="https://brms-api-h2qf.onrender.com/api/v1"
PROJECT_ID="builing-rent-management-system"

if [ ! -f "$FRONTEND/.env.local" ]; then
  echo "Missing frontend/.env.local. Configure the production Firebase Web App values first." >&2
  exit 1
fi

if ! grep -Fqx "VITE_API_BASE_URL=$EXPECTED_API_URL" "$FRONTEND/.env.local"; then
  echo "frontend/.env.local must set VITE_API_BASE_URL to the production Render API." >&2
  exit 1
fi

if [ ! -f "$ROOT/firebase.json" ] || [ ! -f "$ROOT/.firebaserc" ]; then
  echo "Firebase Hosting configuration is incomplete at the repository root." >&2
  exit 1
fi

(
  cd "$FRONTEND"
  npm test
  npm run build
)

if [ ! -f "$FRONTEND/dist/index.html" ]; then
  echo "Frontend build did not produce frontend/dist/index.html." >&2
  exit 1
fi

(
  cd "$ROOT"
  npx --yes firebase-tools@15.28.1 deploy --only hosting --project "$PROJECT_ID"
)
