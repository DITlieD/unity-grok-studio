#!/usr/bin/env python3
"""Measured mortar-depth check from height (or id) maps — not manifest params.

Brick generators put mortar in low-height bands. Deep mortar ⇒ high fraction of
low-height pixels. Exit non-zero when mortar_fraction exceeds --max-fraction.

This fails a wrong implementation that only rewrites manifest.mortar while maps
stay deep (or that bakes deep joints regardless of params).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def measure_mortar_fraction(
    maps_dir: Path,
    *,
    height_threshold: float = 0.40,
) -> dict:
    maps_dir = Path(maps_dir)
    height_path = None
    for name in ("height.png", "Height.png", "height.jpg"):
        p = maps_dir / name
        if p.exists():
            height_path = p
            break
    if height_path is None:
        # try any *height*
        cands = list(maps_dir.glob("*height*"))
        height_path = cands[0] if cands else None
    if height_path is None:
        return {
            "pass": False,
            "error": "no height map found",
            "mortar_fraction": None,
        }
    arr = np.asarray(Image.open(height_path).convert("L"), dtype=np.float32) / 255.0
    frac = float((arr < height_threshold).mean())
    return {
        "height_map": str(height_path),
        "height_threshold": height_threshold,
        "mortar_fraction": frac,
        "mean_height": float(arr.mean()),
        "pass": None,  # filled by caller with max
    }


def check_dir(
    maps_dir: Path,
    *,
    max_fraction: float = 0.30,
    height_threshold: float = 0.40,
) -> dict:
    m = measure_mortar_fraction(maps_dir, height_threshold=height_threshold)
    if m.get("error"):
        m["pass"] = False
        m["max_fraction"] = max_fraction
        return m
    frac = float(m["mortar_fraction"])
    ok = frac <= max_fraction
    m["pass"] = ok
    m["max_fraction"] = max_fraction
    if not ok:
        m["issues"] = [f"mortar_fraction={frac:.4f} > max={max_fraction}"]
    else:
        m["issues"] = []
    return m


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--maps", required=True)
    ap.add_argument("--max-fraction", type=float, default=0.30)
    ap.add_argument("--height-threshold", type=float, default=0.40)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = check_dir(
        Path(args.maps),
        max_fraction=args.max_fraction,
        height_threshold=args.height_threshold,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("PASS" if report.get("pass") else "FAIL", report)
    return 0 if report.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
