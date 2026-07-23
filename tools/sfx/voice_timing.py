#!/usr/bin/env python3
"""Optional voice-timing leg: guide wav -> event map for assemble.

OFF BY DEFAULT in skill doctrine. Only when owner hands a guide recording.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import yaml

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.metrics import analyze_file, load_audio


def envelope_peaks(
    x: np.ndarray, sr: int, floor: float = 0.15, min_gap_s: float = 0.08
) -> list[float]:
    hop = max(64, int(sr * 0.01))
    n_frames = max(1, (len(x) - hop) // hop)
    env = np.array(
        [np.sqrt(np.mean(x[i * hop : i * hop + hop] ** 2)) for i in range(n_frames)]
    )
    if env.size == 0:
        return []
    peak = float(np.max(env)) or 1.0
    thr = floor * peak
    times: list[float] = []
    last = -1e9
    for i in range(1, len(env) - 1):
        if env[i] >= thr and env[i] >= env[i - 1] and env[i] >= env[i + 1]:
            t = i * hop / sr
            if t - last >= min_gap_s:
                times.append(float(t))
                last = t
    return times


def extract_event_map(
    path: Path,
    mode: str = "onset",
) -> dict:
    m = analyze_file(path)
    data, sr, _ = load_audio(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if mode == "envelope":
        times = envelope_peaks(data, sr)
    else:
        times = list(m.onset_times_s)
        if not times:
            times = envelope_peaks(data, sr)
    events = [{"t_ms": round(t * 1000.0, 3), "label": f"e{i}"} for i, t in enumerate(times)]
    # energy envelope downsample for optional use
    hop = max(64, int(sr * 0.02))
    env = [
        float(np.sqrt(np.mean(data[i : i + hop] ** 2)))
        for i in range(0, max(1, len(data) - hop), hop)
    ]
    return {
        "event_map": events,
        "onset_count": len(events),
        "mode": mode,
        "guide": str(path.resolve()),
        "duration_s": m.duration_s,
        "energy_envelope": env[:500],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", "-f", required=True)
    ap.add_argument("--mode", choices=["onset", "envelope"], default="onset")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None, help="write event map yaml")
    args = ap.parse_args(argv)

    path = Path(args.file)
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        return 2
    result = extract_event_map(path, mode=args.mode)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml.safe_dump({"event_map": result["event_map"]}, sort_keys=False), encoding="utf-8")
        result["written"] = str(out)
    if args.json:
        # trim envelope in json for size
        print(json.dumps(result, indent=2))
    else:
        print(f"onsets={result['onset_count']} mode={result['mode']}")
        for e in result["event_map"]:
            print(f"  {e['t_ms']:.1f}ms  {e['label']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
