"""Arch / bridge piece generator."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..paths import mesh_dir
from .export import write_mesh_package
from .walls import _box


def gen_arch(
    game_slug: str = "default",
    seed: int = 184,
    *,
    width: float = 4.0,
    height: float = 3.0,
    depth: float = 1.0,
    segments: int = 12,
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    out = Path(out_dir) if out_dir else mesh_dir(game_slug, "arch", seed)
    all_v, all_i = [], []
    offset = 0
    # two pillars
    for px in (-width / 2 + 0.3, width / 2 - 0.3):
        v, i = _box(px, height / 2, 0, 0.5, height, depth)
        all_v.append(v)
        all_i.append(i + offset)
        offset += len(v)
    # arch voussoirs as boxes along semicircle
    r = width / 2 - 0.2
    for s in range(segments):
        t0 = np.pi * s / segments
        t1 = np.pi * (s + 1) / segments
        tm = 0.5 * (t0 + t1)
        cx = r * np.cos(tm)
        cy = height * 0.55 + r * 0.55 * np.sin(tm)
        v, i = _box(float(cx), float(cy), 0, 0.45, 0.35, depth * 0.9)
        all_v.append(v)
        all_i.append(i + offset)
        offset += len(v)
    # deck
    v, i = _box(0, height + 0.15, 0, width + 0.4, 0.3, depth + 0.2)
    all_v.append(v)
    all_i.append(i + offset)
    positions = np.vstack(all_v)
    indices = np.concatenate(all_i)
    params = {
        "game_slug": game_slug,
        "width": width,
        "height": height,
        "depth": depth,
        "segments": segments,
    }
    return write_mesh_package(
        out, kind="arch", seed=seed, positions=positions, indices=indices, params=params
    )
