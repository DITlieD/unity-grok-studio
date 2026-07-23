"""Wood material generator."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ..manifest import write_manifest
from ..paths import material_dir
from .baking import make_grazing_preview, make_tiling_preview, normal_from_height, save_map
from .masks import tileable_value_noise


def gen_wood_material(
    game_slug: str = "default",
    seed: int = 184,
    *,
    size: int = 2048,
    base_color: tuple[float, float, float] = (0.42, 0.28, 0.16),
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    out = Path(out_dir) if out_dir else material_dir(game_slug, "wood", seed)
    out.mkdir(parents=True, exist_ok=True)
    n = tileable_value_noise(size, seed, scale=4.0, octaves=4, salt="wood")
    yy = np.linspace(0, 1, size, endpoint=False)[:, None]
    grain = 0.5 + 0.5 * np.sin((yy * 40.0 + n * 3.0) * 2 * np.pi)
    grain = grain.astype(np.float32)
    # tileable along X already; Y is continuous in sin of fractional yy with noise wrap via n
    height = np.clip(0.5 + 0.2 * grain + 0.15 * n, 0, 1).astype(np.float32)
    col = np.array(base_color, dtype=np.float32)
    base = np.clip(col * (0.7 + 0.5 * grain[..., None]), 0, 1).astype(np.float32)
    rough = np.clip(0.55 + 0.3 * (1 - grain) + 0.1 * n, 0, 1).astype(np.float32)
    ao = np.clip(0.6 + 0.4 * height, 0, 1).astype(np.float32)
    metallic = np.zeros((size, size), dtype=np.float32)
    normal = normal_from_height(height, strength=3.5)
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
    write_manifest(out, seed=seed, kind="wood_material", params=params, files=files)
    files.append("manifest.json")
    return {"status": "ok", "out_dir": str(out), "seed": seed, "files": files, "params": params}
