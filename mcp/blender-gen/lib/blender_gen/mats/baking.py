"""Map packing + diagnostic renders (pure numpy/pillow, no Cycles required)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def force_tile_edges(arr: np.ndarray, band: int = 2) -> np.ndarray:
    """Make left/right and top/bottom edge bands identical (seamless tiling)."""
    a = np.array(arr, copy=True)
    b = max(1, min(band, a.shape[0] // 4, a.shape[1] // 4))
    a[:, -b:] = a[:, :b]
    a[-b:, :] = a[:b, :]
    return a


def save_map(path: Path, arr: np.ndarray, *, mode: str = "RGB", tileable: bool = True) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    a = np.clip(arr, 0.0, 1.0)
    if a.ndim == 2:
        a = np.stack([a, a, a], axis=-1)
    if a.shape[-1] == 1:
        a = np.repeat(a, 3, axis=-1)
    if tileable and path.stem not in ("3x3_tiling", "grazing", "preview"):
        a = force_tile_edges(a, band=2)
    img = Image.fromarray((a * 255.0).astype(np.uint8), mode="RGB")
    if mode == "L":
        img = img.convert("L")
    img.save(path)


def normal_from_height(height: np.ndarray, strength: float = 4.0) -> np.ndarray:
    """OpenGL normal map from height (tileable sobel)."""
    h = height.astype(np.float64)
    # Enforce exact wrap on height before derivatives (kills PNG-edge drift later)
    h[0, :] = h[-1, :] = 0.5 * (h[0, :] + h[-1, :])
    h[:, 0] = h[:, -1] = 0.5 * (h[:, 0] + h[:, -1])
    # tileable gradients
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(h)
    length = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-8
    nx, ny, nz = nx / length, ny / length, nz / length
    # encode 0..1 OpenGL
    out = np.stack([(nx + 1) * 0.5, (ny + 1) * 0.5, (nz + 1) * 0.5], axis=-1)
    # force seam identity (normal maps amplify tiny height diffs)
    out[0, :] = out[-1, :] = 0.5 * (out[0, :] + out[-1, :])
    out[:, 0] = out[:, -1] = 0.5 * (out[:, 0] + out[:, -1])
    return out.astype(np.float32)


def make_tiling_preview(basecolor: np.ndarray, tiles: int = 3) -> np.ndarray:
    return np.tile(basecolor, (tiles, tiles, 1) if basecolor.ndim == 3 else (tiles, tiles))


def make_grazing_preview(basecolor: np.ndarray, height: np.ndarray) -> np.ndarray:
    """Fake grazing light: darken by height gradient along X."""
    h = height.astype(np.float64)
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    shade = np.clip(0.55 + dx * 3.0, 0.2, 1.2)
    if basecolor.ndim == 2:
        return np.clip(basecolor * shade, 0, 1).astype(np.float32)
    return np.clip(basecolor * shade[..., None], 0, 1).astype(np.float32)


def pack_orm(ao: np.ndarray, roughness: np.ndarray, metallic: np.ndarray) -> np.ndarray:
    """Unity/HDRP-ish ORM: R=AO G=Roughness B=Metallic."""
    def _ch(a: np.ndarray) -> np.ndarray:
        if a.ndim == 3:
            return a[..., 0]
        return a

    return np.stack([_ch(ao), _ch(roughness), _ch(metallic)], axis=-1).astype(np.float32)
