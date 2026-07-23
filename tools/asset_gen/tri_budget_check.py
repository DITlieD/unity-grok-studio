#!/usr/bin/env python3
"""Triangle budget check against asset-style.yaml class caps."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_style(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            raise SystemExit("pyyaml required for asset-style.yaml")
        return yaml.safe_load(text) or {}
    return json.loads(text)


def check(stats: dict, style: dict, asset_class: str) -> dict:
    budgets = (style.get("tri_budgets") or style.get("triangle_budgets") or {})
    cap = budgets.get(asset_class)
    if cap is None:
        # fallback flat max
        cap = int(style.get("default_tri_budget", 50000))
    tris = int(stats.get("tris", stats.get("triangles", 0)) or 0)
    ok = tris <= int(cap)
    return {
        "pass": ok,
        "class": asset_class,
        "tris": tris,
        "budget": int(cap),
        "issues": [] if ok else [f"tris={tris} exceeds budget={cap} for class={asset_class}"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", required=True)
    ap.add_argument("--style", required=True, help="asset-style.yaml")
    ap.add_argument("--class", dest="asset_class", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
    style = load_style(Path(args.style))
    report = check(stats, style, args.asset_class)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("PASS" if report["pass"] else "FAIL", report)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
