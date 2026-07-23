#!/usr/bin/env bash
# Bootstrap unity-grok-studio: venvs, path exports, optional plugin install.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export UNITY_GROK_ROOT="$ROOT"
export GROK_PLUGIN_ROOT="${GROK_PLUGIN_ROOT:-$ROOT/plugin}"
export SFX_LIB="${SFX_LIB:-$ROOT/sfx_library}"
log() { echo "[unity-grok-studio] $*"; }
need() { command -v "$1" >/dev/null 2>&1 || { log "WARN: missing $1"; return 1; }; }
need python3
need curl || true
need uv || need uvx || log "WARN: install uv (https://github.com/astral-sh/uv) for MCP wheels"
VENV="$ROOT/.venv"
if [[ ! -d "$VENV" ]]; then
  log "creating venv $VENV"
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip -q install -U pip wheel setuptools
if [[ -f "$ROOT/mcp/blender-gen/requirements.txt" ]]; then
  pip -q install -r "$ROOT/mcp/blender-gen/requirements.txt" || log "WARN: blender-gen requirements partial"
else
  pip -q install 'mcp>=1.0' httpx pillow numpy || true
fi
if [[ -f "$ROOT/tools/sfx/requirements.txt" ]]; then
  pip -q install -r "$ROOT/tools/sfx/requirements.txt" || log "WARN: sfx requirements partial"
fi
pip -q install pytest || true
mkdir -p "$ROOT/sfx_library"/{searchable,generated,reports}
chmod +x "$ROOT"/scripts/*.sh "$ROOT"/mcp/wrappers/*.sh "$ROOT"/plugin/hooks/bin/*.sh 2>/dev/null || true
if [[ -x "$ROOT/scripts/apply_models.sh" ]]; then
  bash "$ROOT/scripts/apply_models.sh" || log "WARN: apply_models skipped"
fi
if command -v grok >/dev/null 2>&1; then
  log "install plugin: grok plugin install \"$ROOT/plugin\" --trust"
  log "  grok plugin enable unity-grok-studio"
fi
log "UNITY_GROK_ROOT=$UNITY_GROK_ROOT"
log "bootstrap complete. Run: ./scripts/doctor.sh"
