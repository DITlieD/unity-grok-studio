"""End-to-end tests that drive shipped sfx tools and assert real wavs.

No mocks of units under test. Fixtures and SFX_LIB may be written by the test
bootstrap using shipped seed_library / dsp helpers.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SFX_ROOT = Path(__file__).resolve().parents[1]
PY = SFX_ROOT / ".venv" / "bin" / "python"
if not PY.exists():
    PY = Path(sys.executable)

# Isolate library under tools/sfx test area when env not set by runner
TEST_LIB = SFX_ROOT / "_test_sfx_lib"
OUT = SFX_ROOT / "_test_out"


def run(args: list[str], check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    e = os.environ.copy()
    e["SFX_LIB"] = str(TEST_LIB)
    if env:
        e.update(env)
    return subprocess.run(
        [str(PY), *args],
        cwd=str(SFX_ROOT),
        capture_output=True,
        text=True,
        env=e,
        check=check,
    )


@pytest.fixture(scope="module", autouse=True)
def bootstrap_lib():
    TEST_LIB.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    r = run(["seed_library.py", "--sfx-lib", str(TEST_LIB), "--force"])
    assert r.returncode == 0, r.stderr + r.stdout
    r = run(["sfx_index_build.py", "--sfx-lib", str(TEST_LIB)])
    assert r.returncode == 0, r.stderr + r.stdout
    yield


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def test_analyze_clean_exit0_json_png():
    wav = SFX_ROOT / "_fixtures" / "clean_impact.wav"
    assert wav.exists()
    r = run(
        [
            "analyze_audio.py",
            "--file",
            str(wav),
            "--profile",
            "impact",
            "--json",
            "--png",
            str(OUT / "clean.qa.png"),
        ]
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["pass"] is True
    assert data["metrics"]["duration_s"] > 0
    assert data["finite"] is True
    assert (OUT / "clean.qa.png").exists()
    assert (OUT / "clean.qa.png").stat().st_size > 100


def test_analyze_clipped_exit1_names_clipping():
    wav = SFX_ROOT / "_fixtures" / "clipped_tone.wav"
    r = run(
        [
            "analyze_audio.py",
            "--file",
            str(wav),
            "--profile",
            "impact",
            "--json",
            "--no-png",
        ],
        check=False,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    data = json.loads(r.stdout)
    assert data["pass"] is False
    assert "clipping" in data["failed_checks"]
    assert data["metrics"]["clip_samples"] > 0


def test_analyze_missing_exit2():
    r = run(
        ["analyze_audio.py", "--file", "/no/such/file.wav", "--json", "--no-png"],
        check=False,
    )
    assert r.returncode == 2


def test_ledger_matches_seed_wavs():
    ledger = TEST_LIB / "ledger.tsv"
    assert ledger.exists()
    lines = [ln for ln in ledger.read_text().splitlines() if ln.strip()][1:]
    wavs = list((TEST_LIB / "seed").rglob("*.wav"))
    assert len(lines) == len(wavs)
    assert len(wavs) >= 10
    for w in wavs:
        assert w.stat().st_size > 100


def test_search_returns_licensed_candidates():
    r = run(
        [
            "sfx_search.py",
            "--sfx-lib",
            str(TEST_LIB),
            "--query",
            "heavy wooden door slam close dry under 1s",
            "--license",
            "allowed",
            "--max-dur",
            "2",
            "--json",
        ]
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["count"] >= 1
    for row in data["results"]:
        assert row["license"]
        assert Path(row["path"]).exists()
        assert Path(row["path"]).stat().st_size > 0
        assert row["duration_s"] > 0
        assert row["score"] >= 0


def test_search_refuses_unlicensed_rows_structurally():
    """Drop a wav with no ledger row — search must never return it."""
    rogue = TEST_LIB / "seed" / "ROGUE_not_in_ledger.wav"
    # copy bytes from a real seed without ledgering
    src = next((TEST_LIB / "seed").glob("*.wav"))
    rogue.write_bytes(src.read_bytes())
    try:
        r = run(
            [
                "sfx_search.py",
                "--sfx-lib",
                str(TEST_LIB),
                "--query",
                "ROGUE_not_in_ledger",
                "--license",
                "any",
                "--json",
                "--rebuild-index",
            ]
        )
        data = json.loads(r.stdout)
        for row in data["results"]:
            assert "ROGUE" not in row["path"]
    finally:
        rogue.unlink(missing_ok=True)
        run(["sfx_index_build.py", "--sfx-lib", str(TEST_LIB)])


def test_assemble_refuses_non_ledgered_seed_file():
    """Criterion 2: assemble must refuse non-ledgered paths under SFX_LIB/seed."""
    import yaml
    import shutil

    unled = TEST_LIB / "seed" / "UNLEDGERED_assemble_probe.wav"
    src = next((TEST_LIB / "seed").glob("IMPACT_*.wav"))
    unled.write_bytes(src.read_bytes())
    plan = {
        "version": 0,
        "name": "unledgered_probe",
        "profile": "impact",
        "seed": 1,
        "event_map": [{"t_ms": 0, "label": "e0"}],
        "layers": [
            {
                "role": "transient",
                "source": "seed/UNLEDGERED_assemble_probe.wav",
                "gain_db": 0,
            }
        ],
        "family": {"variant_count": 1, "lock_transient_pitch": True},
        "target": {"peak_dbfs": -1.0, "sample_rate": 48000, "duration_s": 0.5},
    }
    plan_path = OUT / "unledgered_plan.yaml"
    out_dir = OUT / "unledgered_family"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    plan_path.write_text(yaml.safe_dump(plan), encoding="utf-8")
    try:
        r = run(
            [
                "assemble_sfx.py",
                "--plan",
                str(plan_path),
                "--out",
                str(out_dir),
                "--sfx-lib",
                str(TEST_LIB),
            ],
            check=False,
        )
        assert r.returncode != 0, r.stdout + r.stderr
        blob = (r.stderr + r.stdout).lower()
        assert "non-ledgered" in blob or "refused" in blob or "ledger" in blob
        master = out_dir / "unledgered_probe_master.wav"
        assert not master.exists(), "must not write master from non-ledgered source"
    finally:
        unled.unlink(missing_ok=True)


def test_generate_dsp_placeholder_never_labeled_stable_audio():
    out = OUT / "gen_label_check"
    r = run(
        [
            "sfx_generate.py",
            "--provider",
            "stable_audio_3_small_sfx",
            "--prompt",
            "crackle",
            "--dur",
            "0.4",
            "--seed",
            "3",
            "--count",
            "1",
            "--allow-dsp-placeholder",
            "--out",
            str(out),
            "--sfx-lib",
            str(TEST_LIB),
        ]
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data.get("backend") == "dsp_placeholder"
    prov = json.loads(Path(data["items"][0]["provenance"]).read_text())
    assert prov["backend"] == "dsp_placeholder"
    assert prov["backend"] != "stable_audio"


def test_generate_refuses_noncommercial():
    r = run(
        [
            "sfx_generate.py",
            "--provider",
            "research_sony_woosh",
            "--prompt",
            "short crackle",
            "--dur",
            "0.5",
            "--count",
            "1",
            "--sfx-lib",
            str(TEST_LIB),
        ],
        check=False,
    )
    assert r.returncode != 0
    blob = (r.stderr + r.stdout).lower()
    assert "noncommercial" in blob or "refused" in blob


def test_generate_parked_or_placeholder():
    r = run(
        [
            "sfx_generate.py",
            "--provider",
            "stable_audio_3_small_sfx",
            "--prompt",
            "short ionized crackle decay dry",
            "--dur",
            "0.8",
            "--seed",
            "7",
            "--count",
            "2",
            "--sfx-lib",
            str(TEST_LIB),
        ],
        check=False,
    )
    # parked without placeholder => 3; with default providers status parked
    assert r.returncode == 3, r.stdout + r.stderr
    data = json.loads(r.stdout)
    assert data.get("status") == "parked" or data.get("abort")


def test_generate_dsp_placeholder_writes_real_wavs():
    out = OUT / "gen_placeholder"
    r = run(
        [
            "sfx_generate.py",
            "--provider",
            "stable_audio_3_small_sfx",
            "--prompt",
            "crackle tail dry",
            "--dur",
            "0.6",
            "--seed",
            "11",
            "--count",
            "2",
            "--allow-dsp-placeholder",
            "--out",
            str(out),
            "--sfx-lib",
            str(TEST_LIB),
        ]
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["count"] == 2
    for item in data["items"]:
        wav = Path(item["wav"])
        assert wav.exists() and wav.stat().st_size > 100
        assert Path(item["provenance"]).exists()
        # analyze should decode
        ar = run(
            ["analyze_audio.py", "--file", str(wav), "--profile", "default", "--json", "--no-png"],
            check=False,
        )
        assert ar.returncode in (0, 1)
        metrics = json.loads(ar.stdout)["metrics"]
        assert metrics["duration_s"] > 0
        assert metrics["sample_rate"] > 0


def test_assemble_family_real_wavs_and_determinism():
    plan = SFX_ROOT / "plans" / "firework_burst_family.yaml"
    # rewrite plan sources to test lib — plan uses seed/ relative paths
    out1 = OUT / "family_run1"
    out2 = OUT / "family_run2"
    for d in (out1, out2):
        if d.exists():
            import shutil

            shutil.rmtree(d)

    r1 = run(
        [
            "assemble_sfx.py",
            "--plan",
            str(plan),
            "--out",
            str(out1),
            "--sfx-lib",
            str(TEST_LIB),
        ]
    )
    assert r1.returncode == 0, r1.stderr + r1.stdout
    res1 = json.loads(r1.stdout)
    assert res1["pass"] is True
    master = Path(res1["master"])
    assert master.exists() and master.stat().st_size > 500
    variants = list(out1.glob("firework_burst_v*.wav"))
    assert len(variants) == 8
    for v in variants:
        assert v.stat().st_size > 500
    man = json.loads((out1 / "manifest.json").read_text())
    assert man["output_count"] == len(man["outputs"])
    assert man["output_count"] >= 9  # master + 8 variants (+ stems)
    # physical layers from library
    sources = [L["source"] for L in man["layers"]]
    assert any("FIRE_Transient" in s or "seed/" in s for s in sources)
    assert any(L["license"] in ("studio-seed", "procedural-seed", "generated") for L in man["layers"])

    r2 = run(
        [
            "assemble_sfx.py",
            "--plan",
            str(plan),
            "--out",
            str(out2),
            "--sfx-lib",
            str(TEST_LIB),
        ]
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout
    # byte-identical masters and variants
    for name in ["firework_burst_master.wav"] + [f"firework_burst_v{i:02d}.wav" for i in range(8)]:
        a = out1 / name
        b = out2 / name
        assert a.exists() and b.exists()
        assert sha256(a) == sha256(b), name


def test_audition_report_exists():
    family = OUT / "family_run1"
    if not family.exists():
        pytest.skip("assemble first")
    report_out = OUT / "report" / "audition_report.html"
    old = Path(
        "$UNITY_GROK_ROOT/fixtures/beep.wav"
    )
    args = [
        "render_audition_report.py",
        "--family-dir",
        str(family),
        "--out",
        str(report_out),
    ]
    if old.exists():
        args += ["--compare", str(old)]
    r = run(args)
    assert r.returncode == 0, r.stderr + r.stdout
    assert report_out.exists()
    body = report_out.read_text(encoding="utf-8")
    assert "Verdict" in body or "verdict" in body.lower()
    assert "firework" in body.lower() or "Layer" in body
    md = report_out.with_suffix(".md")
    assert md.exists()


def test_voice_timing_event_map_and_assemble():
    # build a guide wav with multiple impacts
    sys.path.insert(0, str(SFX_ROOT))
    from lib.dsp import synth_impact, write_wav
    import numpy as np

    sr = 48000
    a = synth_impact(sr, 0.2, seed=1)
    b = synth_impact(sr, 0.2, seed=2)
    c = synth_impact(sr, 0.2, seed=3)
    gap = np.zeros(int(0.15 * sr))
    guide = np.concatenate([a, gap, b, gap, c])
    gpath = OUT / "guide.wav"
    write_wav(gpath, guide, sr)

    emap = OUT / "event_map.yaml"
    r = run(
        [
            "voice_timing.py",
            "--file",
            str(gpath),
            "--json",
            "--out",
            str(emap),
            "--mode",
            "envelope",
        ]
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(r.stdout)
    assert data["onset_count"] >= 1
    assert emap.exists()

    # minimal plan consuming event map
    plan = {
        "version": 0,
        "name": "voice_timed",
        "profile": "impact",
        "seed": 9,
        "event_map": [{"t_ms": 0, "label": "e0"}],
        "layers": [
            {
                "role": "transient",
                "source": "seed/IMPACT_GenericThump_01.wav",
                "gain_db": 0,
            }
        ],
        "family": {"variant_count": 2, "lock_transient_pitch": True},
        "target": {"peak_dbfs": -1.0, "sample_rate": 48000, "duration_s": 0.8},
    }
    plan_path = OUT / "voice_plan.yaml"
    import yaml

    plan_path.write_text(yaml.safe_dump(plan), encoding="utf-8")
    out = OUT / "voice_family"
    r2 = run(
        [
            "assemble_sfx.py",
            "--plan",
            str(plan_path),
            "--event-map",
            str(emap),
            "--out",
            str(out),
            "--sfx-lib",
            str(TEST_LIB),
        ]
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout
    assert (out / "voice_timed_master.wav").exists()
    assert (out / "voice_timed_master.wav").stat().st_size > 100


def test_unity_family_player_exists():
    cs = Path(
        "$UNITY_GROK_ROOT/fixtures/CleanSample.cs"
    )
    assert cs.exists()
    text = cs.read_text(encoding="utf-8")
    assert "class SfxFamilyPlayer" in text
    assert "PlayOneShot" in text
    assert "avoidRepeatLastN" in text


def test_skill_doctrine():
    skill = Path(
        "$UNITY_GROK_ROOT/plugin/skills/sfx-forge/SKILL.md"
    )
    text = skill.read_text(encoding="utf-8")
    assert "RETRIEVAL BEFORE GENERATION" in text or "retrieval" in text.lower()
    assert "NEVER declares audio done" in text or "never declares audio done" in text.lower()
    assert "OFF by default" in text or "off by default" in text.lower()
    assert "analyze_audio.py" in text
    assert "assemble_sfx.py" in text
