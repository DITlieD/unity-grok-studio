"""blender_gen SDK — seeded, deterministic material + mesh generators.

Runs inside Blender when available; pure-Python procedural path for maps and
simple meshes so unit tests drive real generators without a live GUI.
"""
from __future__ import annotations

__version__ = "0.1.0"


def version_info() -> dict:
    return {"name": "blender_gen", "version": __version__}
