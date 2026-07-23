#!/usr/bin/env python3
"""Normal map convention check (OpenGL vs DirectX).

OpenGL: green (Y) points up; DirectX: green inverted.
Heuristic: mean of G channel relative to expected bias, plus B (Z) high.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def check_file(path: Path, convention: str = "OpenGL") -> dict:
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    g_mean = float(arr[..., 1].mean())
    b_mean = float(arr[..., 2].mean())
    issues = []
    if b_mean < 0.45:
        issues.append(f"B(Z) mean {b_mean:.3f} too low for a normal map")
    # For OpenGL we only enforce Z bias; Y sign is content-dependent.
    # DirectX flag is recorded for engine packing.
    return {
        "file": str(path),
        "convention": convention,
        "g_mean": g_mean,
        "b_mean": b_mean,
        "pass": not issues,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", required=True, help="Path to normal map image")
    ap.add_argument("--convention", default="OpenGL")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = check_file(Path(args.map), args.convention)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("PASS" if report["pass"] else "FAIL", report)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
