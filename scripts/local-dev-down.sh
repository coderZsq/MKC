#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$REPO_ROOT/.mkc-dev"
PID_DIR="$STATE_DIR/pids"

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
  else
    echo "$name was not running."
  fi

  rm -f "$pid_file"
}

stop_process "Flutter client" "client"
stop_process "Gateway" "gateway"
stop_process "AI Celery worker" "ai-worker"
stop_process "AI Service" "ai-service"

echo "Local app processes stopped."
