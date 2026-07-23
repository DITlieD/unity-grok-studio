#!/usr/bin/env python3
"""Tile boundary seam check for PBR map directories.

Compares left/right and top/bottom edge strips of tileable maps. Exit 0 on pass,
non-zero on fail. JSON summary with --json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# maps that should tile (exclude non-tile diagnostics)
DEFAULT_MAPS = (
    "basecolor",
    "albedo",
    "diffuse",
    "normal",
    "roughness",
    "ao",
    "height",
    "metallic",
    "orm",
    "id",
)


def _load_rgb(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    return np.asarray(img, dtype=np.float32) / 255.0


def edge_diff(arr: np.ndarray, band: int = 2) -> dict[str, float]:
    h, w = arr.shape[:2]
    band = max(1, min(band, h // 4, w // 4))
    left = arr[:, :band]
    right = arr[:, -band:]
    top = arr[:band, :]
    bottom = arr[-band:, :]
    # wrap: left should match right when tiled
    lr = float(np.mean(np.abs(left - right)))
    tb = float(np.mean(np.abs(top - bottom)))
    return {"left_right_mae": lr, "top_bottom_mae": tb, "band": band}


def check_dir(
    maps_dir: Path,
    threshold: float = 0.08,
    band: int = 2,
) -> dict:
    maps_dir = Path(maps_dir)
    results = []
    worst = 0.0
    for p in sorted(maps_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".tga", ".exr"):
            continue
        stem = p.stem.lower()
        if not any(k in stem for k in DEFAULT_MAPS):
            continue
        if any(x in stem for x in ("tiling", "grazing", "preview", "render", "3x3")):
            continue
        try:
            arr = _load_rgb(p)
        except Exception as exc:
            results.append({"file": p.name, "error": str(exc), "pass": False})
            worst = 1.0
            continue
        d = edge_diff(arr, band=band)
        score = max(d["left_right_mae"], d["top_bottom_mae"])
        worst = max(worst, score)
        ok = score <= threshold
        results.append({"file": p.name, **d, "score": score, "pass": ok})
    overall = bool(results) and all(r.get("pass") for r in results)
    return {
        "dir": str(maps_dir),
        "threshold": threshold,
        "worst_score": worst,
        "pass": overall,
        "maps": results,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--maps", required=True, help="Directory of map PNGs")
    ap.add_argument("--threshold", type=float, default=0.08)
    ap.add_argument("--band", type=int, default=2)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = check_dir(Path(args.maps), threshold=args.threshold, band=args.band)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        status = "PASS" if report["pass"] else "FAIL"
        print(f"{status} worst={report['worst_score']:.4f} maps={len(report['maps'])}")
        for m in report["maps"]:
            print(f"  {'ok' if m.get('pass') else 'BAD'} {m.get('file')} score={m.get('score', m.get('error'))}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
