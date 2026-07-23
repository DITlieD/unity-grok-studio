#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$(cd "$HERE/../.." && pwd)"
export UNITY_GROK_ROOT="${UNITY_GROK_ROOT:-$PKG}"
export GROK_PLUGIN_ROOT="${GROK_PLUGIN_ROOT:-$UNITY_GROK_ROOT/plugin}"
exec bash "$UNITY_GROK_ROOT/mcp/wrappers/vision-check.sh" "$@"
