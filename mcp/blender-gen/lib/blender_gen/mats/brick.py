"""Brick material generator — deterministic tileable PBR maps."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..manifest import write_manifest
from ..paths import material_dir
from .baking import (
    make_grazing_preview,
    make_tiling_preview,
    normal_from_height,
    save_map,
)
from .masks import brick_mask, tileable_value_noise


def gen_brick_material(
    game_slug: str = "default",
    seed: int = 184,
    *,
    size: int = 2048,
    rows: int = 8,
    brick_w: float = 0.22,
    brick_h: float = 0.10,
    mortar: float = 0.02,
    stagger: float = 0.5,
    variation: float = 0.15,
    brick_color: tuple[float, float, float] = (0.62, 0.38, 0.28),
    mortar_color: tuple[float, float, float] = (0.55, 0.52, 0.48),
    final: bool = False,
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Generate brick PBR set under Assets/Generated/materials/brick_{seed}/.

    Metallic hard 0. Deterministic for the same seed+params.
    """
    if final and size < 4096:
        size = 4096
    out = Path(out_dir) if out_dir else material_dir(game_slug, "brick", seed)
    out.mkdir(parents=True, exist_ok=True)

    brick_id, mortar_m, height = brick_mask(
        size,
        seed,
        rows=rows,
        brick_w=brick_w,
        brick_h=brick_h,
        mortar=mortar,
        stagger=stagger,
        variation=variation,
    )
    nse = tileable_value_noise(size, seed, scale=16.0, octaves=5, salt="brick_n")
    fine = tileable_value_noise(size, seed, scale=48.0, octaves=3, salt="brick_f")

    # chips / cracks via noise threshold on bricks only
    chip = ((nse > 0.82) & (mortar_m < 0.5)).astype(np.float32)
    height = height - 0.12 * chip - 0.05 * fine * (1.0 - mortar_m)
    height = np.clip(height, 0.0, 1.0).astype(np.float32)

    bc = np.array(brick_color, dtype=np.float32)
    mc = np.array(mortar_color, dtype=np.float32)
    # per-brick tint
    tint = 0.85 + 0.3 * ((np.sin(brick_id * 7.1 + seed) * 0.5 + 0.5))
    base = bc * tint[..., None] * (0.9 + 0.15 * nse[..., None])
    base = np.where(mortar_m[..., None] > 0.5, mc * (0.95 + 0.1 * fine[..., None]), base)
    base = np.clip(base, 0, 1).astype(np.float32)

    rough = np.where(mortar_m > 0.5, 0.85 + 0.1 * fine, 0.70 + 0.15 * nse).astype(np.float32)
    ao = np.clip(0.55 + 0.45 * height - 0.15 * mortar_m, 0, 1).astype(np.float32)
    metallic = np.zeros((size, size), dtype=np.float32)
    normal = normal_from_height(height, strength=6.0)
    # ID map visualization
    id_vis = np.stack(
        [
            (brick_id * 0.17) % 1.0,
            (brick_id * 0.31) % 1.0,
            (brick_id * 0.47) % 1.0,
        ],
        axis=-1,
    ).astype(np.float32)
    id_vis = np.where(mortar_m[..., None] > 0.5, 0.05, id_vis)

    files = []
    for name, arr in [
        ("basecolor.png", base),
        ("normal.png", normal),
        ("roughness.png", rough),
        ("ao.png", ao),
        ("height.png", height),
        ("id.png", id_vis),
        ("metallic.png", metallic),
    ]:
        save_map(out / name, arr)
        files.append(name)

    tiling = make_tiling_preview(base, 3)
    save_map(out / "3x3_tiling.png", tiling)
    files.append("3x3_tiling.png")
    grazing = make_grazing_preview(base, height)
    save_map(out / "grazing.png", grazing)
    files.append("grazing.png")

    params = {
        "game_slug": game_slug,
        "size": size,
        "rows": rows,
        "brick_w": brick_w,
        "brick_h": brick_h,
        "mortar": mortar,
        "stagger": stagger,
        "variation": variation,
        "brick_color": list(brick_color),
        "mortar_color": list(mortar_color),
        "final": final,
        "metallic": 0.0,
    }
    write_manifest(out, seed=seed, kind="brick_material", params=params, files=files)
    files.append("manifest.json")
    return {
        "status": "ok",
        "out_dir": str(out),
        "seed": seed,
        "files": files,
        "params": params,
    }
