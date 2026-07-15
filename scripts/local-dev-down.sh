#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$REPO_ROOT/.mkc-dev"
PID_DIR="$STATE_DIR/pids"

process_cwd() {
  local pid="$1"
  lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1
}

stop_pid() {
  local name="$1"
  local pid="$2"

  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "Stopping $name (PID $pid)..."
    kill "$pid" >/dev/null 2>&1 || true

    for _ in {1..20}; do
      if ! kill -0 "$pid" >/dev/null 2>&1; then
        break
      fi
      sleep 0.5
    done

    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "$name did not stop gracefully; forcing..."
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  fi
}

stop_process() {
  local name="$1"
  local pid_file="$PID_DIR/$2.pid"

  if [[ ! -f "$pid_file" ]]; then
    echo "$name is not managed by local-dev scripts."
    return
  fi

  local pid
  pid="$(cat "$pid_file")"

  if kill -0 "$pid" >/dev/null 2>&1; then
    stop_pid "$name" "$pid"
  else
    echo "$name was not running."
  fi

  rm -f "$pid_file"
}

stop_orphan_gateway() {
  local port="${GATEWAY_PORT:-8080}"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  [[ -z "$pids" ]] && return

  local pid
  for pid in $pids; do
    if [[ "$(process_cwd "$pid")" == "$REPO_ROOT/gateway" ]]; then
      stop_pid "Gateway orphan on :$port" "$pid"
    fi
  done
}

stop_process "Flutter client" "client"
stop_process "Gateway" "gateway"
stop_orphan_gateway
stop_process "AI Celery worker" "ai-worker"
stop_process "AI Service" "ai-service"

echo "Local app processes stopped."
