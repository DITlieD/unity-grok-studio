#!/usr/bin/env python3
"""Freesound CC0 ORIGINAL-file fetch via OAuth2 (deliverable-8 leg).

freesound_fetch.py stays the preview/search reference; this leg pulls the
uploader's ORIGINAL file (wav/flac/aiff/mp3 as-uploaded) through the OAuth2
download endpoint and writes a ledger row per the standard lib.ledger schema
BEFORE the file is usable. Sources are as-received and immutable (no re-encode).

Auth: the OAuth2 bearer token comes from freesound_oauth.py at call time and is
held only in memory -- never printed, logged, or written to any file. CC0 filter
is mandatory. Rate limits are honoured with Retry-After backoff.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import soundfile as sf

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.ledger import LedgerRow, file_sha256, now_iso, read_ledger, write_ledger
from lib.paths import resolve_sfx_lib

FANTASY_CARTOON_QUERIES = [
    "cartoon boing",
    "cartoon impact",
    "magic spell",
    "fantasy whoosh",
    "stylized fire crackle",
    "pop",
    "sparkle chime",
    "cartoon explosion",
]

CC0_FILTER = 'license:"Creative Commons 0"'
_TYPE_EXT = {"wav": ".wav", "flac": ".flac", "aiff": ".aiff", "aif": ".aiff", "ogg": ".ogg", "mp3": ".mp3", "m4a": ".m4a"}


def get_bearer() -> str:
    tok = subprocess.run(
        [sys.executable, str(_ROOT / "freesound_oauth.py"), "token"],
        capture_output=True, text=True, timeout=40,
    ).stdout.strip()
    if not tok:
        raise SystemExit("no bearer token from freesound_oauth.py")
    return tok


def license_is_cc0(lic: str) -> bool:
    l = (lic or "").lower()
    return "zero" in l or "cc0" in l or "publicdomain" in l.replace(" ", "")


def api_get(url: str, bearer: str) -> dict:
    for attempt in range(5):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bearer}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After", "5")) + 1
                print(f"  rate-limited, backing off {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
    raise SystemExit("search kept rate-limiting")


def search_cc0(query: str, bearer: str, page_size: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "query": query,
        "fields": "id,name,username,license,url,type,samplerate,channels,duration,filesize",
        "page_size": page_size,
        "filter": CC0_FILTER,
        "sort": "downloads_desc",
    })
    data = api_get(f"https://freesound.org/apiv2/search/text/?{params}", bearer)
    return [h for h in data.get("results", []) if license_is_cc0(h.get("license", ""))]


def derive_tags(name: str, query: str, ftype: str) -> str:
    low = f"{name} {query}".lower()
    toks: dict[str, None] = {}
    for t in re.split(r"[^a-z0-9]+", low):
        if len(t) >= 3 and not t.isdigit():
            toks.setdefault(t, None)
    toks.setdefault("stylized", None)
    if re.search(r"cartoon|boing|comic|goofy|pop|honk|squeak", low):
        for t in ("cartoon", "exaggerated"):
            toks.setdefault(t, None)
    if re.search(r"magic|spell|fantasy|sparkle|whoosh|fairy", low):
        for t in ("fantasy", "designed"):
            toks.setdefault(t, None)
    toks.setdefault(f"fmt-{ftype}", None)
    return " ".join(toks.keys())


def download_original(sound_id: int, dest: Path, bearer: str) -> bool:
    url = f"https://freesound.org/apiv2/sounds/{sound_id}/download/"
    # curl -L strips auth on the cross-host CDN redirect (correct: signed URL)
    r = subprocess.run(
        ["curl", "-sL", "--max-time", "120", "-H", f"Authorization: Bearer {bearer}",
         "-o", str(dest), "-w", "%{http_code}", url],
        capture_output=True, text=True,
    )
    code = (r.stdout or "").strip()[-3:]
    if code != "200" or not dest.exists() or dest.stat().st_size < 256:
        dest.unlink(missing_ok=True)
        print(f"  download fail id={sound_id} http={code}", flush=True)
        return False
    return True


def run(sfx_lib: Path, queries: list[str], max_per_query: int, max_total: int) -> tuple[int, int, Path]:
    sfx_lib = Path(sfx_lib).resolve()
    out_dir = sfx_lib / "freesound"
    out_dir.mkdir(parents=True, exist_ok=True)
    bearer = get_bearer()

    existing = {r.path: r for r in read_ledger(sfx_lib)}
    have_ids = {r.source_id for r in existing.values() if r.source == "freesound"}
    added = 0
    fails = 0

    for q in queries:
        if added >= max_total:
            break
        try:
            hits = search_cc0(q, bearer, max(max_per_query * 2, 15))
        except Exception as e:
            print(f"search fail {q!r}: {e}", flush=True)
            continue
        print(f"query {q!r}: {len(hits)} cc0 hits", flush=True)
        got = 0
        for h in hits:
            if got >= max_per_query or added >= max_total:
                break
            sid = h["id"]
            if str(sid) in have_ids:
                continue
            ftype = (h.get("type") or "wav").lower()
            ext = _TYPE_EXT.get(ftype, ".bin")
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (h.get("name") or f"fs{sid}"))[:70]
            dest = out_dir / f"FS_{sid}_{safe}{ext}"
            if dest.exists():
                continue
            if not download_original(sid, dest, bearer):
                fails += 1
                time.sleep(1)
                continue
            # metadata: header read for readable formats, else API fields (mp3/m4a)
            sr = int(h.get("samplerate") or 0)
            ch = int(h.get("channels") or 0)
            dur = float(h.get("duration") or 0.0)
            try:
                info = sf.info(str(dest))
                sr = int(info.samplerate) or sr
                ch = int(info.channels) or ch
                dur = (float(info.frames) / info.samplerate) if info.samplerate else dur
            except Exception:
                pass  # mp3/m4a: keep API-reported sr/ch/duration
            rel = str(dest.relative_to(sfx_lib)).replace("\\", "/")
            row = LedgerRow(
                path=rel,
                original_name=h.get("name") or dest.name,
                ucs_name=dest.name,
                license="cc0",
                source="freesound",
                source_id=str(sid),
                uploader=h.get("username") or "",
                url=h.get("url") or f"https://freesound.org/s/{sid}/",
                download_date=now_iso(),
                duration_s=round(dur, 3),
                sample_rate=sr,
                channels=ch,
                sha256=file_sha256(dest),
                tags=derive_tags(h.get("name") or "", q, ftype),
                category=f"freesound:{ftype}",
            )
            existing[rel] = row
            have_ids.add(str(sid))
            added += 1
            got += 1
            print(f"  saved id={sid} fmt={ftype} sr={sr} {dest.name}", flush=True)
            time.sleep(0.4)  # gentle on the API

    led = write_ledger(sfx_lib, list(existing.values()))
    return added, fails, led


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sfx-lib", default=None)
    ap.add_argument("--queries", default=None, help="comma-separated; default fantasy/cartoon set")
    ap.add_argument("--max-per-query", type=int, default=25)
    ap.add_argument("--max-total", type=int, default=250)
    args = ap.parse_args(argv)
    lib = resolve_sfx_lib(args.sfx_lib)
    queries = [q.strip() for q in args.queries.split(",")] if args.queries else FANTASY_CARTOON_QUERIES
    added, fails, led = run(lib, queries, args.max_per_query, args.max_total)
    print(f"freesound originals: added {added}, failed {fails}")
    print(f"ledger -> {led}; total rows: {len(read_ledger(lib))}")
    return 0 if added else 1


if __name__ == "__main__":
    sys.exit(main())
