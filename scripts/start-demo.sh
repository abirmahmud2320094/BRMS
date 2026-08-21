#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACK_PID=""
FRONT_PID=""

cleanup() {
  trap - EXIT INT TERM
  if [ -n "$BACK_PID" ]; then
    kill "$BACK_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONT_PID" ]; then
    kill "$FRONT_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

wait_for_service() {
  url="$1"
  pid="$2"
  name="$3"
  attempts=0

  while [ "$attempts" -lt 50 ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "$name stopped before it became ready." >&2
      wait "$pid" || true
      return 1
    fi
    if curl --silent --fail "$url" >/dev/null; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 0.2
  done

  echo "$name did not become ready at $url." >&2
  return 1
}

require_free_port() {
  port="$1"
  name="$2"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "$name cannot start because port $port is already in use." >&2
    return 1
  fi
}

trap cleanup EXIT INT TERM

echo "Starting BRMS presentation demo..."

if [ ! -d "$ROOT/backend/.venv" ]; then
  python3 -m venv "$ROOT/backend/.venv"
fi
source "$ROOT/backend/.venv/bin/activate"
pip install -r "$ROOT/backend/requirements.txt"

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  (cd "$ROOT/frontend" && npm install)
fi

require_free_port 8000 "FastAPI backend"
require_free_port 5173 "Vite frontend"

export AUTH_MODE=demo
export DATA_MODE=local
export LOCAL_DATA_PATH="$ROOT/backend/data/local_data.json"
export CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
(cd "$ROOT/backend" && exec "$ROOT/backend/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACK_PID=$!
wait_for_service "http://127.0.0.1:8000/api/v1/system/health" "$BACK_PID" "FastAPI backend"

export VITE_API_BASE_URL="http://127.0.0.1:8000/api/v1"
export VITE_DEMO_MODE="true"
(cd "$ROOT/frontend" && npm run dev -- --strictPort) &
FRONT_PID=$!
wait_for_service "http://localhost:5173" "$FRONT_PID" "Vite frontend"

echo "Backend ready: http://127.0.0.1:8000"
echo "Frontend ready: http://localhost:5173"

while kill -0 "$BACK_PID" 2>/dev/null && kill -0 "$FRONT_PID" 2>/dev/null; do
  sleep 1
done

if ! kill -0 "$BACK_PID" 2>/dev/null; then
  echo "FastAPI backend stopped unexpectedly." >&2
  wait "$BACK_PID" || exit $?
else
  echo "Vite frontend stopped unexpectedly." >&2
  wait "$FRONT_PID" || exit $?
fi
