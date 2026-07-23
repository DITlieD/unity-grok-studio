#!/usr/bin/env python3
"""Texel density check from mesh_stats + map resolution + style tile_size_m."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def check(
    stats: dict,
    style: dict,
    map_res: int,
    *,
    min_px_per_m: float | None = None,
    max_px_per_m: float | None = None,
) -> dict:
    uv_area = float(stats.get("uv_area", 1.0) or 1.0)
    world_area = float(stats.get("world_surface_area_m2", stats.get("surface_area", 1.0)) or 1.0)
    # density ≈ map_res * sqrt(uv_area) / sqrt(world_area)  (px/m rough)
    if world_area <= 0:
        world_area = 1.0
    density = (map_res * (uv_area ** 0.5)) / (world_area ** 0.5)
    td = style.get("texel_density") or {}
    lo = min_px_per_m if min_px_per_m is not None else float(td.get("min_px_per_m", 64))
    hi = max_px_per_m if max_px_per_m is not None else float(td.get("max_px_per_m", 1024))
    ok = lo <= density <= hi
    issues = [] if ok else [f"texel_density={density:.1f} px/m outside [{lo},{hi}]"]
    return {
        "pass": ok,
        "density_px_per_m": density,
        "min": lo,
        "max": hi,
        "map_res": map_res,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", required=True)
    ap.add_argument("--style", required=True)
    ap.add_argument("--map-res", type=int, default=2048)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
    style_path = Path(args.style)
    if style_path.suffix in (".yaml", ".yml"):
        if yaml is None:
            raise SystemExit("pyyaml required")
        style = yaml.safe_load(style_path.read_text(encoding="utf-8")) or {}
    else:
        style = json.loads(style_path.read_text(encoding="utf-8"))
    report = check(stats, style, args.map_res)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("PASS" if report["pass"] else "FAIL", report)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
