#!/usr/bin/env python3
"""Ingest an extracted Sonniss GDC bundle tree into SFX_LIB with license ledger rows.

Follows the seed_library.py / freesound_fetch.py convention exactly: same
lib.ledger LedgerRow schema, license=sonniss-gdc (already in
DEFAULT_ALLOWED_LICENSES), provenance written BEFORE a file is usable, sources
immutable after ingest. Bulk metadata comes from soundfile.info (header-only,
fast); the full analyze_audio QA stays a per-candidate step at assemble/report
time, not an ingest requirement.

Fantasy/cartoon curation rides the existing free-text `tags` column and the
`category` bucket (no new ledger field): folder/filename tokens that name
stylized game sound (magic, whoosh, cartoon, spell, fire, impact, ui...) get
normalized style tags appended so BM25 surfaces them.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import soundfile as sf

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.ledger import LedgerRow, file_sha256, now_iso, read_ledger, write_ledger
from lib.paths import resolve_sfx_lib

AUDIO_EXTS = {".wav", ".flac", ".aif", ".aiff", ".ogg", ".w64"}

# category bucket -> keyword patterns (first match wins; order = priority)
CATEGORY_RULES: list[tuple[str, re.Pattern]] = [
    ("magic", re.compile(r"magic|spell|arcane|enchant|rune|mana|wizard|sorcer|cast(ing)?")),
    ("explosion", re.compile(r"explos|blast|detona|firework|kaboom")),
    ("fire", re.compile(r"\bfire\b|flame|burn|ember|torch|campfire|ignite")),
    ("whoosh", re.compile(r"whoosh|swoosh|swish|swipe|swing|woosh|air\s?swipe|pass\s?by")),
    ("weapon", re.compile(r"sword|blade|axe|dagger|gun|rifle|pistol|laser|blaster|arrow|bow|melee|clang|sheath")),
    ("impact", re.compile(r"impact|hit|punch|slam|smash|thud|thump|crash|bonk|whack|crunch")),
    ("cartoon", re.compile(r"cartoon|boing|boink|comic|comedy|goofy|zany|slapstick|slap\s?stick|bonk|squeak|honk|toon")),
    ("ui", re.compile(r"\bui\b|menu|button|click|hover|beep|blip|notif|hud|interface|select|confirm|cursor")),
    ("pickup", re.compile(r"pickup|coin|collect|reward|powerup|power\s?up|score|bonus|gem|loot")),
    ("sparkle", re.compile(r"sparkle|shimmer|chime|twinkle|glitter|magic\s?wand|fairy|glow|pixie")),
    ("creature", re.compile(r"creature|monster|beast|dragon|goblin|orc|growl|roar|snarl|grunt|screech")),
    ("footstep", re.compile(r"footstep|foot\s?step|walk|run\s?step|boot|stomp")),
    ("water", re.compile(r"water|splash|drip|bubble|liquid|pour|wave|ocean|river")),
    ("ambience", re.compile(r"ambien|atmos|room\s?tone|drone|background|loop|forest|wind|rain|cave|dungeon")),
    ("voice", re.compile(r"voice|vocal|shout|scream|laugh|dialog|grunt|breath")),
    ("foley", re.compile(r"foley|cloth|paper|wood|metal|glass|rope|leather|handling")),
]

FANTASY_RE = re.compile(
    r"magic|spell|arcane|enchant|rune|mana|wizard|sorcer|fantasy|dragon|goblin|orc|"
    r"fairy|pixie|potion|dungeon|medieval|myth|elf|troll|sword|blade|bow|arrow"
)
CARTOON_RE = re.compile(
    r"cartoon|toon|boing|boink|comic|comedy|goofy|zany|slap\s?stick|squeak|honk|"
    r"bonk|silly|wacky|comedic|pop\b|sparkle|whimsic"
)
DESIGNED_RE = re.compile(
    r"design|stylis|stylized|game|hybrid|whoosh|magic|ui|interface|sparkle|impact|"
    r"cartoon|sci\s?fi|scifi|fantasy|synth"
)


def derive_category(text: str) -> str:
    for cat, pat in CATEGORY_RULES:
        if pat.search(text):
            return cat
    return "sonniss"


def derive_tags(rel_path: str, category: str) -> str:
    low = rel_path.lower().replace("\\", "/")
    # descriptive tokens from path folders + filename (deduped, order-preserving)
    raw = re.split(r"[/_\-.\s]+", low)
    seen: dict[str, None] = {}
    for tok in raw:
        tok = tok.strip()
        if len(tok) >= 3 and not tok.isdigit() and tok not in ("wav", "flac", "aiff"):
            seen.setdefault(tok, None)
    tags = list(seen.keys())[:24]
    tags.append(category)
    if FANTASY_RE.search(low):
        tags += ["fantasy", "stylized"]
    if CARTOON_RE.search(low):
        tags += ["cartoon", "stylized", "exaggerated"]
    if DESIGNED_RE.search(low):
        tags.append("designed")
    # dedupe again
    out: dict[str, None] = {}
    for t in tags:
        out.setdefault(t, None)
    return " ".join(out.keys())


def probe(path: Path) -> tuple[float, int, int] | None:
    """Header-only (duration_s, sample_rate, channels); None if unreadable."""
    try:
        info = sf.info(str(path))
        dur = float(info.frames) / info.samplerate if info.samplerate else 0.0
        return dur, int(info.samplerate), int(info.channels)
    except Exception:
        return None


def ingest(
    sfx_lib: Path,
    source_dir: Path,
    *,
    year: str,
    bundle_url: str,
    limit: int | None = None,
) -> tuple[int, int, int, Path]:
    sfx_lib = Path(sfx_lib).resolve()
    source_dir = Path(source_dir).resolve()
    source = f"sonniss_gdc_{year}"

    existing = {r.path: r for r in read_ledger(sfx_lib)}
    added = 0
    skipped = 0
    seen_files = 0

    files = sorted(p for p in source_dir.rglob("*") if p.suffix.lower() in AUDIO_EXTS)
    for f in files:
        seen_files += 1
        if limit is not None and added >= limit:
            break
        try:
            rel = str(f.relative_to(sfx_lib)).replace("\\", "/")
        except ValueError:
            skipped += 1
            continue
        if rel in existing:
            continue  # idempotent: already ledgered
        m = probe(f)
        if m is None:
            skipped += 1
            continue
        dur, sr, ch = m
        rel_in_bundle = str(f.relative_to(source_dir)).replace("\\", "/")
        category = derive_category(rel_in_bundle)
        tags = derive_tags(rel_in_bundle, category)
        # uploader = the contributor/library folder (top dir under the bundle)
        parts = f.relative_to(source_dir).parts
        uploader = parts[0] if len(parts) > 1 else ""
        row = LedgerRow(
            path=rel,
            original_name=f.name,
            ucs_name=f.name,
            license="sonniss-gdc",
            source=source,
            source_id=rel_in_bundle,
            uploader=uploader,
            url=bundle_url,
            download_date=now_iso(),
            duration_s=round(dur, 3),
            sample_rate=sr,
            channels=ch,
            sha256=file_sha256(f),
            tags=tags,
            category=category,
        )
        existing[rel] = row
        added += 1
        if added % 2000 == 0:
            print(f"  ingested {added} (seen {seen_files})...", flush=True)

    led = write_ledger(sfx_lib, list(existing.values()))
    return added, skipped, seen_files, led


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sfx-lib", default=None)
    ap.add_argument("--source-dir", required=True, help="extracted bundle tree under SFX_LIB")
    ap.add_argument("--year", required=True)
    ap.add_argument("--bundle-url", default="https://sonniss.com/gameaudiogdc")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args(argv)
    lib = resolve_sfx_lib(args.sfx_lib)
    added, skipped, seen, led = ingest(
        lib,
        Path(args.source_dir),
        year=args.year,
        bundle_url=args.bundle_url,
        limit=args.limit,
    )
    print(f"ingested {added} new rows; skipped {skipped}; scanned {seen} audio files")
    print(f"ledger -> {led}")
    print(f"total ledger rows: {len(read_ledger(lib))}")
    return 0 if added or seen == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
