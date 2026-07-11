#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$REPO_ROOT/.mkc-dev"
LOG_DIR="$STATE_DIR/logs"
PID_DIR="$STATE_DIR/pids"

AI_PORT="${AI_PORT:-5001}"
GATEWAY_PORT="${GATEWAY_PORT:-8080}"
CLIENT_DEVICE="${CLIENT_DEVICE:-chrome}"
BASE_URL="${BASE_URL:-http://localhost:${GATEWAY_PORT}/api/v1}"
STORAGE_HOST="${STORAGE_HOST:-localhost}"

mkdir -p "$LOG_DIR" "$PID_DIR"

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" >/dev/null 2>&1
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local timeout="${3:-45}"
  local start
  start="$(date +%s)"

  until curl -fsS "$url" >/dev/null 2>&1; do
    if (( "$(date +%s)" - start >= timeout )); then
      echo "Error: $name did not become ready at $url within ${timeout}s."
      return 1
    fi
    sleep 1
  done
}

start_ai_service() {
  local pid_file="$PID_DIR/ai-service.pid"
  if is_running "$pid_file"; then
    echo "AI Service already running (PID $(cat "$pid_file"))."
    return
  fi

  if [[ ! -x "$REPO_ROOT/ai-service/.venv/bin/flask" ]]; then
    echo "Error: ai-service virtualenv is missing. Run:"
    echo "  cd ai-service && python -m venv .venv && source .venv/bin/activate && make install"
    exit 1
  fi

  echo "Starting AI Service on :$AI_PORT..."
  (
    cd "$REPO_ROOT/ai-service"
    set -a
    [[ -f .env ]] && source .env
    DEBUG=True
    PORT="$AI_PORT"
    INTERNAL_API_KEY="${INTERNAL_API_KEY:-dev-internal-key}"
    GATEWAY_INTERNAL_KEY="${GATEWAY_INTERNAL_KEY:-dev-internal-key}"
    REDIS_URL="${REDIS_URL:-redis://:dev-redis@localhost:6379/0}"
    CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://:dev-redis@localhost:6379/1}"
    CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://:dev-redis@localhost:6379/1}"
    MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-mkc}"
    MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-dev-minio}"
    MINIO_BUCKET="${MINIO_BUCKET:-mkc-resources}"
    MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
    EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-mock}"
    set +a
    exec .venv/bin/flask --app app.main:create_app run \
      --host=0.0.0.0 \
      --port="$AI_PORT" \
      --no-debugger \
      --no-reload
  ) >"$LOG_DIR/ai-service.log" 2>&1 &

  echo $! > "$pid_file"
  wait_for_http "AI Service" "http://localhost:${AI_PORT}/api/v1/health" 90
  echo "AI Service ready: http://localhost:${AI_PORT}/api/v1/health"
}

start_gateway() {
  local pid_file="$PID_DIR/gateway.pid"
  if is_running "$pid_file"; then
    echo "Gateway already running (PID $(cat "$pid_file"))."
    return
  fi

  if [[ ! -f "$REPO_ROOT/gateway/config/config.yaml" ]]; then
    cp "$REPO_ROOT/gateway/config/config.example.yaml" "$REPO_ROOT/gateway/config/config.yaml"
    echo "Created gateway/config/config.yaml from example."
  fi

  echo "Starting Gateway on :$GATEWAY_PORT..."
  (
    cd "$REPO_ROOT/gateway"
    export APP_SERVER_PORT="$GATEWAY_PORT"
    export APP_MYSQL_PASSWORD="${APP_MYSQL_PASSWORD:-dev-mkc}"
    export APP_REDIS_PASSWORD="${APP_REDIS_PASSWORD:-dev-redis}"
    export APP_JWT_SECRET="${APP_JWT_SECRET:-dev-jwt-secret}"
    export APP_AI_SERVICE_BASE_URL="${APP_AI_SERVICE_BASE_URL:-http://localhost:${AI_PORT}}"
    export APP_AI_SERVICE_INTERNAL_KEY="${APP_AI_SERVICE_INTERNAL_KEY:-dev-internal-key}"
    export APP_MINIO_ACCESS_KEY="${APP_MINIO_ACCESS_KEY:-mkc}"
    export APP_MINIO_SECRET_KEY="${APP_MINIO_SECRET_KEY:-dev-minio}"
    exec go run ./cmd/server
  ) >"$LOG_DIR/gateway.log" 2>&1 &

  echo $! > "$pid_file"
  wait_for_http "Gateway" "http://localhost:${GATEWAY_PORT}/health" 90
  echo "Gateway ready: http://localhost:${GATEWAY_PORT}/health"
}

start_client() {
  local pid_file="$PID_DIR/client.pid"
  if is_running "$pid_file"; then
    echo "Client already running (PID $(cat "$pid_file"))."
    return
  fi

  echo "Starting Flutter client on device '$CLIENT_DEVICE'..."
  (
    cd "$REPO_ROOT/client"
    exec flutter run -d "$CLIENT_DEVICE" \
      --dart-define=BASE_URL="$BASE_URL" \
      --dart-define=STORAGE_HOST="$STORAGE_HOST"
  ) >"$LOG_DIR/client.log" 2>&1 &

  echo $! > "$pid_file"
  echo "Client starting. Watch logs with:"
  echo "  tail -f $LOG_DIR/client.log"
}

cat <<EOF
=== MKC local app startup ===
AI_PORT=$AI_PORT
GATEWAY_PORT=$GATEWAY_PORT
CLIENT_DEVICE=$CLIENT_DEVICE
BASE_URL=$BASE_URL
STORAGE_HOST=$STORAGE_HOST
Logs: $LOG_DIR
EOF

start_ai_service
start_gateway
start_client

cat <<EOF

Started local app processes.

Useful URLs:
  AI Service: http://localhost:${AI_PORT}/api/v1/health
  Gateway:    http://localhost:${GATEWAY_PORT}/health

Stop with:
  ./scripts/local-dev-down.sh
EOF
