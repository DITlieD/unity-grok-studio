#!/usr/bin/env python3
"""Deterministic layer compositor + variation renderer.

Loads a layer plan yaml/json, aligns onsets, mixes master + variants + optional
stems, auto-QA via analyze, writes family manifest. Byte-identical on re-run
with same plan+seed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import yaml

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.dsp import (
    apply_fade,
    apply_gain_db,
    first_onset_index,
    mix_layers,
    pitch_shift_resample,
    rng_for,
    synth_crackle_tail,
    synth_debris,
    synth_fire_bed,
    synth_impact,
    synth_sub_boom,
    write_wav,
)
from lib.ledger import file_sha256, row_for_path
from lib.metrics import analyze_file, evaluate_profile, load_audio, load_profiles
from lib.paths import is_quarantine_path, path_is_allowed_source, resolve_sfx_lib
from sfx_manifest import LayerProvenance, OutputRow, new_manifest


DSP_MAP = {
    "sub_boom": synth_sub_boom,
    "crackle_tail": synth_crackle_tail,
    "impact": synth_impact,
    "debris": synth_debris,
    "fire_bed": synth_fire_bed,
}


def load_plan(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def validate_plan(plan: dict, sfx_lib: Path) -> list[str]:
    errs: list[str] = []
    if "layers" not in plan or not plan["layers"]:
        errs.append("no layers")
    if "family" not in plan:
        errs.append("no family block")
    if "target" not in plan:
        errs.append("no target block")
    for i, layer in enumerate(plan.get("layers", [])):
        cents = float(layer.get("pitch_cents", 0) or 0)
        if abs(cents) > 150:
            errs.append(f"layer[{i}] pitch_cents out of bounds: {cents}")
        src = layer.get("source")
        if isinstance(src, str):
            p = Path(src)
            if not p.is_absolute():
                # try relative to sfx_lib and plan dir later
                continue
            if is_quarantine_path(p, sfx_lib):
                errs.append(f"layer[{i}] quarantine path refused: {p}")
        elif isinstance(src, dict) and src.get("kind") == "file":
            p = Path(src.get("path", ""))
            if p.is_absolute() and is_quarantine_path(p, sfx_lib):
                errs.append(f"layer[{i}] quarantine path refused: {p}")
    return errs


def resolve_source(
    src,
    sfx_lib: Path,
    plan_dir: Path,
    sr: int,
    seed: int,
) -> tuple[np.ndarray, str, str]:
    """Return (audio, resolved_path_or_dsp, license)."""
    if isinstance(src, dict):
        kind = src.get("kind", "file")
        if kind == "dsp":
            name = src.get("dsp", "sub_boom")
            params = dict(src.get("params") or {})
            params.setdefault("sr", sr)
            params.setdefault("seed", seed)
            fn = DSP_MAP.get(name)
            if not fn:
                raise ValueError(f"unknown dsp: {name}")
            # map common keys
            if "duration_s" not in params and "dur" in params:
                params["duration_s"] = params.pop("dur")
            # filter kwargs to known
            import inspect

            sig = inspect.signature(fn)
            kwargs = {k: v for k, v in params.items() if k in sig.parameters}
            audio = fn(**kwargs)
            return audio, f"dsp:{name}", "procedural-seed"
        path = src.get("path", "")
        src = path

    p = Path(str(src))
    candidates = []
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.append(sfx_lib / p)
        candidates.append(plan_dir / p)
        candidates.append(Path(p))
    found = None
    for c in candidates:
        if c.exists():
            found = c.resolve()
            break
    if found is None:
        raise FileNotFoundError(f"layer source not found: {src}")
    if is_quarantine_path(found, sfx_lib):
        raise PermissionError(f"quarantine path refused: {found}")
    # Structural license gate: file sources MUST be ledgered (no path-segment invent)
    row = row_for_path(sfx_lib, found)
    if row is None:
        raise PermissionError(f"non-ledgered source refused: {found}")
    if not path_is_allowed_source(found, sfx_lib):
        raise PermissionError(f"disallowed source root: {found}")
    lic = (row.license or "").strip()
    if not lic:
        raise PermissionError(f"ledger row missing license: {found}")
    data, file_sr, _ = load_audio(found)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if file_sr != sr:
        # simple resample
        n = int(len(data) * sr / file_sr)
        idx = np.linspace(0, len(data) - 1, max(1, n))
        data = np.interp(idx, np.arange(len(data)), data)
    return np.asarray(data, dtype=np.float64), str(found), lic


def prepare_layer_audio(
    audio: np.ndarray,
    sr: int,
    layer: dict,
    event_t_ms: float,
    jitter_gain: float,
    jitter_pitch: float,
    jitter_offset_ms: float,
    lock_pitch: bool,
) -> tuple[np.ndarray, int, dict]:
    role = layer.get("role", "body")
    gain = float(layer.get("gain_db", 0)) + jitter_gain
    cents = float(layer.get("pitch_cents", 0) or 0)
    if lock_pitch and role == "transient":
        cents = 0.0
    else:
        cents = cents + jitter_pitch
    cents = max(-150.0, min(150.0, cents))
    y = pitch_shift_resample(audio, cents)
    y = apply_gain_db(y, gain)
    y = apply_fade(
        y,
        sr,
        float(layer.get("fade_in_ms", 0) or 0),
        float(layer.get("fade_out_ms", 0) or 0),
    )
    onset = first_onset_index(y, sr)
    # align onset to event time + offsets
    target = int(sr * (event_t_ms + float(layer.get("offset_ms", 0) or 0) + jitter_offset_ms) / 1000.0)
    start = target - onset
    meta = {
        "role": role,
        "gain_db": gain,
        "pitch_cents": cents,
        "start_sample": start,
        "onset": onset,
    }
    return y, start, meta


def assemble(
    plan: dict,
    plan_path: Path,
    out_dir: Path,
    sfx_lib: Path,
    write_stems: bool = True,
    run_qa: bool = True,
) -> dict:
    errs = validate_plan(plan, sfx_lib)
    if errs:
        raise ValueError("plan invalid: " + "; ".join(errs))

    name = plan.get("name", "family")
    seed = int(plan.get("seed", 0))
    sr = int(plan.get("target", {}).get("sample_rate", 48000))
    family = plan.get("family", {})
    n_var = int(family.get("variant_count", 4))
    jitter = family.get("jitter") or {}
    j_gain = float(jitter.get("gain_db", 0.5))
    j_pitch = float(jitter.get("pitch_cents", 20))
    j_off = float(jitter.get("offset_ms", 5))
    lock_transient = bool(family.get("lock_transient_pitch", True))
    events = plan.get("event_map") or [{"t_ms": 0.0, "label": "hit"}]
    profile_name = plan.get("profile", "impact")
    profiles = load_profiles()
    profile = profiles.get(profile_name, profiles.get("default", {}))

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stems_dir = out_dir / "stems"
    if write_stems:
        stems_dir.mkdir(exist_ok=True)

    # load raw sources once
    loaded = []
    layer_prov: list[LayerProvenance] = []
    for i, layer in enumerate(plan["layers"]):
        audio, resolved, lic = resolve_source(
            layer["source"], sfx_lib, plan_path.parent, sr, seed + i * 17
        )
        loaded.append((layer, audio, resolved, lic))
        layer_prov.append(
            LayerProvenance(
                role=layer.get("role", "body"),
                source=resolved,
                license=lic,
                gain_db=float(layer.get("gain_db", 0) or 0),
                pitch_cents=float(layer.get("pitch_cents", 0) or 0),
                offset_ms=float(layer.get("offset_ms", 0) or 0),
            )
        )

    # estimate duration
    target_dur = plan.get("target", {}).get("duration_s")
    if target_dur:
        total = int(float(target_dur) * sr)
    else:
        max_end = 0
        for layer, audio, _, _ in loaded:
            ei = int(layer.get("event_index", 0) or 0)
            t_ms = float(events[min(ei, len(events) - 1)]["t_ms"])
            max_end = max(max_end, int(sr * (t_ms / 1000.0)) + len(audio) + sr // 10)
        total = max(max_end, int(0.5 * sr))

    manifest = new_manifest(name, seed, plan_path)
    manifest.layers = layer_prov
    outputs_meta = []
    qa_failures = []

    def render_one(variant_idx: int | None) -> tuple[np.ndarray, list[tuple[str, np.ndarray]]]:
        g = rng_for(seed + (0 if variant_idx is None else (variant_idx + 1) * 9973))
        pieces = []
        stem_parts: list[tuple[str, np.ndarray]] = []
        for layer, audio, resolved, lic in loaded:
            if variant_idx is None:
                jg = jp = jo = 0.0
            else:
                # transient: no pitch jitter if locked
                role = layer.get("role", "body")
                jg = float(g.uniform(-j_gain, j_gain))
                if lock_transient and role == "transient":
                    jp = 0.0
                else:
                    jp = float(g.uniform(-j_pitch, j_pitch))
                jo = float(g.uniform(-j_off, j_off))
            ei = int(layer.get("event_index", 0) or 0)
            t_ms = float(events[min(ei, len(events) - 1)]["t_ms"])
            y, start, meta = prepare_layer_audio(
                audio, sr, layer, t_ms, jg, jp, jo, lock_transient
            )
            pieces.append((y, start))
            if write_stems and variant_idx is None:
                stem = np.zeros(total)
                s0 = max(0, start)
                s1 = min(total, start + len(y))
                if s1 > s0:
                    stem[s0:s1] = y[: s1 - s0]
                stem_parts.append((layer.get("role", "layer"), stem))
        mixed = mix_layers(pieces, total)
        # peak normalize to target
        peak_db = float(plan.get("target", {}).get("peak_dbfs", -1.0))
        peak = np.max(np.abs(mixed)) if mixed.size else 0.0
        if peak > 0:
            target_lin = 10.0 ** (peak_db / 20.0)
            mixed = mixed * (target_lin / peak)
        return mixed, stem_parts

    # master
    master, stems = render_one(None)
    master_path = out_dir / f"{name}_master.wav"
    write_wav(master_path, master, sr)
    if write_stems:
        for role, stem in stems:
            sp = stems_dir / f"{name}_stem_{role}.wav"
            write_wav(sp, stem, sr)
            sh = file_sha256(sp)
            # Stems are partial layers; do not gate the family on stem profile QA
            qa_ok, mdict = _qa(sp, profile, False)
            manifest.outputs.append(
                OutputRow(
                    name=sp.name,
                    path=str(sp),
                    role="stem",
                    sha256=sh,
                    qa_pass=qa_ok,
                    metrics=mdict,
                )
            )

    sh = file_sha256(master_path)
    qa_ok, mdict = _qa(master_path, profile, run_qa)
    manifest.outputs.append(
        OutputRow(
            name=master_path.name,
            path=str(master_path),
            role="master",
            sha256=sh,
            qa_pass=qa_ok,
            metrics=mdict,
        )
    )
    if run_qa and not qa_ok:
        qa_failures.append(master_path.name)
    outputs_meta.append(str(master_path))

    for vi in range(n_var):
        audio, _ = render_one(vi)
        vp = out_dir / f"{name}_v{vi:02d}.wav"
        write_wav(vp, audio, sr)
        sh = file_sha256(vp)
        qa_ok, mdict = _qa(vp, profile, run_qa)
        manifest.outputs.append(
            OutputRow(
                name=vp.name,
                path=str(vp),
                role="variant",
                sha256=sh,
                qa_pass=qa_ok,
                metrics=mdict,
            )
        )
        if run_qa and not qa_ok:
            qa_failures.append(vp.name)
        outputs_meta.append(str(vp))

    man_path = out_dir / "manifest.json"
    manifest.write(man_path)

    # copy plan
    (out_dir / "plan.yaml").write_text(
        yaml.safe_dump(plan, sort_keys=False), encoding="utf-8"
    )

    result = {
        "name": name,
        "out_dir": str(out_dir),
        "master": str(master_path),
        "variants": n_var,
        "manifest": str(man_path),
        "output_count": len(manifest.outputs),
        "qa_failures": qa_failures,
        "pass": len(qa_failures) == 0,
    }
    if qa_failures:
        raise RuntimeError(f"QA failed on: {qa_failures}")
    return result


def _qa(path: Path, profile: dict, run: bool) -> tuple[bool | None, dict]:
    if not run:
        return None, {}
    m = analyze_file(path)
    ok, failed = evaluate_profile(m, profile)
    d = m.to_dict()
    d["failed_checks"] = failed
    return ok, d


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sfx-lib", default=None)
    ap.add_argument("--no-stems", action="store_true")
    ap.add_argument("--no-qa", action="store_true")
    ap.add_argument("--event-map", default=None, help="override event map yaml/json")
    args = ap.parse_args(argv)

    plan_path = Path(args.plan)
    plan = load_plan(plan_path)
    if args.event_map:
        em = load_plan(Path(args.event_map))
        if isinstance(em, dict) and "event_map" in em:
            plan["event_map"] = em["event_map"]
        elif isinstance(em, list):
            plan["event_map"] = em
        else:
            plan["event_map"] = em.get("events", em)
    lib = resolve_sfx_lib(args.sfx_lib)
    try:
        result = assemble(
            plan,
            plan_path,
            Path(args.out),
            lib,
            write_stems=not args.no_stems,
            run_qa=not args.no_qa,
        )
    except Exception as e:
        print(json.dumps({"pass": False, "error": str(e)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
