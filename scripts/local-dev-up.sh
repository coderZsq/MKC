#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$REPO_ROOT/.mkc-dev"
LOG_DIR="$STATE_DIR/logs"
PID_DIR="$STATE_DIR/pids"
BIN_DIR="$STATE_DIR/bin"

AI_PORT="${AI_PORT:-5001}"
GATEWAY_PORT="${GATEWAY_PORT:-8080}"
CLIENT_DEVICE="${CLIENT_DEVICE:-chrome}"
BASE_URL="${BASE_URL:-http://localhost:${GATEWAY_PORT}/api/v1}"
STORAGE_HOST="${STORAGE_HOST:-localhost}"

mkdir -p "$LOG_DIR" "$PID_DIR" "$BIN_DIR"

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" >/dev/null 2>&1
}

listening_pids() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
}

process_cwd() {
  local pid="$1"
  lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1
}

is_repo_gateway_pid() {
  local pid="$1"
  [[ "$(process_cwd "$pid")" == "$REPO_ROOT/gateway" ]]
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

wait_for_tcp() {
  local name="$1"
  local host="$2"
  local port="$3"
  local timeout="${4:-15}"
  local start
  start="$(date +%s)"

  until nc -z "$host" "$port" >/dev/null 2>&1; do
    if (( "$(date +%s)" - start >= timeout )); then
      echo "Error: $name did not become ready at ${host}:${port} within ${timeout}s."
      echo "Start local infrastructure port-forwards first:"
      echo "  ./infra/scripts/port-forward.sh"
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

  if [[ ! -x "$REPO_ROOT/ai-service/.venv/bin/python" ]]; then
    echo "Error: ai-service virtualenv is missing. Run:"
    echo "  cd ai-service && python -m venv .venv && source .venv/bin/activate && make install"
    exit 1
  fi

  # Source .env early so the startup message reflects actual provider settings.
  if [[ -f "$REPO_ROOT/ai-service/.env" ]]; then
    set -a
    source "$REPO_ROOT/ai-service/.env"
    set +a
  fi

  echo "Starting AI Service on :$AI_PORT with LLM_PROVIDER=${LLM_PROVIDER:-mock}, EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-mock}..."
  (
    cd "$REPO_ROOT/ai-service"
    set -a
    [[ -f .env ]] && source .env
    DEBUG=false
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
    EMBEDDING_MODEL="${EMBEDDING_MODEL:-bge-m3}"
    EMBEDDING_BASE_URL="${EMBEDDING_BASE_URL:-http://localhost:11434/v1}"
    EMBEDDING_DIMENSIONS="${EMBEDDING_DIMENSIONS:-1024}"
    VECTOR_STORE_DIMENSIONS="${VECTOR_STORE_DIMENSIONS:-1024}"
    LLM_PROVIDER="${LLM_PROVIDER:-mock}"
    LLM_MODEL="${LLM_MODEL:-deepseek-r1:8b}"
    LLM_BASE_URL="${LLM_BASE_URL:-http://localhost:11434/v1}"
    LLM_API_KEY="${LLM_API_KEY:-ollama}"
    set +a
    exec .venv/bin/python -m flask --app app.main:create_app run \
      --host=0.0.0.0 \
      --port="$AI_PORT" \
      --no-debugger \
      --no-reload
  ) >"$LOG_DIR/ai-service.log" 2>&1 &

  echo $! > "$pid_file"
  wait_for_http "AI Service" "http://localhost:${AI_PORT}/api/v1/health" 90
  echo "AI Service ready: http://localhost:${AI_PORT}/api/v1/health"
}

start_ai_worker() {
  local pid_file="$PID_DIR/ai-worker.pid"
  if is_running "$pid_file"; then
    echo "AI Celery worker already running (PID $(cat "$pid_file"))."
    return
  fi

  if [[ ! -x "$REPO_ROOT/ai-service/.venv/bin/celery" ]]; then
    echo "Error: ai-service Celery executable is missing. Run:"
    echo "  cd ai-service && python -m venv .venv && source .venv/bin/activate && make install"
    exit 1
  fi

  echo "Starting AI Celery worker..."
  (
    cd "$REPO_ROOT/ai-service"
    set -a
    [[ -f .env ]] && source .env
    DEBUG=false
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
    EMBEDDING_MODEL="${EMBEDDING_MODEL:-bge-m3}"
    EMBEDDING_BASE_URL="${EMBEDDING_BASE_URL:-http://localhost:11434/v1}"
    EMBEDDING_DIMENSIONS="${EMBEDDING_DIMENSIONS:-1024}"
    VECTOR_STORE_DIMENSIONS="${VECTOR_STORE_DIMENSIONS:-1024}"
    LLM_PROVIDER="${LLM_PROVIDER:-mock}"
    LLM_MODEL="${LLM_MODEL:-deepseek-r1:8b}"
    LLM_BASE_URL="${LLM_BASE_URL:-http://localhost:11434/v1}"
    LLM_API_KEY="${LLM_API_KEY:-ollama}"
    set +a
    exec .venv/bin/celery -A celery_workers.celery_app worker \
      -l info \
      -Q default,transcribe,parse_pdf,embed,rag
  ) >"$LOG_DIR/ai-worker.log" 2>&1 &

  echo $! > "$pid_file"
  echo "AI Celery worker starting. Watch logs with:"
  echo "  tail -f $LOG_DIR/ai-worker.log"
}

start_gateway() {
  local pid_file="$PID_DIR/gateway.pid"
  if is_running "$pid_file"; then
    echo "Gateway already running (PID $(cat "$pid_file"))."
    return
  fi

  local pids
  pids="$(listening_pids "$GATEWAY_PORT")"
  if [[ -n "$pids" ]]; then
    local pid
    for pid in $pids; do
      if is_repo_gateway_pid "$pid"; then
        echo "Gateway already listening on :$GATEWAY_PORT (PID $pid); adopting it."
        echo "$pid" > "$pid_file"
        wait_for_http "Gateway" "http://localhost:${GATEWAY_PORT}/health" 10
        echo "Gateway ready: http://localhost:${GATEWAY_PORT}/health"
        return
      fi
    done

    echo "Error: port $GATEWAY_PORT is already in use by another process:"
    lsof -nP -iTCP:"$GATEWAY_PORT" -sTCP:LISTEN || true
    exit 1
  fi

  if [[ ! -f "$REPO_ROOT/gateway/config/config.yaml" ]]; then
    cp "$REPO_ROOT/gateway/config/config.example.yaml" "$REPO_ROOT/gateway/config/config.yaml"
    echo "Created gateway/config/config.yaml from example."
  fi

  echo "Starting Gateway on :$GATEWAY_PORT..."
  (
    cd "$REPO_ROOT/gateway"
    go build -o "$BIN_DIR/gateway-server" ./cmd/server
  )
  APP_SERVER_PORT="$GATEWAY_PORT" \
  APP_MYSQL_PASSWORD="${APP_MYSQL_PASSWORD:-dev-mkc}" \
  APP_REDIS_PASSWORD="${APP_REDIS_PASSWORD:-dev-redis}" \
  APP_JWT_SECRET="${APP_JWT_SECRET:-dev-jwt-secret}" \
  APP_AI_SERVICE_BASE_URL="${APP_AI_SERVICE_BASE_URL:-http://localhost:${AI_PORT}}" \
  APP_AI_SERVICE_INTERNAL_KEY="${APP_AI_SERVICE_INTERNAL_KEY:-dev-internal-key}" \
  APP_MINIO_ACCESS_KEY="${APP_MINIO_ACCESS_KEY:-mkc}" \
  APP_MINIO_SECRET_KEY="${APP_MINIO_SECRET_KEY:-dev-minio}" \
  nohup bash -c 'cd "$1" && exec "$2"' bash "$REPO_ROOT/gateway" "$BIN_DIR/gateway-server" >"$LOG_DIR/gateway.log" 2>&1 < /dev/null &

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

check_local_infra() {
  wait_for_tcp "MySQL" "localhost" "3306" 3
  wait_for_tcp "Redis" "localhost" "6379" 3
  wait_for_tcp "MinIO" "localhost" "9000" 3
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

check_local_infra
start_ai_service
start_ai_worker
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
