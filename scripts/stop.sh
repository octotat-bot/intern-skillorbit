#!/usr/bin/env bash
# Stop the services started by ./scripts/start.sh.
#
# Usage:
#   ./scripts/stop.sh                 stop frontend and backend
#   ./scripts/stop.sh backend         stop only the named service(s)
#
# Each service is stopped with its child processes (e.g. Flask's debug reloader or
# gunicorn workers): SIGTERM first, then SIGKILL after a grace period.
# Only processes recorded in .run/*.pid are touched; nothing else is killed.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/.run"
GRACE_SECONDS="${GRACE_SECONDS:-10}"

ok()   { printf '\033[1;32m ok\033[0m %s\n' "$*"; }
info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }

descendants() {   # print all descendant PIDs of $1, deepest first
  local child
  for child in $(pgrep -P "$1" 2>/dev/null); do
    descendants "$child"
    echo "$child"
  done
}

stop_service() {   # $1 = service name
  local name="$1" pid_file="$RUN_DIR/$1.pid" pid pids waited=0
  if [[ ! -f "$pid_file" ]]; then
    ok "$name is not running"; return
  fi
  pid="$(cat "$pid_file")"
  if ! kill -0 "$pid" 2>/dev/null; then
    ok "$name was not running (removed stale PID file)"; rm -f "$RUN_DIR/$name.pid" "$RUN_DIR/$name.port"; return
  fi

  info "Stopping $name (PID $pid)"
  pids="$(descendants "$pid") $pid"
  kill -TERM $pids 2>/dev/null
  while kill -0 "$pid" 2>/dev/null && (( waited < GRACE_SECONDS )); do
    sleep 1; waited=$((waited + 1))
  done
  # Anything still alive (parent or children) gets SIGKILL.
  for p in $pids; do kill -0 "$p" 2>/dev/null && kill -KILL "$p" 2>/dev/null; done
  rm -f "$RUN_DIR/$name.pid" "$RUN_DIR/$name.port"
  ok "$name stopped"
}

services=("$@")
(( ${#services[@]} )) || services=(frontend backend)
for service in "${services[@]}"; do
  case "$service" in
    frontend|backend) stop_service "$service" ;;
    *) echo "Unknown service: $service (use frontend or backend)" >&2; exit 2 ;;
  esac
done
