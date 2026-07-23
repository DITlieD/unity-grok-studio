"""Parametric wall mesh generator (boolean-free brick placement)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..paths import mesh_dir
from ..rng import make_rng
from .export import write_mesh_package


def _box(cx, cy, cz, sx, sy, sz):
    """Axis-aligned box with SHARED 8 vertices (one connected component)."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    # 8 corners — shared across faces so topology inspect sees one component
    verts = np.array(
        [
            [cx - hx, cy - hy, cz - hz],  # 0
            [cx + hx, cy - hy, cz - hz],  # 1
            [cx + hx, cy + hy, cz - hz],  # 2
            [cx - hx, cy + hy, cz - hz],  # 3
            [cx - hx, cy - hy, cz + hz],  # 4
            [cx + hx, cy - hy, cz + hz],  # 5
            [cx + hx, cy + hy, cz + hz],  # 6
            [cx - hx, cy + hy, cz + hz],  # 7
        ],
        dtype=np.float32,
    )
    # 12 triangles (2 per face), outward-ish winding
    idx = np.array(
        [
            0, 2, 1, 0, 3, 2,  # -Z
            4, 5, 6, 4, 6, 7,  # +Z
            0, 1, 5, 0, 5, 4,  # -Y
            2, 3, 7, 2, 7, 6,  # +Y
            0, 4, 7, 0, 7, 3,  # -X
            1, 2, 6, 1, 6, 5,  # +X
        ],
        dtype=np.uint32,
    )
    return verts, idx


def gen_parametric_wall(
    game_slug: str = "embervow",
    seed: int = 184,
    *,
    length: float = 12.0,
    height: float = 4.0,
    depth: float = 0.5,
    course_h: float = 0.3,
    brick_w: float = 0.5,
    variation: float = 0.05,
    stagger: float = 0.5,
    gate: dict | None = None,
    buttresses: bool = False,
    battlements: bool = False,
    damage: float = 0.0,
    out_dir: Path | str | None = None,
    seed_defect_detached: bool = False,
) -> dict[str, Any]:
    """Generate a wall as instanced brick boxes (no booleans).

    gate: optional {w, h, arch:bool}
    seed_defect_detached: if True, add a floating brick (for validator fail proof).
    """
    rng = make_rng(seed, "wall")
    out = Path(out_dir) if out_dir else mesh_dir(game_slug, "wall", seed)
    all_v = []
    all_i = []
    offset = 0
    rows = max(1, int(height / course_h))
    gate = gate or {}
    gw = float(gate.get("w", 0) or 0)
    gh = float(gate.get("h", 0) or 0)
    gate_on = gw > 0 and gh > 0
    gx0, gx1 = length / 2 - gw / 2, length / 2 + gw / 2

    for r in range(rows):
        y = r * course_h + course_h / 2
        xoff = stagger * brick_w if (r % 2) else 0.0
        x = xoff
        while x < length:
            bw = brick_w * (1.0 + rng.uniform(-variation, variation))
            bh = course_h * 0.95
            bd = depth * (1.0 + rng.uniform(-variation * 0.5, variation * 0.5))
            cx = x + bw / 2
            # skip bricks in gate opening
            if gate_on and y < gh and gx0 < cx < gx1:
                x += bw
                continue
            if damage > 0 and rng.random() < damage * 0.15:
                x += bw
                continue
            v, i = _box(cx, y, 0.0, bw, bh, bd)
            all_v.append(v)
            all_i.append(i + offset)
            offset += len(v)
            x += bw

    if buttresses:
        for bx in (0.3, length - 0.3):
            v, i = _box(bx, height / 2, depth * 0.6, 0.35, height, depth * 0.8)
            all_v.append(v)
            all_i.append(i + offset)
            offset += len(v)

    if battlements:
        n = max(2, int(length / 0.8))
        for k in range(n):
            if k % 2 == 0:
                continue
            cx = (k + 0.5) * length / n
            v, i = _box(cx, height + 0.2, 0.0, 0.35, 0.4, depth)
            all_v.append(v)
            all_i.append(i + offset)
            offset += len(v)

    if seed_defect_detached:
        # floating brick far above wall — topology inspect must report floating_components>=1
        v, i = _box(length / 2, height + 5.0, 0.0, 0.4, 0.25, 0.3)
        all_v.append(v)
        all_i.append(i + offset)
        offset += len(v)

    if not all_v:
        v, i = _box(length / 2, height / 2, 0, length, height, depth)
        all_v = [v]
        all_i = [i]

    positions = np.vstack(all_v)
    indices = np.concatenate(all_i)
    params = {
        "game_slug": game_slug,
        "length": length,
        "height": height,
        "depth": depth,
        "course_h": course_h,
        "brick_w": brick_w,
        "variation": variation,
        "stagger": stagger,
        "gate": gate,
        "buttresses": buttresses,
        "battlements": battlements,
        "damage": damage,
        "seed_defect_detached": seed_defect_detached,
    }
    # topology is measured inside write_mesh_package/mesh_stats — no self-certified flags
    return write_mesh_package(
        out,
        kind="wall",
        seed=seed,
        positions=positions,
        indices=indices,
        params=params,
    )
