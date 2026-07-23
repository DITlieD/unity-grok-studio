#!/usr/bin/env bash
set -euo pipefail
ROOT="${UNITY_GROK_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
export UNITY_GROK_ROOT="$ROOT"
export PYTHONPATH="$ROOT/mcp/blender-gen/lib${PYTHONPATH:+:$PYTHONPATH}"
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"
exec "$PY" "$ROOT/mcp/blender-gen/server.py"
