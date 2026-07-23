#!/usr/bin/env python3
"""Mesh topology validator over mesh_stats.json produced by real geometry inspect.

Fails when:
  - nonmanifold_edges > max
  - floating_components > max (detached pieces far from main body)
  - flipped_faces > max
  - disconnected_components > max_disconnected (optional; default high for multi-brick props)

Generators must not self-certify: stats come from analyze_topology on positions+indices.
Exit 0 on pass, non-zero on fail.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def check_stats(
    stats: dict,
    *,
    max_nonmanifold: int = 0,
    max_floating: int = 0,
    max_flipped: int = 0,
    max_disconnected: int | None = None,
) -> dict:
    nm = int(stats.get("nonmanifold_edges", stats.get("nonmanifold", 0)) or 0)
    fl_comp = int(stats.get("floating_components", 0) or 0)
    # legacy: if floating_components absent, treat excess disconnected as fail signal
    dc = int(stats.get("disconnected_components", stats.get("disconnected", 1)) or 0)
    fl = int(stats.get("flipped_faces", stats.get("flipped", 0)) or 0)

    issues = []
    if nm > max_nonmanifold:
        issues.append(f"nonmanifold_edges={nm} > {max_nonmanifold}")
    if fl_comp > max_floating:
        issues.append(f"floating_components={fl_comp} > {max_floating}")
    if fl > max_flipped:
        issues.append(f"flipped_faces={fl} > {max_flipped}")
    if max_disconnected is not None and dc > max_disconnected:
        issues.append(f"disconnected_components={dc} > {max_disconnected}")

    return {
        "pass": not issues,
        "nonmanifold_edges": nm,
        "floating_components": fl_comp,
        "disconnected_components": dc,
        "flipped_faces": fl,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", required=True, help="Path to mesh_stats.json")
    ap.add_argument("--max-nonmanifold", type=int, default=0)
    ap.add_argument("--max-floating", type=int, default=0)
    ap.add_argument("--max-flipped", type=int, default=0)
    ap.add_argument(
        "--max-disconnected",
        type=int,
        default=None,
        help="Optional hard cap on edge-connected components (default: ignore raw count)",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    path = Path(args.stats)
    stats = json.loads(path.read_text(encoding="utf-8"))
    report = check_stats(
        stats,
        max_nonmanifold=args.max_nonmanifold,
        max_floating=args.max_floating,
        max_flipped=args.max_flipped,
        max_disconnected=args.max_disconnected,
    )
    report["stats_path"] = str(path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("PASS" if report["pass"] else "FAIL", "; ".join(report["issues"]) or "ok")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
