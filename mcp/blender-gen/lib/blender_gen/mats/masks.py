"""Shared procedural masks (tileable)."""
from __future__ import annotations

import math

import numpy as np

from ..rng import make_rng


def tileable_value_noise(
    size: int,
    seed: int,
    *,
    scale: float = 8.0,
    octaves: int = 4,
    salt: str = "vn",
) -> np.ndarray:
    """Simple tileable multi-octave value noise in [0,1]."""
    rng = make_rng(seed, salt)
    grid_n = max(2, int(scale))
    # lattice on torus (stdlib Random has no shape arg)
    lattice = np.array(
        [[rng.random() for _ in range(grid_n)] for _ in range(grid_n)],
        dtype=np.float64,
    )

    def sample(u: np.ndarray, v: np.ndarray) -> np.ndarray:
        # u,v in [0,1)
        x = u * grid_n
        y = v * grid_n
        x0 = np.floor(x).astype(int) % grid_n
        y0 = np.floor(y).astype(int) % grid_n
        x1 = (x0 + 1) % grid_n
        y1 = (y0 + 1) % grid_n
        fx = x - np.floor(x)
        fy = y - np.floor(y)
        # smoothstep
        sx = fx * fx * (3 - 2 * fx)
        sy = fy * fy * (3 - 2 * fy)
        v00 = lattice[y0, x0]
        v10 = lattice[y0, x1]
        v01 = lattice[y1, x0]
        v11 = lattice[y1, x1]
        a = v00 * (1 - sx) + v10 * sx
        b = v01 * (1 - sx) + v11 * sx
        return a * (1 - sy) + b * sy

    yy, xx = np.mgrid[0:size, 0:size]
    u = xx / size
    v = yy / size
    acc = np.zeros((size, size), dtype=np.float64)
    amp = 1.0
    total = 0.0
    freq = 1.0
    for o in range(octaves):
        acc += amp * sample((u * freq) % 1.0, (v * freq) % 1.0)
        total += amp
        amp *= 0.5
        freq *= 2.0
    acc /= total
    return acc.astype(np.float32)


def brick_mask(
    size: int,
    seed: int,
    *,
    rows: int = 8,
    brick_w: float = 0.22,
    brick_h: float = 0.10,
    mortar: float = 0.02,
    stagger: float = 0.5,
    variation: float = 0.15,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (brick_id, mortar_mask, height_hint) tileable arrays.

    Geometrically tileable: integer courses and columns wrap on the unit square.
    brick_id: int-ish ids per brick (as float)
    mortar_mask: 1 on mortar, 0 on brick
    height_hint: relative height (brick high, mortar low)
    """
    yy, xx = np.mgrid[0:size, 0:size]
    u = xx / float(size)
    v = yy / float(size)

    # Force integer courses so top/bottom edges match when tiled
    n_rows = max(2, int(rows))
    course_h = 1.0 / n_rows
    # columns: choose integer count from brick_w
    n_cols = max(2, int(round(1.0 / max(brick_w + mortar * 0.5, 1e-6))))
    cell_w = 1.0 / n_cols
    # mortar fraction of cell (clamped)
    mortar_frac_u = min(0.45, max(0.02, mortar / max(brick_w + mortar, 1e-6)))
    mortar_frac_v = min(0.45, max(0.02, mortar / max(brick_h + mortar, 1e-6)))

    row = np.floor(v * n_rows).astype(np.int32) % n_rows
    # stagger odd rows by half a brick (wrap-safe)
    offset = np.where((row % 2) == 1, 0.5 * cell_w, 0.0)
    col = np.floor(((u + offset) % 1.0) * n_cols).astype(np.int32) % n_cols

    lu = ((u + offset) % 1.0) * n_cols - col.astype(np.float64)
    # lu in [0,1) within cell
    lv = (v * n_rows) - np.floor(v * n_rows)

    mx = np.minimum(lu, 1.0 - lu)
    my = np.minimum(lv, 1.0 - lv)
    is_mortar = (mx < mortar_frac_u * 0.5) | (my < mortar_frac_v * 0.5)

    brick_id = (row.astype(np.float32) * 97.0 + col.astype(np.float32)) % 10000.0

    # per-brick height variation (hash) — pure function of id+seed (tile-safe)
    hvar = ((np.sin(brick_id * 12.9898 + float(seed)) * 43758.5453) % 1.0).astype(np.float32)
    hvar = np.abs(hvar) * variation

    height = np.where(is_mortar, 0.15 + 0.05 * hvar, 0.75 + 0.25 * hvar).astype(np.float32)
    mortar_mask = is_mortar.astype(np.float32)
    return brick_id.astype(np.float32), mortar_mask, height
