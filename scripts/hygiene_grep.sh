#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
FAIL=0
P1="/home/lied/""teikoku"
P2="C:/Users/""LieD"
P3="uvx"".exe"
P4="com.""taporbit"
EX=(--exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=__pycache__ --exclude-dir=tests --exclude=*.png --exclude=*.wav --exclude=*.dll --exclude=*.db --exclude=hygiene_grep.sh --exclude=EXCLUDE.md --exclude=NOTICE)
check() { local pat="$1"; local label="$2"; if grep -RIn "${EX[@]}" -e "$pat" . 2>/dev/null | head -1 | grep -q .; then echo "HYGIENE FAIL: $label"; grep -RIn "${EX[@]}" -e "$pat" . 2>/dev/null | head -20 || true; FAIL=1; fi; }
check "$P1" owner-teikoku-path
check "$P2" windows-personal-path
check "$P3" uvx-exe
check "$P4" legacy-product-id
if [[ $FAIL -ne 0 ]]; then echo hygiene_grep: FAILED; exit 1; fi
echo hygiene_grep: OK
exit 0
