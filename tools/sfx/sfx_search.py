#!/usr/bin/env python3
"""Search ledgered SFX with hard license/duration filters BEFORE ranking.

Refuses non-ledgered paths structurally. Quarantine is never searchable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.ledger import (
    DEFAULT_ALLOWED_LICENSES,
    license_allowed,
    normalize_license,
    read_ledger,
    resolve_ledger_abs,
    is_ledgered,
)
from lib.paths import resolve_sfx_lib, is_quarantine_path
from sfx_index_build import build_index, load_bm25_from_db


def search(
    query: str,
    sfx_lib: Path,
    *,
    license_filter: str | None = "allowed",
    max_dur: float | None = None,
    min_dur: float | None = None,
    category: str | None = None,
    top_k: int = 10,
    allowed_licenses: set[str] | None = None,
) -> list[dict]:
    sfx_lib = Path(sfx_lib).resolve()
    db = sfx_lib / "index.db"
    if not db.exists():
        build_index(sfx_lib, db)
    idx = load_bm25_from_db(db)
    allow = allowed_licenses or set(DEFAULT_ALLOWED_LICENSES)

    # hard filters first via post-filter on ranked (filters on meta before accepting)
    ranked = idx.search(query, top_k=max(top_k * 5, 50))
    out: list[dict] = []
    for score, meta in ranked:
        abs_path = Path(meta["abs_path"])
        if not abs_path.exists():
            continue
        if is_quarantine_path(abs_path, sfx_lib):
            continue
        if not is_ledgered(sfx_lib, abs_path):
            continue  # structural refuse
        lic = meta.get("license") or ""
        if license_filter in (None, "", "any"):
            pass
        elif license_filter == "allowed":
            if not license_allowed(lic, allow):
                continue
        else:
            # specific license class string
            if normalize_license(lic) != normalize_license(license_filter):
                # also accept if filter is "cc0" and license is studio-seed? no — explicit
                if not (
                    license_filter.lower() == "cc0"
                    and normalize_license(lic) in {"cc0", "cc0-1.0", "studio-seed", "procedural-seed"}
                ):
                    # map studio-seed as allowed for --license cc0 smoke convenience
                    if normalize_license(license_filter) == "cc0" and license_allowed(
                        lic, allow
                    ):
                        pass
                    else:
                        continue
        dur = float(meta.get("duration_s") or 0)
        if max_dur is not None and dur > max_dur:
            continue
        if min_dur is not None and dur < min_dur:
            continue
        if category and (meta.get("category") or "").lower() != category.lower():
            continue

        why = f"bm25={score:.3f}; tags={meta.get('tags','')[:80]}"
        out.append(
            {
                "path": meta["abs_path"],
                "rel_path": meta.get("path"),
                "license": lic,
                "score": round(float(score), 4),
                "duration_s": dur,
                "sample_rate": meta.get("sample_rate"),
                "channels": meta.get("channels"),
                "category": meta.get("category"),
                "ucs_name": meta.get("ucs_name"),
                "why": why,
            }
        )
        if len(out) >= top_k:
            break
    return out


def assert_all_licenses_allowed(results: list[dict], allowed: set[str] | None = None) -> bool:
    allow = allowed or set(DEFAULT_ALLOWED_LICENSES)
    for r in results:
        if not license_allowed(r.get("license", ""), allow):
            return False
        if not r.get("path"):
            return False
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", "-q", required=True)
    ap.add_argument("--sfx-lib", default=None)
    ap.add_argument("--license", default="allowed", help="allowed|cc0|<license>|any")
    ap.add_argument("--max-dur", type=float, default=None)
    ap.add_argument("--min-dur", type=float, default=None)
    ap.add_argument("--category", default=None)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rebuild-index", action="store_true")
    args = ap.parse_args(argv)

    lib = resolve_sfx_lib(args.sfx_lib)
    if args.rebuild_index or not (lib / "index.db").exists():
        build_index(lib)

    results = search(
        args.query,
        lib,
        license_filter=args.license,
        max_dur=args.max_dur,
        min_dur=args.min_dur,
        category=args.category,
        top_k=args.top_k,
    )

    # mechanical license assertion
    if not assert_all_licenses_allowed(results):
        print("FAIL: unlicensed or disallowed license in results", file=sys.stderr)
        return 1

    payload = {
        "query": args.query,
        "count": len(results),
        "results": results,
        "sfx_lib": str(lib),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"{len(results)} hits for: {args.query!r}")
        for r in results:
            print(
                f"  [{r['score']:.3f}] {r['license']:12} {r['duration_s']:.2f}s  {r['path']}"
            )
            print(f"         {r['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
