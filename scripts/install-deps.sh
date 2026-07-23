#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WITH_BLENDER=0; ASSUME_YES=0; WITH_DEVIN_BRIDGE=0; WITH_LIA=0; WITH_UNITY_CLI=0
for a in "$@"; do
  case "$a" in
    --with-blender) WITH_BLENDER=1;;
    --with-devin-bridge) WITH_DEVIN_BRIDGE=1;;
    --with-lia) WITH_LIA=1;;
    --with-unity-cli) WITH_UNITY_CLI=1;;
    --assume-yes|-y) ASSUME_YES=1;;
    -h|--help)
      cat <<'USAGE'
Usage: install-deps.sh [options]

  (default)              bootstrap + uv; install grok plugin if present; run doctor
  --with-blender         optional Blender (needs --assume-yes for auto-install)
  --with-devin-bridge    create tools/devin-bridge venv + pip deps (does not start proxy)
  --with-lia             install LIA Trust ≥ 0.3.0 from DITlieD/lia-trust
  --with-unity-cli       official Unity CLI companion (print install; binary only with --assume-yes)
  --assume-yes | -y      allow non-interactive optional installs when paired with a --with-* flag
  -h | --help            this help

Never silently installs multi-GB Unity Editor versions. See docs/UNITY-CLI.md and docs/DEPENDENCIES.md.
USAGE
      exit 0
      ;;
  esac
done
bash "$ROOT/scripts/bootstrap.sh"
# Bucket B: uv
if ! command -v uv >/dev/null 2>&1 && ! command -v uvx >/dev/null 2>&1; then
  echo "Installing uv (user-level)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
# Optional Blender (Bucket C)
if [[ $WITH_BLENDER -eq 1 ]]; then
  if ! command -v blender >/dev/null 2>&1; then
    if [[ $ASSUME_YES -eq 1 ]]; then
      echo "Attempting Blender install (requires privileges)..."
      if command -v snap >/dev/null 2>&1; then sudo snap install blender --classic || true
      elif command -v brew >/dev/null 2>&1; then brew install --cask blender || true
      else echo "No snap/brew; install Blender 5.x manually (see docs/SETUP.md)"; fi
    else
      echo "Pass --assume-yes with --with-blender to auto-install, or install Blender manually."
    fi
  fi
fi
# Optional Devin bridge Python deps (does NOT start proxy without credentials)
if [[ $WITH_DEVIN_BRIDGE -eq 1 ]]; then
  BR="$ROOT/tools/devin-bridge"
  if [[ -f "$BR/requirements.txt" ]]; then
    VENV="$BR/.venv"
    if [[ ! -x "$VENV/bin/python" ]]; then
      echo "Creating Devin bridge venv at $VENV ..."
      python3 -m venv "$VENV"
      "$VENV/bin/pip" -q install -U pip wheel
    fi
    echo "Installing Devin bridge Python deps..."
    "$VENV/bin/pip" -q install -r "$BR/requirements.txt"
    echo ""
    echo "=== Devin bridge next steps ==="
    echo "1. Install Devin Desktop from Cognition (your own account)."
    echo "2. Log in once in the Desktop app (creates credentials.toml)."
    echo "3. Run: ./tools/devin-bridge/run.sh"
    echo "4. Health: curl -s http://127.0.0.1:8810/health"
    echo "5. Select Grok model: -m devin-free  (or devin-glm / devin-swe)"
    echo "Do NOT start the bridge until credentials exist."
    echo "================================"
  else
    echo "WARN: tools/devin-bridge/requirements.txt missing"
  fi
fi
# Optional LIA Trust ≥ 0.3.0 (Bucket C — user network; PreToolUse GATE)
if [[ $WITH_LIA -eq 1 ]]; then
  echo "Installing LIA Trust from DITlieD/lia-trust main (expect ≥ 0.3.0)..."
  curl -fsSL https://raw.githubusercontent.com/DITlieD/lia-trust/main/install.sh | bash || {
    echo "WARN: LIA install script failed (network or remote). See docs/LIA-TRUST.md"
  }
  if command -v lia >/dev/null 2>&1; then
    echo -n "lia --version: "
    lia --version || true
    echo "Next: lia doctor && lia status"
    echo "If needed: lia install --apply-live"
  else
    echo "WARN: lia not on PATH after install; open a new shell or check install docs."
  fi
fi
# Optional official Unity CLI binary (Bucket C companion — NOT Editor install)
# Default: print install guidance only. With --assume-yes: run official CLI installer only.
# Never runs `unity install <editor-version>` (multi-GB).
if [[ $WITH_UNITY_CLI -eq 1 ]]; then
  UNITY_CLI_INSTALL_SH='https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh'
  echo "=== Official Unity CLI (optional companion) ==="
  echo "MCP alone is enough for the live Editor agent loop; CLI is not required."
  echo "Install docs: docs/UNITY-CLI.md"
  if command -v unity >/dev/null 2>&1; then
    echo -n "unity already on PATH: "
    unity --version 2>&1 | head -1 || true
  elif [[ $ASSUME_YES -eq 1 ]]; then
    echo "Installing standalone Unity CLI binary (UNITY_CLI_CHANNEL=beta)..."
    echo "This does NOT download Unity Editor versions."
    if [[ "$(uname -s)" == "Darwin" ]] || [[ "$(uname -s)" == "Linux" ]]; then
      curl -fsSL "$UNITY_CLI_INSTALL_SH" | UNITY_CLI_CHANNEL=beta bash || {
        echo "WARN: Unity CLI install script failed (network or remote). See docs/UNITY-CLI.md"
      }
    else
      echo "Non-Linux/macOS host: use PowerShell install from docs/UNITY-CLI.md"
      echo "  \$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex"
    fi
    if command -v unity >/dev/null 2>&1; then
      echo -n "unity --version: "
      unity --version 2>&1 | head -1 || true
    else
      echo "WARN: unity not on PATH after install; reopen shell or add CLI install dir to PATH."
    fi
  else
    echo "Print-only (pass --assume-yes with --with-unity-cli to run the CLI binary installer):"
    echo "  curl -fsSL $UNITY_CLI_INSTALL_SH | UNITY_CLI_CHANNEL=beta bash"
    echo "Windows (PowerShell):"
    echo "  \$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex"
    echo "Never auto-run: unity install <editor-version>  # multi-GB; human confirm"
  fi
  echo "=============================================="
fi
if command -v grok >/dev/null 2>&1; then
  grok plugin install "$ROOT/plugin" --trust || true
fi
bash "$ROOT/scripts/doctor.sh" || true
