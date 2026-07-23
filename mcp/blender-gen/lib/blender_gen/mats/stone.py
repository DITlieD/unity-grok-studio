"""Stone material on brick chassis."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..manifest import write_manifest
from ..paths import material_dir
from .baking import make_grazing_preview, make_tiling_preview, normal_from_height, save_map
from .masks import tileable_value_noise


def gen_stone_material(
    game_slug: str = "default",
    seed: int = 184,
    *,
    size: int = 2048,
    base_color: tuple[float, float, float] = (0.55, 0.52, 0.48),
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    out = Path(out_dir) if out_dir else material_dir(game_slug, "stone", seed)
    out.mkdir(parents=True, exist_ok=True)
    n1 = tileable_value_noise(size, seed, scale=6.0, octaves=5, salt="stone1")
    n2 = tileable_value_noise(size, seed, scale=24.0, octaves=4, salt="stone2")
    height = np.clip(0.4 + 0.4 * n1 + 0.2 * n2, 0, 1).astype(np.float32)
    col = np.array(base_color, dtype=np.float32)
    base = np.clip(col * (0.75 + 0.4 * n1[..., None] + 0.1 * n2[..., None]), 0, 1).astype(
        np.float32
    )
    rough = np.clip(0.65 + 0.25 * n2, 0, 1).astype(np.float32)
    ao = np.clip(0.5 + 0.5 * height, 0, 1).astype(np.float32)
    metallic = np.zeros((size, size), dtype=np.float32)
    normal = normal_from_height(height, strength=5.0)
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
    write_manifest(out, seed=seed, kind="stone_material", params=params, files=files)
    files.append("manifest.json")
    return {"status": "ok", "out_dir": str(out), "seed": seed, "files": files, "params": params}
