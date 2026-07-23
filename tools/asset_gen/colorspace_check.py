#!/usr/bin/env python3
"""Colorspace / channel sanity for PBR map sets.

- basecolor: sRGB-looking (not all-flat linear gray extremes only check)
- normal: mostly mid-blue Z (OpenGL: Z in B channel ~0.5..1)
- roughness/ao/height: single-channel-ish grayscale
Exit 0 on pass, non-zero on fail.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def check_normal(arr: np.ndarray) -> tuple[bool, str]:
    b_mean = float(arr[..., 2].mean())
    # OpenGL-style: B (Z) should be biased high
    if b_mean < 0.45:
        return False, f"normal B-mean={b_mean:.3f} too low (expected OpenGL Z-up bias)"
    # not a flat solid color
    if float(arr.std()) < 0.01:
        return False, "normal map nearly constant"
    return True, f"normal B-mean={b_mean:.3f}"


def check_grayscale_map(arr: np.ndarray, name: str) -> tuple[bool, str]:
    # channels nearly equal
    diff = float(np.mean(np.abs(arr[..., 0] - arr[..., 1])) + np.mean(np.abs(arr[..., 1] - arr[..., 2])))
    if diff > 0.05:
        return False, f"{name} not grayscale (chroma mae={diff:.3f})"
    return True, f"{name} grayscale ok"


def check_basecolor(arr: np.ndarray) -> tuple[bool, str]:
    if float(arr.std()) < 0.005:
        return False, "basecolor nearly constant"
    return True, "basecolor variance ok"


def check_dir(maps_dir: Path, engine_normal: str = "OpenGL") -> dict:
    maps_dir = Path(maps_dir)
    results = []
    for p in sorted(maps_dir.iterdir()):
        if p.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        stem = p.stem.lower()
        if any(x in stem for x in ("tiling", "grazing", "preview", "render", "3x3")):
            continue
        try:
            arr = load(p)
        except Exception as exc:
            results.append({"file": p.name, "pass": False, "note": str(exc)})
            continue
        if "normal" in stem:
            ok, note = check_normal(arr)
        elif any(k in stem for k in ("rough", "ao", "height", "metal", "orm")):
            ok, note = check_grayscale_map(arr, stem)
        elif any(k in stem for k in ("basecolor", "albedo", "diffuse", "color")):
            ok, note = check_basecolor(arr)
        else:
            continue
        results.append({"file": p.name, "pass": ok, "note": note})
    overall = bool(results) and all(r["pass"] for r in results)
    return {
        "dir": str(maps_dir),
        "engine_normal": engine_normal,
        "pass": overall,
        "maps": results,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--maps", required=True)
    ap.add_argument("--normal-convention", default="OpenGL")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = check_dir(Path(args.maps), engine_normal=args.normal_convention)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("PASS" if report["pass"] else "FAIL")
        for m in report["maps"]:
            print(f"  {'ok' if m['pass'] else 'BAD'} {m['file']}: {m['note']}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
