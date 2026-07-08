#!/usr/bin/env bash
set -euo pipefail

# S0-3: CI pipeline static checks.

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

for wf in ci-gateway.yml ci-ai-service.yml ci-client.yml ci-docs.yml; do
  check ".github/workflows/$wf exists" test -f ".github/workflows/$wf"
  if python3 -c "import yaml" > /dev/null 2>&1; then
    check "$wf is valid YAML" python3 -c "import yaml; yaml.safe_load(open('.github/workflows/$wf'))"
  else
    echo "[SKIP] $wf YAML syntax check (PyYAML not installed)"
  fi
  check "$wf defines concurrency" grep -q '^concurrency:' ".github/workflows/$wf"
  check "$wf defines permissions" grep -q '^permissions:' ".github/workflows/$wf"
done

# Recommended action versions.
check "uses actions/checkout@v4" grep -q 'actions/checkout@v4' .github/workflows/*.yml
check "uses actions/setup-go@v5" grep -q 'actions/setup-go@v5' .github/workflows/*.yml
check "uses actions/setup-python@v5" grep -q 'actions/setup-python@v5' .github/workflows/*.yml
check "uses subosito/flutter-action@v2" grep -q 'subosito/flutter-action@v2' .github/workflows/*.yml

# README contains CI badge.
check "README contains CI badge" grep -q 'github.com/.*/workflows/.*/badge.svg' README.md

if [ "$fail" -eq 0 ]; then
  echo "S0-3 validation passed."
else
  echo "S0-3 validation failed."
  exit 1
fi
