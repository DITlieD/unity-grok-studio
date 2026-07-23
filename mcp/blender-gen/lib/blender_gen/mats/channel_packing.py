"""Engine channel packing helpers."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .baking import pack_orm, save_map


def pack_orm_tool(
    out_dir: Path,
    ao: np.ndarray,
    roughness: np.ndarray,
    metallic: np.ndarray,
    name: str = "orm.png",
) -> Path:
    out = Path(out_dir) / name
    save_map(out, pack_orm(ao, roughness, metallic))
    return out
