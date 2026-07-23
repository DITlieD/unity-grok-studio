"""Output path contract for blender-gen (standalone unity-grok-studio)."""
from __future__ import annotations

import os
from pathlib import Path

def _package_root() -> Path:
    env = os.environ.get("UNITY_GROK_ROOT")
    if env: return Path(env).resolve()
    # mcp/blender-gen/lib/blender_gen/paths.py -> repo root is parents[4]
    return Path(__file__).resolve().parents[4]

def workspace_root() -> Path:
    """Prefer UNITY_PROJECT, else CWD."""
    up = os.environ.get("UNITY_PROJECT") or os.environ.get("UNITY_PROJECT_ROOT")
    if up: return Path(up).resolve()
    return Path(os.environ.get("CWD", os.getcwd())).resolve()

def generated_root(game_slug: str | None = None) -> Path:
    """$UNITY_PROJECT/Assets/Generated or $CWD/Generated."""
    ws = workspace_root()
    assets = ws / "Assets"
    if assets.is_dir():
        base = assets / "Generated"
    else:
        base = ws / "Generated"
    if game_slug:
        base = base / game_slug
    return base

def material_dir(game_slug: str, kind: str, seed: int) -> Path:
    return generated_root(game_slug) / "materials" / f"{kind}_{seed}"

def mesh_dir(game_slug: str, kind: str, seed: int) -> Path:
    return generated_root(game_slug) / "meshes" / f"{kind}_{seed}"

def style_path(game_slug: str) -> Path:
    # Optional style YAML next to project or package config
    candidates = [
        workspace_root() / "asset-style.yaml",
        workspace_root() / "Assets" / "asset-style.yaml",
        _package_root() / "config" / "asset-style.yaml",
    ]
    for c in candidates:
        if c.is_file(): return c
    return candidates[0]

# Back-compat aliases
def project_root(game_slug: str) -> Path:
    return workspace_root()

WORK_GAMES = _package_root()  # legacy name; not a games monorepo
