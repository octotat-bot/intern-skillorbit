#!/usr/bin/env bash
# Start the backend (Flask) and frontend (Vite) in the background.
#
# Usage:
#   ./scripts/start.sh            development servers (Flask + Vite dev server)
#   ./scripts/start.sh --prod     production-like (gunicorn + built frontend via vite preview)
#
# Ports default to 5000 (backend) and 5173 (frontend). If a default port is busy (on macOS,
# AirPlay Receiver holds 5000) the next free port is used automatically. To force a port:
#   BACKEND_PORT=5001 FRONTEND_PORT=5174 ./scripts/start.sh
#
# PIDs and logs are written to .run/. Stop everything with ./scripts/stop.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/.run"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
BACKEND_PORT_SET="${BACKEND_PORT:+yes}"
FRONTEND_PORT_SET="${FRONTEND_PORT:+yes}"
BACKEND_PORT="${BACKEND_PORT:-5000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
PORT_SEARCH_RANGE=20   # how many ports above the default to try
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-60}"   # seconds to wait for each service
MODE="dev"

case "${1:-}" in
  "") ;;
  --prod) MODE="prod" ;;
  -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
  *) echo "Unknown option: $1 (use --prod or --help)" >&2; exit 2 ;;
esac

mkdir -p "$RUN_DIR"
STARTED=()   # services started by this run (cleaned up if a later step fails)

info()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok()    { printf '\033[1;32m ok\033[0m %s\n' "$*"; }
fail()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; }

is_running() {   # $1 = service name; true if its PID file points at a live process
  local pid_file="$RUN_DIR/$1.pid"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

port_in_use() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t >/dev/null 2>&1; }

resolve_port() {   # $1 = default port, $2 = "yes" if user-chosen, $3 = label; prints the port to use
  local port="$1" chosen="$2" label="$3" candidate
  if ! port_in_use "$port"; then echo "$port"; return; fi
  if [[ "$chosen" == "yes" ]]; then
    fail "$label port $port is already in use; choose a different one."; return 1
  fi
  for ((candidate = port + 1; candidate <= port + PORT_SEARCH_RANGE; candidate++)); do
    if ! port_in_use "$candidate"; then
      info "$label port $port is busy; using $candidate instead" >&2
      echo "$candidate"; return
    fi
  done
  fail "no free $label port between $port and $((port + PORT_SEARCH_RANGE))"; return 1
}

wait_for_url() {   # $1 = url, $2 = service name; fails if the process dies or time runs out
  local url="$1" name="$2" pid elapsed=0
  pid="$(cat "$RUN_DIR/$name.pid")"
  until curl -fsS -o /dev/null "$url" 2>/dev/null; do
    if ! kill -0 "$pid" 2>/dev/null; then
      fail "$name exited during startup. Last log lines:"; tail -n 20 "$RUN_DIR/$name.log" >&2; return 1
    fi
    if (( elapsed >= HEALTH_TIMEOUT )); then
      fail "$name did not respond at $url within ${HEALTH_TIMEOUT}s. Last log lines:"
      tail -n 20 "$RUN_DIR/$name.log" >&2; return 1
    fi
    sleep 1; elapsed=$((elapsed + 1))
  done
}

# ---------------------------------------------------------------------------
# One-time setup (skipped when already done)
# ---------------------------------------------------------------------------
ensure_backend_setup() {
  if [[ ! -x "$BACKEND_DIR/venv/bin/python" ]]; then
    local py; py="$(command -v python3.11 || command -v python3 || true)"
    [[ -n "$py" ]] || { fail "Python 3.11+ is required"; exit 1; }
    info "Creating backend virtual environment with $py"
    "$py" -m venv "$BACKEND_DIR/venv"
    "$BACKEND_DIR/venv/bin/pip" install -q --upgrade pip
    info "Installing backend dependencies (first run only)"
    "$BACKEND_DIR/venv/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"
  fi
  if ! "$BACKEND_DIR/venv/bin/python" -c "import en_core_web_sm" 2>/dev/null; then
    info "Downloading spaCy model en_core_web_sm (first run only)"
    "$BACKEND_DIR/venv/bin/python" -m spacy download en_core_web_sm >/dev/null
  fi
}

ensure_frontend_setup() {
  command -v npm >/dev/null || { fail "Node.js 18+ and npm are required"; exit 1; }
  if [[ ! -x "$FRONTEND_DIR/node_modules/.bin/vite" ]]; then
    info "Installing frontend dependencies (first run only)"
    (cd "$FRONTEND_DIR" && npm install --no-audit --no-fund >/dev/null)
  fi
}

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
start_backend() {
  if is_running backend; then ok "backend already running (PID $(cat "$RUN_DIR/backend.pid"))"; return; fi
  info "Starting backend ($MODE) on port $BACKEND_PORT"
  export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:$FRONTEND_PORT,http://127.0.0.1:$FRONTEND_PORT}"
  cd "$BACKEND_DIR"
  if [[ "$MODE" == "prod" ]]; then
    PORT="$BACKEND_PORT" nohup ./venv/bin/gunicorn -c gunicorn.conf.py "app:create_app()" \
      > "$RUN_DIR/backend.log" 2>&1 &
  else
    PORT="$BACKEND_PORT" nohup ./venv/bin/python run.py > "$RUN_DIR/backend.log" 2>&1 &
  fi
  echo $! > "$RUN_DIR/backend.pid"
  echo "$BACKEND_PORT" > "$RUN_DIR/backend.port"
  STARTED+=(backend)
  cd "$ROOT"
  wait_for_url "http://localhost:$BACKEND_PORT/api/health" backend
  ok "backend ready: http://localhost:$BACKEND_PORT/api/health"
}

start_frontend() {
  if is_running frontend; then ok "frontend already running (PID $(cat "$RUN_DIR/frontend.pid"))"; return; fi
  local api_url="http://localhost:$BACKEND_PORT"
  cd "$FRONTEND_DIR"
  if [[ "$MODE" == "prod" ]]; then
    info "Building frontend against $api_url"
    VITE_API_BASE_URL="$api_url" ./node_modules/.bin/vite build > "$RUN_DIR/frontend-build.log" 2>&1 \
      || { fail "frontend build failed:"; tail -n 20 "$RUN_DIR/frontend-build.log" >&2; exit 1; }
    info "Starting frontend preview on port $FRONTEND_PORT"
    nohup ./node_modules/.bin/vite preview --port "$FRONTEND_PORT" --strictPort \
      > "$RUN_DIR/frontend.log" 2>&1 &
  else
    info "Starting frontend dev server on port $FRONTEND_PORT (API: $api_url)"
    VITE_API_BASE_URL="$api_url" nohup ./node_modules/.bin/vite --port "$FRONTEND_PORT" --strictPort \
      > "$RUN_DIR/frontend.log" 2>&1 &
  fi
  echo $! > "$RUN_DIR/frontend.pid"
  echo "$FRONTEND_PORT" > "$RUN_DIR/frontend.port"
  STARTED+=(frontend)
  cd "$ROOT"
  wait_for_url "http://localhost:$FRONTEND_PORT/" frontend
  ok "frontend ready: http://localhost:$FRONTEND_PORT"
}

# On failure, stop only the services this run started (leave earlier ones alone).
cleanup_on_failure() {
  local status=$?
  if (( status != 0 && ${#STARTED[@]} > 0 )); then
    fail "startup failed; stopping ${STARTED[*]}"
    "$ROOT/scripts/stop.sh" "${STARTED[@]}" >/dev/null 2>&1 || true
  fi
}
trap cleanup_on_failure EXIT

ensure_backend_setup
ensure_frontend_setup
# A service that is already running keeps its port (recorded at start); others get a free one.
if is_running backend; then BACKEND_PORT="$(cat "$RUN_DIR/backend.port")"
else BACKEND_PORT="$(resolve_port "$BACKEND_PORT" "$BACKEND_PORT_SET" backend)"; fi
if is_running frontend; then FRONTEND_PORT="$(cat "$RUN_DIR/frontend.port")"
else FRONTEND_PORT="$(resolve_port "$FRONTEND_PORT" "$FRONTEND_PORT_SET" frontend)"; fi
start_backend
start_frontend

echo
ok "All services running. Open http://localhost:$FRONTEND_PORT"
echo "    Logs: $RUN_DIR/backend.log, $RUN_DIR/frontend.log"
echo "    Stop: ./scripts/stop.sh"
