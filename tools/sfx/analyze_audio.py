#!/usr/bin/env python3
"""Objective QA analyzer + waveform/mel PNG for sfx-forge.

Exit codes (fail-closed):
  0 = pass
  1 = threshold fail
  2 = scan error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# allow running as script from tools/sfx
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.metrics import analyze_file, evaluate_profile, load_profiles, load_audio
from lib.spectrogram import render_waveform_mel_png


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze SFX wav: metrics + spectrogram PNG")
    ap.add_argument("--file", "-f", required=True, help="Path to wav")
    ap.add_argument(
        "--profile",
        "-p",
        default="default",
        help="Threshold profile from checks.toml (ui/impact/loop/ambience/default)",
    )
    ap.add_argument("--json", action="store_true", help="Print JSON metrics to stdout")
    ap.add_argument(
        "--png",
        default=None,
        help="PNG output path (default: <wav>.qa.png beside input)",
    )
    ap.add_argument(
        "--no-png",
        action="store_true",
        help="Skip spectrogram render",
    )
    ap.add_argument(
        "--checks",
        default=None,
        help="Path to checks.toml (default: tools/sfx/checks.toml)",
    )
    args = ap.parse_args(argv)

    wav = Path(args.file)
    if not wav.exists():
        err = {
            "path": str(wav),
            "pass": False,
            "exit": 2,
            "failed_checks": ["scan_error"],
            "errors": [f"scan_error:file not found: {wav}"],
        }
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"scan error: file not found: {wav}", file=sys.stderr)
        return 2

    metrics = analyze_file(wav)
    if metrics.errors and any(e.startswith("scan_error") for e in metrics.errors):
        out = {
            "path": str(wav),
            "pass": False,
            "exit": 2,
            "failed_checks": ["scan_error"],
            "metrics": metrics.to_dict(),
            "errors": metrics.errors,
        }
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print(f"scan error: {metrics.errors}", file=sys.stderr)
        return 2

    profiles = load_profiles(args.checks)
    if args.profile not in profiles:
        print(f"unknown profile: {args.profile}", file=sys.stderr)
        return 2
    ok, failed = evaluate_profile(metrics, profiles[args.profile])

    png_path = None
    if not args.no_png:
        png_path = Path(args.png) if args.png else wav.with_suffix(wav.suffix + ".qa.png")
        try:
            data, sr, _ = load_audio(wav)
            render_waveform_mel_png(data, sr, png_path, title=wav.name)
        except Exception as e:
            # PNG failure is soft for metrics path, but record it
            metrics.errors.append(f"png_error:{e}")
            png_path = None

    result = {
        "path": str(wav.resolve()),
        "profile": args.profile,
        "pass": ok,
        "exit": 0 if ok else 1,
        "failed_checks": failed,
        "metrics": metrics.to_dict(),
        "png": str(png_path) if png_path else None,
        "finite": metrics.is_finite(),
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "PASS" if ok else "FAIL"
        print(f"{status} {wav.name} profile={args.profile}")
        m = metrics
        print(
            f"  dur={m.duration_s:.3f}s sr={m.sample_rate} ch={m.channels} "
            f"peak={m.peak_dbfs:.1f}dBFS lufs={m.integrated_lufs} "
            f"clip={m.clip_samples} onsets={m.onset_count}"
        )
        if failed:
            print(f"  failed: {', '.join(failed)}")
        if png_path:
            print(f"  png: {png_path}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
