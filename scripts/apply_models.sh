#!/usr/bin/env bash
# Merge free model stanzas into ~/.grok/config.toml if missing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="${GROK_CONFIG:-$HOME/.grok/config.toml}"
EXAMPLE="$ROOT/config/models.example.toml"
mkdir -p "$(dirname "$CFG")"
touch "$CFG"

if grep -q '\[model\.free-auto\]' "$CFG" 2>/dev/null; then
  echo "[apply_models] free-auto already present in $CFG"
else
  {
    echo ""
    echo "# --- unity-grok free models (applied $(date -Iseconds)) ---"
    cat "$EXAMPLE"
  } >> "$CFG"
  echo "[apply_models] appended free model stanzas to $CFG"
fi

# Ensure a non-secret local key for the free chat shim when FreeLLMAPI key unset
if [[ -z "${FREELLM_API_KEY:-}" ]]; then
  echo "[apply_models] hint: export FREELLM_API_KEY=freellmapi-local  # for free-chat-shim"
fi
