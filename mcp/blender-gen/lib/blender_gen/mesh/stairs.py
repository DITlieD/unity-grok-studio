"""Stairs generator."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..paths import mesh_dir
from .export import write_mesh_package
from .walls import _box


def gen_stairs(
    game_slug: str = "embervow",
    seed: int = 184,
    *,
    steps: int = 8,
    step_w: float = 1.2,
    step_h: float = 0.18,
    step_d: float = 0.3,
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    out = Path(out_dir) if out_dir else mesh_dir(game_slug, "stairs", seed)
    all_v, all_i = [], []
    offset = 0
    for s in range(steps):
        cx = 0.0
        cy = (s + 0.5) * step_h
        cz = (s + 0.5) * step_d
        v, i = _box(cx, cy, cz, step_w, step_h, step_d)
        all_v.append(v)
        all_i.append(i + offset)
        offset += len(v)
    positions = np.vstack(all_v)
    indices = np.concatenate(all_i)
    params = {
        "game_slug": game_slug,
        "steps": steps,
        "step_w": step_w,
        "step_h": step_h,
        "step_d": step_d,
    }
    return write_mesh_package(
        out, kind="stairs", seed=seed, positions=positions, indices=indices, params=params
    )
