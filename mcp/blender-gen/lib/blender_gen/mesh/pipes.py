"""Pipe run generator."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..paths import mesh_dir
from .export import write_mesh_package


def _cyl(ax0, ax1, radius: float, segs: int = 8):
    """Cylinder between two points."""
    a = np.asarray(ax0, dtype=np.float64)
    b = np.asarray(ax1, dtype=np.float64)
    axis = b - a
    length = float(np.linalg.norm(axis)) + 1e-8
    axis = axis / length
    # orthonormal basis
    tmp = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(axis, tmp)
    u /= np.linalg.norm(u) + 1e-8
    v = np.cross(axis, u)
    verts = []
    idx = []
    for i in range(segs):
        t = 2 * np.pi * i / segs
        off = radius * (np.cos(t) * u + np.sin(t) * v)
        verts.append(a + off)
        verts.append(b + off)
    verts = np.array(verts, dtype=np.float32)
    for i in range(segs):
        i0 = 2 * i
        i1 = 2 * ((i + 1) % segs)
        # quad as two tris
        idx.extend([i0, i1, i0 + 1, i1, i1 + 1, i0 + 1])
    return verts, np.array(idx, dtype=np.uint32)


def gen_pipes(
    game_slug: str = "embervow",
    seed: int = 184,
    *,
    length: float = 4.0,
    radius: float = 0.12,
    bends: int = 1,
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    out = Path(out_dir) if out_dir else mesh_dir(game_slug, "pipes", seed)
    pts = [np.array([0.0, 0.5, 0.0])]
    pts.append(np.array([length / 2, 0.5, 0.0]))
    if bends:
        pts.append(np.array([length / 2, 0.5 + 1.0, 0.0]))
        pts.append(np.array([length, 0.5 + 1.0, 0.0]))
    else:
        pts.append(np.array([length, 0.5, 0.0]))
    all_v, all_i = [], []
    offset = 0
    for a, b in zip(pts, pts[1:]):
        v, i = _cyl(a, b, radius)
        all_v.append(v)
        all_i.append(i + offset)
        offset += len(v)
    positions = np.vstack(all_v)
    indices = np.concatenate(all_i)
    params = {
        "game_slug": game_slug,
        "length": length,
        "radius": radius,
        "bends": bends,
    }
    return write_mesh_package(
        out, kind="pipes", seed=seed, positions=positions, indices=indices, params=params
    )
