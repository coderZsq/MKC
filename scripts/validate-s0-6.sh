#!/usr/bin/env bash
set -euo pipefail

# S0-6: Flutter client skeleton static checks.

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

check "client directory exists" test -d client
cd client

check "pubspec.yaml exists" test -f pubspec.yaml

for dir in lib/data lib/domain lib/presentation lib/config lib/shared test; do
  check "$dir/ exists" test -d "$dir"
done

for dep in flutter_riverpod go_router dio freezed_annotation json_annotation flutter_secure_storage; do
  check "pubspec declares $dep" grep -q "^  $dep:" pubspec.yaml
done

for dev in build_runner freezed json_serializable mockito flutter_lints; do
  check "pubspec dev_dependency $dev" grep -qE "^  $dev:" pubspec.yaml
done

# Domain layer should not import Flutter UI packages.
if grep -Rq "package:flutter/material.dart\|package:flutter/widgets.dart" lib/domain/ 2> /dev/null; then
  echo "[FAIL] domain layer imports Flutter UI packages"
  fail=1
else
  echo "[PASS] domain layer does not import Flutter UI packages"
fi

# Token storage should use secure storage, not SharedPreferences.
if grep -Rq "SharedPreferences\|shared_preferences" lib/; then
  echo "[FAIL] client uses SharedPreferences for token storage"
  fail=1
else
  echo "[PASS] client avoids SharedPreferences for tokens"
fi

# Smoke: flutter version check.
if command -v flutter > /dev/null 2>&1; then
  check "flutter installed" flutter --version
else
  echo "[SKIP] flutter not installed"
fi

if [ "$fail" -eq 0 ]; then
  echo "S0-6 validation passed."
else
  echo "S0-6 validation failed."
  exit 1
fi
