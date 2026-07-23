"""Metal material generator."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..manifest import write_manifest
from ..paths import material_dir
from .baking import make_grazing_preview, make_tiling_preview, normal_from_height, save_map
from .masks import tileable_value_noise


def gen_metal_material(
    game_slug: str = "embervow",
    seed: int = 184,
    *,
    size: int = 2048,
    base_color: tuple[float, float, float] = (0.72, 0.72, 0.74),
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    out = Path(out_dir) if out_dir else material_dir(game_slug, "metal", seed)
    out.mkdir(parents=True, exist_ok=True)
    n = tileable_value_noise(size, seed, scale=20.0, octaves=4, salt="metal")
    scratches = tileable_value_noise(size, seed, scale=64.0, octaves=2, salt="metal_s")
    height = np.clip(0.5 + 0.1 * n - 0.05 * (scratches > 0.75), 0, 1).astype(np.float32)
    col = np.array(base_color, dtype=np.float32)
    base = np.clip(col * (0.9 + 0.15 * n[..., None]), 0, 1).astype(np.float32)
    rough = np.clip(0.25 + 0.35 * n + 0.2 * (scratches > 0.7), 0, 1).astype(np.float32)
    ao = np.clip(0.85 + 0.15 * height, 0, 1).astype(np.float32)
    metallic = np.clip(0.9 + 0.1 * n, 0, 1).astype(np.float32)
    normal = normal_from_height(height, strength=2.5)
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
    write_manifest(out, seed=seed, kind="metal_material", params=params, files=files)
    files.append("manifest.json")
    return {"status": "ok", "out_dir": str(out), "seed": seed, "files": files, "params": params}
