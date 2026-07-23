#!/usr/bin/env bash
# Thin plugin-local wrapper: resolves UNITY_GROK_ROOT then execs package MCP wrapper.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# plugin/mcp-wrappers -> plugin -> package root
PKG="$(cd "$HERE/../.." && pwd)"
export UNITY_GROK_ROOT="${UNITY_GROK_ROOT:-$PKG}"
export GROK_PLUGIN_ROOT="${GROK_PLUGIN_ROOT:-$UNITY_GROK_ROOT/plugin}"
exec bash "$UNITY_GROK_ROOT/mcp/wrappers/blender-gen.sh" "$@"
