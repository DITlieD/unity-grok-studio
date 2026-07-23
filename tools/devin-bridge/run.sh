#!/usr/bin/env bash
# Boot local Devin Messages proxy on 127.0.0.1:8810 using THIS machine's Devin Desktop login.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${DEVIN_PROXY_PORT:-8810}"

# Resolve credentials from coworker's Devin Desktop install:
# Linux: ~/.local/share/devin/credentials.toml, ~/.config/devin/, ~/.config/Devin/
# macOS: ~/Library/Application Support/devin/ etc if present
# Windows/WSL: %APPDATA%/devin/credentials.toml via /mnt/c/Users/$USER/AppData/Roaming/devin/ if exists
# DEVIN_CREDS override always wins
resolve_creds() {
  if [[ -n "${DEVIN_CREDS:-}" && -f "${DEVIN_CREDS}" ]]; then
    echo "$DEVIN_CREDS"
    return 0
  fi
  local candidates=(
    "${HOME}/.local/share/devin/credentials.toml"
    "${HOME}/.config/devin/credentials.toml"
    "${HOME}/.config/Devin/credentials.toml"
    "${HOME}/Library/Application Support/devin/credentials.toml"
    "${HOME}/Library/Application Support/Devin/credentials.toml"
  )
  # Windows/WSL AppData
  if [[ -n "${USER:-}" ]]; then
    candidates+=(
      "/mnt/c/Users/${USER}/AppData/Roaming/devin/credentials.toml"
      "/mnt/c/Users/${USER}/AppData/Roaming/Devin/credentials.toml"
    )
  fi
  if [[ -n "${USERNAME:-}" ]]; then
    candidates+=(
      "/mnt/c/Users/${USERNAME}/AppData/Roaming/devin/credentials.toml"
    )
  fi
  local c
  for c in "${candidates[@]}"; do
    if [[ -f "$c" ]]; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

if curl -s -m2 -o /dev/null "http://127.0.0.1:${PORT}/health" 2>/dev/null; then
  echo "[bridge] devin proxy already up on :${PORT}"
  exit 0
fi

if ! CREDS="$(resolve_creds)"; then
  echo "Install Devin Desktop, log in, then re-run. Or set DEVIN_CREDS=/path/to/credentials.toml" >&2
  exit 1
fi

# Create venv at $ROOT/.venv if missing; pip install -r requirements.txt
VENV="${ROOT}/.venv"
if [[ ! -x "${VENV}/bin/python" ]]; then
  echo "[bridge] creating venv at ${VENV}"
  python3 -m venv "${VENV}"
  "${VENV}/bin/pip" -q install -U pip wheel
  "${VENV}/bin/pip" -q install -r "${ROOT}/requirements.txt"
fi

export DEVIN_CREDS="$CREDS"
export DEVIN_PROXY_MODEL="${DEVIN_PROXY_MODEL:-}"
export DEVIN_TOOL_DESC="${DEVIN_TOOL_DESC:-generic}"
export DEVIN_PROXY_PORT="$PORT"
export DEVIN_LOG="${DEVIN_LOG:-1}"

LOG="${ROOT}/proxy.log"
cd "${ROOT}/proxy"

if [[ "${DEVIN_BRIDGE_FOREGROUND:-0}" == "1" ]]; then
  echo "[bridge] starting foreground on :${PORT} (creds=${CREDS})"
  exec "${VENV}/bin/python" devin_proxy.py
fi

# Start proxy with setsid/nohup
if command -v setsid >/dev/null 2>&1; then
  setsid nohup "${VENV}/bin/python" devin_proxy.py >"${LOG}" 2>&1 < /dev/null &
else
  nohup "${VENV}/bin/python" devin_proxy.py >"${LOG}" 2>&1 < /dev/null &
fi

for i in $(seq 1 40); do
  sleep 0.35
  if curl -s -m2 -o /dev/null "http://127.0.0.1:${PORT}/health" 2>/dev/null; then
    echo "[bridge] devin proxy up on :${PORT}"
    exit 0
  fi
done
echo "[bridge] WARN: devin proxy did not become healthy on :${PORT} (see ${LOG})" >&2
tail -20 "${LOG}" 2>/dev/null || true
exit 1
