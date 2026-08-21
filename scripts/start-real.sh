#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
BACK_PID=""
FRONT_PID=""

cleanup() {
  trap - EXIT INT TERM
  if [ -n "$FRONT_PID" ]; then kill "$FRONT_PID" 2>/dev/null || true; fi
  if [ -n "$BACK_PID" ]; then kill "$BACK_PID" 2>/dev/null || true; fi
  wait 2>/dev/null || true
}

require_free_port() {
  local port="$1" name="$2"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "$name cannot start because port $port is already in use." >&2
    exit 1
  fi
}

wait_for_service() {
  local url="$1" pid="$2" name="$3" attempts=0
  while [ "$attempts" -lt 75 ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "$name stopped before it became ready." >&2
      wait "$pid" || true
      return 1
    fi
    if curl --silent --fail "$url" >/dev/null; then return 0; fi
    attempts=$((attempts + 1))
    sleep 0.2
  done
  echo "$name did not become ready at $url." >&2
  return 1
}

trap cleanup EXIT INT TERM

if [ ! -f "$BACKEND/.env" ]; then
  echo "Missing backend/.env. Copy backend/.env.example and configure Firebase Admin credentials." >&2
  exit 1
fi
if [ ! -x "$BACKEND/.venv/bin/python" ]; then
  echo "Missing backend Python environment. Create backend/.venv and run pip install -r backend/requirements.txt." >&2
  exit 1
fi
if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "Missing frontend dependencies. Run npm install in frontend/." >&2
  exit 1
fi
if [ ! -f "$FRONTEND/.env.local" ]; then
  echo "Missing frontend/.env.local. Copy frontend/.env.example and add the Firebase Web App configuration." >&2
  exit 1
fi

export AUTH_MODE="firebase"
export DATA_MODE="firebase"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173}"

(cd "$BACKEND" && "$BACKEND/.venv/bin/python" - <<'PY'
from pathlib import Path
from dotenv import dotenv_values

from app.core.config import get_settings
from app.core.firebase import get_firebase_app
from app.services.store import get_store

settings = get_settings()
if settings.auth_mode != "firebase" or settings.data_mode != "firebase":
    raise SystemExit("Real launcher requires AUTH_MODE=firebase and DATA_MODE=firebase.")
if not settings.firebase_project_id:
    raise SystemExit("FIREBASE_PROJECT_ID is missing from backend/.env.")
if not settings.google_application_credentials and not settings.firebase_service_account_json:
    raise SystemExit("Configure GOOGLE_APPLICATION_CREDENTIALS or FIREBASE_SERVICE_ACCOUNT_JSON in backend/.env.")

frontend_env = dotenv_values(Path("../frontend/.env.local"))
required = (
    "VITE_API_BASE_URL", "VITE_FIREBASE_API_KEY", "VITE_FIREBASE_AUTH_DOMAIN",
    "VITE_FIREBASE_PROJECT_ID", "VITE_FIREBASE_APP_ID",
)
missing = [key for key in required if not frontend_env.get(key)]
if missing:
    raise SystemExit("Missing frontend Firebase variables: " + ", ".join(missing))
if any(key in frontend_env for key in ("private_key", "client_email", "GOOGLE_APPLICATION_CREDENTIALS", "FIREBASE_SERVICE_ACCOUNT_JSON")):
    raise SystemExit("Backend-only Firebase Admin credentials must not be placed in frontend/.env.local.")

get_firebase_app()
get_store().health_check()
print("Firebase Admin credentials and Firestore connectivity verified.")
PY
)

require_free_port 8000 "FastAPI backend"
require_free_port 5173 "Vite frontend"

(cd "$BACKEND" && exec "$BACKEND/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACK_PID=$!
wait_for_service "http://127.0.0.1:8000/api/v1/system/health" "$BACK_PID" "FastAPI backend"

health_modes="$(curl --silent --fail http://127.0.0.1:8000/api/v1/system/health | "$BACKEND/.venv/bin/python" -c 'import json,sys; data=json.load(sys.stdin); print("{}:{}".format(data.get("auth_mode"), data.get("data_mode")))')"
if [ "$health_modes" != "firebase:firebase" ]; then
  echo "Backend health check did not report Firebase authentication and Firestore data mode." >&2
  exit 1
fi

(cd "$FRONTEND" && exec npm run dev -- --strictPort) &
FRONT_PID=$!
wait_for_service "http://localhost:5173" "$FRONT_PID" "Vite frontend"

echo "BRMS real environment is ready."
echo "Frontend: http://localhost:5173"
echo "Backend:  http://127.0.0.1:8000"
echo "Auth/Data: firebase/firebase"

while kill -0 "$BACK_PID" 2>/dev/null && kill -0 "$FRONT_PID" 2>/dev/null; do sleep 1; done

if ! kill -0 "$BACK_PID" 2>/dev/null; then
  echo "FastAPI backend stopped unexpectedly." >&2
  wait "$BACK_PID" || exit $?
else
  echo "Vite frontend stopped unexpectedly." >&2
  wait "$FRONT_PID" || exit $?
fi
