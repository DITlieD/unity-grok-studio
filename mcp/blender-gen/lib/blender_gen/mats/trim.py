"""Trim / border material generator."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..manifest import write_manifest
from ..paths import material_dir
from .baking import make_grazing_preview, make_tiling_preview, normal_from_height, save_map
from .masks import tileable_value_noise


def gen_trim_material(
    game_slug: str = "default",
    seed: int = 184,
    *,
    size: int = 2048,
    base_color: tuple[float, float, float] = (0.48, 0.42, 0.32),
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    out = Path(out_dir) if out_dir else material_dir(game_slug, "trim", seed)
    out.mkdir(parents=True, exist_ok=True)
    n = tileable_value_noise(size, seed, scale=12.0, octaves=3, salt="trim")
    yy, xx = np.mgrid[0:size, 0:size]
    u = xx / size
    # vertical trim bands
    band = (np.abs(((u * 4.0) % 1.0) - 0.5) < 0.12).astype(np.float32)
    height = np.clip(0.4 + 0.35 * band + 0.15 * n, 0, 1).astype(np.float32)
    col = np.array(base_color, dtype=np.float32)
    accent = np.array([0.7, 0.6, 0.35], dtype=np.float32)
    base = np.where(band[..., None] > 0.5, accent, col) * (0.9 + 0.15 * n[..., None])
    base = np.clip(base, 0, 1).astype(np.float32)
    rough = np.clip(0.5 + 0.3 * n - 0.1 * band, 0, 1).astype(np.float32)
    ao = np.clip(0.55 + 0.45 * height, 0, 1).astype(np.float32)
    metallic = (0.15 * band).astype(np.float32)
    normal = normal_from_height(height, strength=4.0)
    files = []
    for name, arr in [
        ("basecolor.png", base),
        ("normal.png", normal),
        ("roughness.png", rough),
        ("ao.png", ao),
        ("height.png", height),
        ("metallic.png", metallic),
    ]:
        save_map(out / name, arr)
        files.append(name)
    save_map(out / "3x3_tiling.png", make_tiling_preview(base))
    files.append("3x3_tiling.png")
    save_map(out / "grazing.png", make_grazing_preview(base, height))
    files.append("grazing.png")
    params = {"game_slug": game_slug, "size": size, "base_color": list(base_color)}
    write_manifest(out, seed=seed, kind="trim_material", params=params, files=files)
    files.append("manifest.json")
    return {"status": "ok", "out_dir": str(out), "seed": seed, "files": files, "params": params}
