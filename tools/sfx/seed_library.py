#!/usr/bin/env python3
"""Build a minimal ledgered seed library for search+assemble smokes.

When Sonniss/Freesound are unavailable unattended, this writes physical-ish
procedural seed wavs under SFX_LIB/seed/ with full ledger provenance
(license=studio-seed). Sources are immutable after write.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.dsp import (
    synth_crackle_tail,
    synth_debris,
    synth_fire_bed,
    synth_glass_debris,
    synth_impact,
    synth_metal_impact,
    synth_sub_boom,
    synth_wood_slam,
    write_wav,
)
from lib.ledger import LedgerRow, file_sha256, now_iso, write_ledger
from lib.paths import resolve_sfx_lib
from lib.metrics import analyze_file

SR = 48000

# (relative path, synth fn kwargs, tags, category)
SEEDS = [
    (
        "seed/IMPACT_WoodDoorSlam_Close_01.wav",
        lambda: synth_wood_slam(SR, 0.55, seed=101),
        "wood door slam close dry heavy wooden impact",
        "impact",
    ),
    (
        "seed/IMPACT_WoodDoorSlam_Close_02.wav",
        lambda: synth_wood_slam(SR, 0.48, seed=102),
        "wood door slam close dry heavy wooden impact",
        "impact",
    ),
    (
        "seed/IMPACT_MetalHit_Dry_01.wav",
        lambda: synth_metal_impact(SR, 0.35, seed=201),
        "metal impact hit dry close sword clang",
        "impact",
    ),
    (
        "seed/IMPACT_MetalHit_Dry_02.wav",
        lambda: synth_metal_impact(SR, 0.4, seed=202),
        "metal impact dry close under 1s no voices",
        "impact",
    ),
    (
        "seed/IMPACT_GenericThump_01.wav",
        lambda: synth_impact(SR, 0.3, seed=301, f0=90, brightness=0.3),
        "impact thump body dry close",
        "impact",
    ),
    (
        "seed/DEBRIS_Scatter_01.wav",
        lambda: synth_debris(SR, 0.75, seed=401, density=0.6),
        "debris scatter particles fall dry",
        "debris",
    ),
    (
        "seed/DEBRIS_Scatter_02.wav",
        lambda: synth_debris(SR, 0.9, seed=402, density=0.8),
        "debris scatter grit wood chips",
        "debris",
    ),
    (
        "seed/DEBRIS_Glass_01.wav",
        lambda: synth_glass_debris(SR, 0.85, seed=501),
        "glass debris scatter shards tink",
        "debris",
    ),
    (
        "seed/DEBRIS_Glass_02.wav",
        lambda: synth_glass_debris(SR, 1.0, seed=502),
        "glass debris scatter break",
        "debris",
    ),
    (
        "seed/FIRE_Transient_Boom_01.wav",
        lambda: synth_impact(SR, 0.25, seed=601, f0=55, brightness=0.55),
        "firework burst transient explosion boom impact",
        "transient",
    ),
    (
        "seed/FIRE_Debris_Sparks_01.wav",
        lambda: synth_debris(SR, 0.7, seed=602, density=0.9),
        "firework debris sparks scatter crackle particles",
        "debris",
    ),
    (
        "seed/FIRE_Sub_Boom_01.wav",
        lambda: synth_sub_boom(SR, 0.95, seed=603, f0=42),
        "sub boom low explosion body firework",
        "sub",
    ),
    (
        "seed/FIRE_CrackleTail_01.wav",
        lambda: synth_crackle_tail(SR, 1.05, seed=604),
        "crackle tail firework sparks decay dry",
        "tail",
    ),
    (
        "seed/IMPACT_WoodKnock_Light_01.wav",
        lambda: synth_wood_slam(SR, 0.3, seed=701),
        "wood knock light impact dry close under 1s",
        "impact",
    ),
    (
        "seed/IMPACT_HeavyThud_01.wav",
        lambda: synth_impact(SR, 0.45, seed=801, f0=60, brightness=0.2),
        "heavy thud wooden impact dry close under 1s no room",
        "impact",
    ),
    (
        "seed/FIRE_BurningBed_Close_01.wav",
        lambda: synth_fire_bed(SR, 3.0, seed=9101, intensity=0.8),
        "fire burning campfire flame crackle rumble dry close wood burn",
        "ambience",
    ),
    (
        "seed/FIRE_BurningBed_Close_02.wav",
        lambda: synth_fire_bed(SR, 3.0, seed=9102, intensity=0.65),
        "fire burning campfire flame crackle rumble dry close wood burn soft",
        "ambience",
    ),
]


def build(sfx_lib: Path, force: bool = False) -> tuple[int, Path]:
    sfx_lib = Path(sfx_lib)
    sfx_lib.mkdir(parents=True, exist_ok=True)
    rows = []
    for rel, fn, tags, cat in SEEDS:
        out = sfx_lib / rel
        if out.exists() and not force:
            # still re-ledger
            pass
        else:
            audio = fn()
            write_wav(out, audio, SR)
        m = analyze_file(out)
        name = out.name
        rows.append(
            LedgerRow(
                path=rel.replace("\\", "/"),
                original_name=name,
                ucs_name=name,
                license="studio-seed",
                source="seed_library.py",
                source_id=f"seed:{name}",
                uploader="unity-grok-studio",
                url="",
                download_date=now_iso(),
                duration_s=m.duration_s,
                sample_rate=m.sample_rate,
                channels=m.channels,
                sha256=file_sha256(out),
                tags=tags,
                category=cat,
            )
        )
    # also write clipped fixture under tools for U1 (not in library for search)
    led = write_ledger(sfx_lib, rows)
    return len(rows), led


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sfx-lib", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    lib = resolve_sfx_lib(args.sfx_lib)
    n, led = build(lib, force=args.force)
    wavs = list(lib.rglob("*.wav"))
    # exclude quarantine
    wavs = [w for w in wavs if "quarantine" not in w.parts]
    print(f"seeded {n} ledger rows -> {led}")
    print(f"wav count under SFX_LIB (non-quarantine): {len(wavs)}")
    print(f"SFX_LIB={lib}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
