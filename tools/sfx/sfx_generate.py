#!/usr/bin/env python3
"""Generation wrapper: fail-closed on license_class, provenance always.

Only commercial_ok providers run on the shipping path. noncommercial/unknown
require --research-quarantine and write under SFX_LIB/quarantine/ which
search and assemble refuse to read.

When Stable Audio host/weights are not viable, the commercial provider is
parked (A3/A4): exit 3 with reason and write evidence.

DSP audio is ONLY produced with --allow-dsp-placeholder and is always labeled
backend=dsp_placeholder — never laundered as stable_audio. A live provider
status without a real inference host refuses (exit 4) rather than faking.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.dsp import synth_crackle_tail, write_wav
from lib.paths import resolve_sfx_lib


def load_providers(path: Path | None = None) -> dict:
    path = path or (_ROOT / "providers.toml")
    with open(path, "rb") as f:
        return tomllib.load(f).get("providers", {})


def refuse_message(name: str, license_class: str) -> str:
    return (
        f"REFUSED provider={name} license_class={license_class}: "
        "noncommercial/unknown providers are excluded from the shipping path "
        "unless --research-quarantine is set (outputs go to quarantine, "
        "unread by search/assemble)."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["t2a", "a2a", "inpaint"], default="t2a")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative", default="music, voices, speech, melody, reverb wash")
    ap.add_argument("--dur", type=float, default=1.2)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--count", type=int, default=4)
    ap.add_argument("--provider", default="stable_audio_3_small_sfx")
    ap.add_argument("--ref", default=None)
    ap.add_argument("--out", default=None, help="output dir")
    ap.add_argument("--sfx-lib", default=None)
    ap.add_argument("--research-quarantine", action="store_true")
    ap.add_argument(
        "--allow-dsp-placeholder",
        action="store_true",
        help="Emit deterministic DSP candidates labeled backend=dsp_placeholder only",
    )
    ap.add_argument("--providers-toml", default=None)
    args = ap.parse_args(argv)

    providers = load_providers(Path(args.providers_toml) if args.providers_toml else None)
    if args.provider not in providers:
        print(f"unknown provider: {args.provider}", file=sys.stderr)
        return 2
    prov = providers[args.provider]
    lic = prov.get("license_class", "unknown")
    lib = resolve_sfx_lib(args.sfx_lib)

    if lic in ("noncommercial", "unknown"):
        if not args.research_quarantine:
            print(refuse_message(args.provider, lic), file=sys.stderr)
            return 1
        out_dir = lib / "quarantine" / "gen" / f"seed{args.seed}"
    else:
        out_dir = Path(args.out) if args.out else (lib / "generated" / f"seed{args.seed}")

    status = prov.get("status", "live")
    inference_implemented = bool(prov.get("inference_implemented", False))

    # parked commercial provider without placeholder
    if lic == "commercial_ok" and status.startswith("parked") and not args.allow_dsp_placeholder:
        msg = {
            "status": "parked",
            "reason": status,
            "provider": args.provider,
            "license_class": lic,
            "abort": "A3/A4",
            "note": "Generation leg parked; retrieval-only pipeline remains valid.",
        }
        print(json.dumps(msg, indent=2))
        return 3

    # live status but no real inference host wired: refuse (do not launder DSP)
    if (
        not args.allow_dsp_placeholder
        and not inference_implemented
        and not status.startswith("parked")
    ):
        msg = {
            "status": "refused",
            "reason": "inference_not_implemented",
            "provider": args.provider,
            "license_class": lic,
            "note": (
                "Provider marked live but no real inference host is wired. "
                "Pass --allow-dsp-placeholder for labeled DSP test audio only, "
                "or park the provider (status=parked_*)."
            ),
        }
        print(json.dumps(msg, indent=2), file=sys.stderr)
        return 4

    if not args.allow_dsp_placeholder and inference_implemented:
        # Real Stable Audio path not shipped in this build — fail closed
        msg = {
            "status": "refused",
            "reason": "stable_audio_runtime_not_shipped",
            "provider": args.provider,
            "license_class": lic,
            "note": "inference_implemented flag set but runtime not present; refuse rather than fake.",
        }
        print(json.dumps(msg, indent=2), file=sys.stderr)
        return 4

    if not args.allow_dsp_placeholder:
        # Only remaining path would be real inference; we never silent-DSP
        print(
            json.dumps(
                {
                    "status": "refused",
                    "reason": "no_backend",
                    "provider": args.provider,
                }
            ),
            file=sys.stderr,
        )
        return 4

    # DSP placeholder only — always labeled honestly
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for i in range(args.count):
        seed_i = args.seed + i
        audio = synth_crackle_tail(48000, max(0.2, args.dur), seed=seed_i)
        wav_path = out_dir / f"gen_{args.mode}_{seed_i:04d}.wav"
        write_wav(wav_path, audio, 48000)
        prov_json = {
            "provider": args.provider,
            "model_id": prov.get("model_id"),
            "license_class": lic,
            "mode": args.mode,
            "prompt": args.prompt,
            "negative": args.negative,
            "duration_s": args.dur,
            "seed": seed_i,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "path": str(wav_path),
            "backend": "dsp_placeholder",
            "quarantine": lic in ("noncommercial", "unknown"),
        }
        meta_path = wav_path.with_suffix(".provenance.json")
        meta_path.write_text(json.dumps(prov_json, indent=2), encoding="utf-8")
        written.append({"wav": str(wav_path), "provenance": str(meta_path)})

    print(
        json.dumps(
            {
                "count": len(written),
                "out_dir": str(out_dir),
                "provider": args.provider,
                "license_class": lic,
                "backend": "dsp_placeholder",
                "items": written,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
