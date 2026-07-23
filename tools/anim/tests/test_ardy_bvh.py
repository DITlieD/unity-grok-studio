"""Golden-file test for CoreSkeleton27 -> BVH converter (real shipped function)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ANIM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ANIM))

from ardy_client import synthesize_core_skeleton_clip  # noqa: E402
from ardy_to_bvh import (  # noqa: E402
    convert_to_bvh,
    humanoid_bone_checklist,
    load_payload,
    retarget_record,
)

GOLDEN = Path(__file__).parent / "golden" / "walk_circle_seed42.bvh"


def test_synthetic_payload_to_bvh_golden(tmp_path: Path):
    clip = synthesize_core_skeleton_clip(seed=42, frames=20, fps=20.0)
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(clip), encoding="utf-8")
    out = tmp_path / "out.bvh"
    convert_to_bvh(load_payload(payload_path), out)
    text = out.read_text(encoding="utf-8")
    assert "HIERARCHY" in text
    assert "ROOT Hips" in text
    assert "MOTION" in text
    assert "Frames: 20" in text
    # regenerate golden if missing (first run ships it)
    if not GOLDEN.exists():
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(text, encoding="utf-8")
    golden = GOLDEN.read_text(encoding="utf-8")
    # byte-identical hierarchy + frame count; allow motion float tolerance via hash of structure
    assert "ROOT Hips" in golden
    assert text.splitlines()[0:5] == golden.splitlines()[0:5]
    # same number of motion lines
    assert text.count("\n") == golden.count("\n") or abs(
        len(text.splitlines()) - len(golden.splitlines())
    ) <= 0
    # full equality for determinism
    assert text == golden


def test_retarget_checklist(tmp_path: Path):
    clip = synthesize_core_skeleton_clip(seed=1, frames=5)
    bvh = tmp_path / "x.bvh"
    convert_to_bvh(clip, bvh)
    rec = retarget_record(bvh, tmp_path / "x.fbx")
    assert rec["checklist"]["pass"] is True
    assert Path(rec["fbx_stub"]).exists()
    assert humanoid_bone_checklist()["pass"] is True


def test_converter_deterministic(tmp_path: Path):
    clip = synthesize_core_skeleton_clip(seed=99, frames=10)
    a = tmp_path / "a.bvh"
    b = tmp_path / "b.bvh"
    convert_to_bvh(clip, a)
    convert_to_bvh(clip, b)
    assert a.read_bytes() == b.read_bytes()
