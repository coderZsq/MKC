#!/usr/bin/env bash
set -euo pipefail

# S0-4: Database schema and migration static checks.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0

check() {
  local msg="$1"
  shift
  if "$@" > /dev/null 2>&1; then
    echo "[PASS] $msg"
  else
    echo "[FAIL] $msg"
    fail=1
  fi
}

check "migration up file exists" test -f gateway/migrations/000001_init_schema.up.sql
check "migration down file exists" test -f gateway/migrations/000001_init_schema.down.sql
check "Makefile has migrate-up target" grep -q 'migrate-up:' gateway/Makefile
check "Makefile has migrate-down target" grep -q 'migrate-down:' gateway/Makefile

# No real passwords in migration SQL.
if grep -inE 'password|secret' gateway/migrations/*.sql | grep -vE 'placeholder|example|dummy|TODO|FIXME' | grep -q .; then
  echo "[FAIL] possible password/secret string found in migration SQL"
  fail=1
else
  echo "[PASS] migration SQL has no obvious passwords"
fi

# Core tables and schema characteristics.
for table in users resources tasks conversations messages; do
  check "table $table defined in up migration" grep -qi "CREATE TABLE \`$table\`" gateway/migrations/000001_init_schema.up.sql
done

check "BIGINT UNSIGNED AUTO_INCREMENT primary keys" grep -q 'BIGINT UNSIGNED AUTO_INCREMENT' gateway/migrations/000001_init_schema.up.sql
check "uuid unique constraints" grep -q 'UNIQUE KEY.*uuid' gateway/migrations/000001_init_schema.up.sql
check "users.email unique" grep -q 'UNIQUE KEY.*email' gateway/migrations/000001_init_schema.up.sql
check "DATETIME(3) columns" grep -q 'DATETIME(3)' gateway/migrations/000001_init_schema.up.sql
check "utf8mb4 charset" grep -qi 'utf8mb4' gateway/migrations/000001_init_schema.up.sql
check "JSON columns" grep -q 'JSON' gateway/migrations/000001_init_schema.up.sql
check "deleted_at soft delete" grep -q 'deleted_at' gateway/migrations/000001_init_schema.up.sql

if [ "$fail" -eq 0 ]; then
  echo "S0-4 validation passed."
else
  echo "S0-4 validation failed."
  exit 1
fi
