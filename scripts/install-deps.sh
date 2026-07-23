#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WITH_BLENDER=0; ASSUME_YES=0
for a in "$@"; do
  case "$a" in --with-blender) WITH_BLENDER=1;; --assume-yes|-y) ASSUME_YES=1;; esac
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
      else echo "No snap/brew; install Blender 5.x manually"; fi
    else
      echo "Pass --assume-yes with --with-blender to auto-install, or install Blender manually."
    fi
  fi
fi
if command -v grok >/dev/null 2>&1; then
  grok plugin install "$ROOT/plugin" --trust || true
fi
bash "$ROOT/scripts/doctor.sh" || true
