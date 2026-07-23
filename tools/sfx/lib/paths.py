"""SFX_LIB path resolution and quarantine guards."""
from __future__ import annotations

import os
from pathlib import Path

def _package_root() -> Path:
    env = os.environ.get("UNITY_GROK_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    # tools/sfx/lib/paths.py -> repo root parents[3]
    return Path(__file__).resolve().parents[3]

def default_sfx_lib() -> Path:
    env = os.environ.get("SFX_LIB")
    if env:
        return Path(env).expanduser().resolve()
    return (_package_root() / "sfx_library").resolve()

def resolve_sfx_lib(override: str | Path | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    return default_sfx_lib()

def is_quarantine_path(path: Path | str, sfx_lib: Path | None = None) -> bool:
    p = Path(path).resolve()
    lib = sfx_lib or default_sfx_lib()
    try:
        rel = p.relative_to(lib.resolve())
    except ValueError:
        return "quarantine" in p.parts
    return bool(rel.parts and rel.parts[0] == "quarantine")

def allowed_source_roots(sfx_lib: Path | None = None) -> list[Path]:
    lib = sfx_lib or default_sfx_lib()
    tools = Path(__file__).resolve().parents[1]
    return [
        lib / "seed",
        lib / "sources",
        lib / "freesound",
        lib / "generated",
        lib / "staging",
        lib / "uncategorized",
        lib / "searchable",
        tools / "_fixtures",
    ]

def path_is_allowed_source(path: Path | str, sfx_lib: Path | None = None) -> bool:
    p = Path(path).resolve()
    if is_quarantine_path(p, sfx_lib):
        return False
    for root in allowed_source_roots(sfx_lib):
        try:
            p.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    lib = (sfx_lib or default_sfx_lib()).resolve()
    try:
        rel = p.relative_to(lib)
        return not (rel.parts and rel.parts[0] == "quarantine")
    except ValueError:
        return False
