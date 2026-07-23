#!/usr/bin/env bash
# Run packaged Unity static gates (off-agent; do not let free models self-certify).
# Usage:
#   run_unity_static_gates.sh --root <dir-with-cs>
#   run_unity_static_gates.sh --files a.cs,b.cs [--project <UnityProject>]
#   run_unity_static_gates.sh --fixture   # package sample fixtures
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"
POLICY="$ROOT/unity-symbol-policy.json"
JSON_FLAG=()
FILES=""
SCAN_ROOT=""
PROJECT=""
USE_FIXTURE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) SCAN_ROOT="$2"; shift 2 ;;
    --files) FILES="$2"; shift 2 ;;
    --project) PROJECT="$2"; shift 2 ;;
    --json) JSON_FLAG=(--json); shift ;;
    --fixture) USE_FIXTURE=1; shift ;;
    -h|--help)
      sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ "$USE_FIXTURE" -eq 1 ]]; then
  SCAN_ROOT="$ROOT/fixtures"
  PROJECT="$ROOT/fixtures"
  FILES=""
fi

if [[ -z "$FILES" && -z "$SCAN_ROOT" ]]; then
  echo "need --root, --files, or --fixture" >&2
  exit 2
fi

echo "=== toban001_check ==="
if [[ -n "$FILES" ]]; then
  "$PY" "$ROOT/toban001_check.py" --files "$FILES" "${JSON_FLAG[@]+"${JSON_FLAG[@]}"}"
else
  "$PY" "$ROOT/toban001_check.py" --root "$SCAN_ROOT" "${JSON_FLAG[@]+"${JSON_FLAG[@]}"}"
fi

echo "=== unity_symbol_census ==="
if [[ -n "$FILES" ]]; then
  "$PY" "$ROOT/unity_symbol_census.py" --files "$FILES" --policy "$POLICY" "${JSON_FLAG[@]+"${JSON_FLAG[@]}"}"
else
  # census expects --files; expand .cs under root
  mapfile -t cs < <(find "$SCAN_ROOT" -name '*.cs' -type f | head -200)
  if [[ ${#cs[@]} -eq 0 ]]; then
    echo "no .cs under $SCAN_ROOT (skip census)"
  else
    IFS=','; joined="${cs[*]}"; IFS=$' \t\n'
    joined="${joined// /,}"
    "$PY" "$ROOT/unity_symbol_census.py" --files "$joined" --policy "$POLICY" "${JSON_FLAG[@]+"${JSON_FLAG[@]}"}"
  fi
fi

echo "=== mono_wire_census ==="
PROJ="${PROJECT:-$SCAN_ROOT}"
if [[ -n "$FILES" ]]; then
  "$PY" "$ROOT/mono_wire_census.py" --new-files "$FILES" --project "${PROJ:-.}" "${JSON_FLAG[@]+"${JSON_FLAG[@]}"}" || true
elif [[ -n "$PROJ" && -d "$PROJ" ]]; then
  mapfile -t cs < <(find "${SCAN_ROOT:-$PROJ}" -name '*.cs' -type f | head -50)
  if [[ ${#cs[@]} -gt 0 ]]; then
    IFS=','; joined="${cs[*]}"; IFS=$' \t\n'
    joined="${joined// /,}"
    "$PY" "$ROOT/mono_wire_census.py" --new-files "$joined" --project "$PROJ" "${JSON_FLAG[@]+"${JSON_FLAG[@]}"}" || true
  fi
fi

echo "=== scan_unity_patterns ==="
if [[ -n "$SCAN_ROOT" ]]; then
  "$PY" "$ROOT/scan_unity_patterns.py" "$SCAN_ROOT" || true
elif [[ -n "$FILES" ]]; then
  IFS=',' read -ra arr <<< "$FILES"
  for f in "${arr[@]}"; do
    "$PY" "$ROOT/scan_unity_patterns.py" "$f" || true
  done
fi

echo "=== unity static gates complete ==="
