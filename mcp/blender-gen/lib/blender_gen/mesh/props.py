"""Prop generators (crate)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..paths import mesh_dir
from .export import write_mesh_package
from .walls import _box


def gen_crate(
    game_slug: str = "embervow",
    seed: int = 184,
    *,
    size: float = 1.0,
    plank_count: int = 4,
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    out = Path(out_dir) if out_dir else mesh_dir(game_slug, "crate", seed)
    s = size
    all_v, all_i = [], []
    offset = 0
    # outer shell as single box
    v, i = _box(0, s / 2, 0, s, s, s)
    all_v.append(v)
    all_i.append(i + offset)
    offset += len(v)
    # lid lip
    v, i = _box(0, s + 0.02, 0, s * 1.02, 0.04, s * 1.02)
    all_v.append(v)
    all_i.append(i + offset)
    offset += len(v)
    # reinforcing bands
    for t in (-s * 0.35, s * 0.35):
        v, i = _box(0, s / 2, t, s * 1.01, s * 0.08, 0.04)
        all_v.append(v)
        all_i.append(i + offset)
        offset += len(v)
    positions = np.vstack(all_v)
    indices = np.concatenate(all_i)
    params = {
        "game_slug": game_slug,
        "size": size,
        "plank_count": plank_count,
    }
    return write_mesh_package(
        out,
        kind="crate",
        seed=seed,
        positions=positions,
        indices=indices,
        params=params,
    )
