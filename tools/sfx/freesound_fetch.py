#!/usr/bin/env python3
"""Freesound API client with HARD license filter (default CC0).

Without FREESOUND_TOKEN, --dry-run still shows the filter that would apply.
Downloads write ledger rows BEFORE files are considered usable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.ledger import LedgerRow, append_ledger_row, file_sha256, now_iso
from lib.paths import resolve_sfx_lib
from lib.metrics import analyze_file

CC0_LICENSE_URLS = {
    "http://creativecommons.org/publicdomain/zero/1.0/",
    "https://creativecommons.org/publicdomain/zero/1.0/",
    "http://creativecommons.org/publicdomain/zero/1.0",
}


def license_is_cc0(license_field: str) -> bool:
    lic = (license_field or "").lower()
    if "zero" in lic or "cc0" in lic or "publicdomain" in lic.replace(" ", ""):
        return True
    return license_field.strip() in CC0_LICENSE_URLS


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", "-q", required=True)
    ap.add_argument("--sfx-lib", default=None)
    ap.add_argument("--allow-ccby", action="store_true")
    ap.add_argument("--max", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--token", default=None, help="or FREESOUND_TOKEN env")
    args = ap.parse_args(argv)

    token = args.token or os.environ.get("FREESOUND_TOKEN", "")
    lic_filter = "CC0 only"
    if args.allow_ccby:
        lic_filter = "CC0 + CC-BY (attribution required)"

    print(f"license_filter: {lic_filter}")
    print(f"query: {args.query!r}")

    if args.dry_run:
        print("dry-run: would search Freesound with hard license filter, write ledger rows")
        return 0

    if not token:
        print(
            "FREESOUND_TOKEN not set; cannot download. Create free account at freesound.org",
            file=sys.stderr,
        )
        return 2

    lib = resolve_sfx_lib(args.sfx_lib)
    out_dir = lib / "freesound"
    out_dir.mkdir(parents=True, exist_ok=True)

    # text search
    params = urllib.parse.urlencode(
        {
            "query": args.query,
            "token": token,
            "fields": "id,name,username,license,url,previews,duration",
            "page_size": max(args.max * 3, 15),
            "filter": 'license:"Creative Commons 0"',
        }
    )
    url = f"https://freesound.org/apiv2/search/text/?{params}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"api error: {e}", file=sys.stderr)
        return 2

    saved = 0
    for hit in data.get("results", []):
        if saved >= args.max:
            break
        lic = hit.get("license") or ""
        if not license_is_cc0(lic) and not args.allow_ccby:
            continue
        fid = hit["id"]
        name = hit.get("name") or f"fs_{fid}"
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)[:80]
        # use preview HQ as free download without oauth for smoke (not full quality)
        previews = hit.get("previews") or {}
        preview = previews.get("preview-hq-ogg") or previews.get("preview-hq-mp3")
        if not preview:
            continue
        dest = out_dir / f"FS_{fid}_{safe}.wav"
        # download preview then re-encode to wav via ffmpeg if needed
        tmp = dest.with_suffix(".tmp" + Path(preview).suffix)
        try:
            urllib.request.urlretrieve(preview, str(tmp))
            import subprocess

            subprocess.check_call(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(tmp),
                    "-ar",
                    "48000",
                    "-ac",
                    "1",
                    str(dest),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            tmp.unlink(missing_ok=True)
        except Exception as e:
            print(f"download fail {fid}: {e}", file=sys.stderr)
            continue

        m = analyze_file(dest)
        rel = str(dest.relative_to(lib)).replace("\\", "/")
        row = LedgerRow(
            path=rel,
            original_name=name,
            ucs_name=dest.name,
            license="cc0" if license_is_cc0(lic) else lic,
            source="freesound",
            source_id=str(fid),
            uploader=hit.get("username") or "",
            url=hit.get("url") or f"https://freesound.org/s/{fid}/",
            download_date=now_iso(),
            duration_s=m.duration_s,
            sample_rate=m.sample_rate,
            channels=m.channels,
            sha256=file_sha256(dest),
            tags=args.query,
            category="freesound",
        )
        append_ledger_row(lib, row)
        saved += 1
        print(f"saved {dest} license={row.license}")

    print(f"downloaded {saved}")
    return 0 if saved or args.dry_run else 1


if __name__ == "__main__":
    sys.exit(main())
