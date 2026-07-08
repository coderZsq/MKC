#!/usr/bin/env bash
set -euo pipefail

# Run all Sprint 0 validation scripts.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_K8S=false
SKIP_DB=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-k8s) SKIP_K8S=true; shift ;;
    --skip-db) SKIP_DB=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

fail=0
echo "Starting Sprint 0 validation..."

run() {
  local script="$1"
  local name="$2"
  echo ""
  echo "== $name =="
  if bash "$script"; then
    echo "== $name OK =="
  else
    echo "== $name FAILED =="
    fail=1
  fi
}

run scripts/validate-s0-1.sh "S0-1 Repo Governance"

if [ "$SKIP_K8S" = true ]; then
  echo ""
  echo "== S0-2 Local K8s Environment (skipped via --skip-k8s) =="
else
  run scripts/validate-s0-2.sh "S0-2 Local K8s Environment"
fi

run scripts/validate-s0-3.sh "S0-3 CI Pipeline"

if [ "$SKIP_DB" = true ]; then
  echo ""
  echo "== S0-4 Database Schema (skipped via --skip-db) =="
else
  run scripts/validate-s0-4.sh "S0-4 Database Schema"
fi

run scripts/validate-s0-5.sh "S0-5 API Design"
run scripts/validate-s0-6.sh "S0-6 Flutter Skeleton"
run scripts/validate-s0-7.sh "S0-7 Gateway Skeleton"
run scripts/validate-s0-8.sh "S0-8 AI Service Skeleton"

echo ""
if [ "$fail" -eq 0 ]; then
  echo "All Sprint 0 validations passed."
else
  echo "Some Sprint 0 validations failed."
  exit 1
fi
