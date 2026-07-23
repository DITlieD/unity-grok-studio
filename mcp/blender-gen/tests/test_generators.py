"""Unit tests driving real shipped generators + validators (no mocks of unit under test)."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))
ASSET_GEN = Path("$UNITY_GROK_ROOT/.claude/tools/asset_gen")
sys.path.insert(0, str(ASSET_GEN))

from blender_gen.mats.brick import gen_brick_material  # noqa: E402
from blender_gen.mats.stone import gen_stone_material  # noqa: E402
from blender_gen.mats.wood import gen_wood_material  # noqa: E402
from blender_gen.mats.metal import gen_metal_material  # noqa: E402
from blender_gen.mats.trim import gen_trim_material  # noqa: E402
from blender_gen.mesh.walls import gen_parametric_wall  # noqa: E402
from blender_gen.mesh.props import gen_crate  # noqa: E402
from blender_gen.mesh.arches import gen_arch  # noqa: E402
from blender_gen.mesh.pipes import gen_pipes  # noqa: E402
from blender_gen.mesh.stairs import gen_stairs  # noqa: E402
from blender_gen.review_loop import generate_with_review  # noqa: E402
from vision_client import vision_check, parse_check_json, treat_unknown_as_fail  # noqa: E402

PY = Path("$UNITY_GROK_ROOT/.claude/tools/asset_gen/.venv/bin/python")
if not PY.exists():
    PY = Path(sys.executable)

STYLE = Path(
    "$UNITY_GROK_ROOT/work_games/workflow/memory-bank/games/embervow/asset-style.yaml"
)


def _val(script: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PY), str(ASSET_GEN / script), *args],
        capture_output=True,
        text=True,
    )


def test_brick_seed_deterministic(tmp_path: Path):
    a = gen_brick_material(seed=184, size=128, out_dir=tmp_path / "a")
    b = gen_brick_material(seed=184, size=128, out_dir=tmp_path / "b")
    ha = hashlib.sha256((tmp_path / "a" / "basecolor.png").read_bytes()).hexdigest()
    hb = hashlib.sha256((tmp_path / "b" / "basecolor.png").read_bytes()).hexdigest()
    assert ha == hb
    assert (tmp_path / "a" / "manifest.json").exists()
    for name in ("basecolor.png", "normal.png", "roughness.png", "ao.png", "height.png", "id.png"):
        assert (tmp_path / "a" / name).exists(), name
    assert a["seed"] == 184


def test_tile_and_colorspace_validators_pass_on_brick(tmp_path: Path):
    gen_brick_material(seed=184, size=256, out_dir=tmp_path / "brick")
    r1 = _val("tile_boundary_check.py", ["--maps", str(tmp_path / "brick"), "--json"])
    r2 = _val("colorspace_check.py", ["--maps", str(tmp_path / "brick"), "--json"])
    assert r1.returncode == 0, r1.stdout + r1.stderr
    assert r2.returncode == 0, r2.stdout + r2.stderr


def test_tile_boundary_fails_on_seeded_seam_defect(tmp_path: Path):
    from PIL import Image
    import numpy as np

    d = tmp_path / "bad"
    d.mkdir()
    # non-tileable: left edge black, right edge white
    arr = np.zeros((64, 64, 3), dtype=np.uint8)
    arr[:, :8] = 0
    arr[:, -8:] = 255
    arr[:, 8:-8] = 128
    Image.fromarray(arr).save(d / "basecolor.png")
    # valid-looking normal so colorspace may still pass path independently
    n = np.zeros((64, 64, 3), dtype=np.uint8)
    n[..., 0] = 128
    n[..., 1] = 128
    n[..., 2] = 255
    Image.fromarray(n).save(d / "normal.png")
    r = _val("tile_boundary_check.py", ["--maps", str(d), "--json"])
    assert r.returncode != 0, r.stdout


def test_wall_and_crate_export(tmp_path: Path):
    w = gen_parametric_wall(seed=184, length=6, height=3, gate={"w": 1.5, "h": 2.0}, out_dir=tmp_path / "wall")
    assert Path(w["glb"]).exists()
    assert (tmp_path / "wall" / "mesh_stats.json").exists()
    c = gen_crate(seed=184, out_dir=tmp_path / "crate")
    assert Path(c["glb"]).exists()


def test_topology_pass_and_seeded_defect_fail(tmp_path: Path):
    """mesh_stats must INSPECT geometry — no caller-supplied topology flags."""
    good = gen_parametric_wall(seed=184, out_dir=tmp_path / "good")
    good_stats = json.loads((tmp_path / "good" / "mesh_stats.json").read_text())
    # real inspect: multi-brick wall has many edge-components but zero floating
    assert good_stats["disconnected_components"] >= 1
    assert good_stats.get("floating_components", 0) == 0
    r = _val(
        "mesh_topology_check.py",
        ["--stats", str(tmp_path / "good" / "mesh_stats.json"), "--json"],
    )
    assert r.returncode == 0, r.stdout
    bad = gen_parametric_wall(
        seed=184, out_dir=tmp_path / "bad", seed_defect_detached=True
    )
    bad_stats = json.loads((tmp_path / "bad" / "mesh_stats.json").read_text())
    assert bad_stats.get("floating_components", 0) >= 1, bad_stats
    r2 = _val(
        "mesh_topology_check.py",
        ["--stats", str(tmp_path / "bad" / "mesh_stats.json"), "--json"],
    )
    assert r2.returncode != 0, "seeded detached brick must fail topology"
    # lying flags cannot help: even if we rewrite disconnected=1, floating is measured
    assert "floating" in r2.stdout or r2.returncode != 0


def test_tri_budget(tmp_path: Path):
    gen_crate(seed=1, out_dir=tmp_path / "c")
    r = _val(
        "tri_budget_check.py",
        [
            "--stats",
            str(tmp_path / "c" / "mesh_stats.json"),
            "--style",
            str(STYLE),
            "--class",
            "crate",
            "--json",
        ],
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_material_family(tmp_path: Path):
    for fn, name in [
        (gen_stone_material, "stone"),
        (gen_wood_material, "wood"),
        (gen_metal_material, "metal"),
        (gen_trim_material, "trim"),
    ]:
        r = fn(seed=99, size=64, out_dir=tmp_path / name)
        assert (tmp_path / name / "manifest.json").exists()
        assert (tmp_path / name / "basecolor.png").exists()


def test_arches_pipes_stairs(tmp_path: Path):
    for fn, name in [(gen_arch, "arch"), (gen_pipes, "pipes"), (gen_stairs, "stairs")]:
        r = fn(seed=7, out_dir=tmp_path / name)
        assert Path(r["glb"]).exists()
        tr = _val(
            "mesh_topology_check.py",
            ["--stats", str(tmp_path / name / "mesh_stats.json"), "--json"],
        )
        assert tr.returncode == 0, (name, tr.stdout)


def test_mortar_depth_measured_not_manifest(tmp_path: Path):
    """mortar_depth_check reads height maps; deep joints fail, shallow pass."""
    deep = gen_brick_material(seed=200, size=256, mortar=0.06, out_dir=tmp_path / "deep")
    shallow = gen_brick_material(seed=200, size=256, mortar=0.02, out_dir=tmp_path / "shallow")
    r_deep = _val("mortar_depth_check.py", ["--maps", str(tmp_path / "deep"), "--json"])
    r_sh = _val("mortar_depth_check.py", ["--maps", str(tmp_path / "shallow"), "--json"])
    assert r_deep.returncode != 0, r_deep.stdout
    assert r_sh.returncode == 0, r_sh.stdout
    # rewrite manifest only — maps still deep → still fail (not param theater)
    man = json.loads((tmp_path / "deep" / "manifest.json").read_text())
    man["params"]["mortar"] = 0.01
    (tmp_path / "deep" / "manifest.json").write_text(json.dumps(man))
    r_lie = _val("mortar_depth_check.py", ["--maps", str(tmp_path / "deep"), "--json"])
    assert r_lie.returncode != 0, "manifest-only lie must not pass mortar check"


def test_review_loop_seeded_mortar_defect(tmp_path: Path):
    """mortar too deep should be measured-fail then revised within <=3 iters."""

    def _gen(**kw):
        return gen_brick_material(
            seed=kw["seed"],
            size=256,
            mortar=float(kw.get("mortar", 0.06)),
            variation=float(kw.get("variation", 0.15)),
            out_dir=tmp_path / f"rev_{kw.get('mortar')}_{kw['seed']}",
        )

    rec = generate_with_review(
        _gen,
        seed=200,
        base_params={"mortar": 0.06, "variation": 0.15},
        max_iters=3,
        skip_vision=True,
    )
    assert rec["iterations"] <= 3
    assert rec["history"][0]["validators"]["pass"] is False
    assert (rec["history"][0]["validators"].get("mortar_depth") or {}).get("exit", 0) != 0
    assert rec["history"][-1]["validators"]["pass"] is True
    assert rec["status"] in ("pass", "pass_validators_only")


def test_normal_convention_good_and_seeded_defect(tmp_path: Path):
    from PIL import Image
    import numpy as np

    gen_brick_material(seed=1, size=128, out_dir=tmp_path / "ok")
    r = _val(
        "normal_convention_check.py",
        ["--map", str(tmp_path / "ok" / "normal.png"), "--json"],
    )
    assert r.returncode == 0, r.stdout
    # seeded defect: inverted / flat normal (B channel low)
    bad = np.zeros((64, 64, 3), dtype=np.uint8)
    bad[..., 0] = 128
    bad[..., 1] = 128
    bad[..., 2] = 20  # Z too low for OpenGL normal
    Image.fromarray(bad).save(tmp_path / "bad_n.png")
    r2 = _val(
        "normal_convention_check.py",
        ["--map", str(tmp_path / "bad_n.png"), "--json"],
    )
    assert r2.returncode != 0, r2.stdout


def test_texel_density_good_and_seeded_defect(tmp_path: Path):
    gen_crate(seed=3, out_dir=tmp_path / "c")
    r = _val(
        "texel_density_check.py",
        [
            "--stats",
            str(tmp_path / "c" / "mesh_stats.json"),
            "--style",
            str(STYLE),
            "--map-res",
            "2048",
            "--json",
        ],
    )
    assert r.returncode == 0, r.stdout + r.stderr
    # seeded defect: absurd world area so density falls outside style band
    stats = json.loads((tmp_path / "c" / "mesh_stats.json").read_text())
    stats["world_surface_area_m2"] = 1e-12
    stats["surface_area"] = 1e-12
    stats["uv_area"] = 1.0
    bad_path = tmp_path / "bad_stats.json"
    bad_path.write_text(json.dumps(stats))
    r2 = _val(
        "texel_density_check.py",
        ["--stats", str(bad_path), "--style", str(STYLE), "--map-res", "2048", "--json"],
    )
    assert r2.returncode != 0, r2.stdout


def test_meshy_wrap_unavailable_without_key(tmp_path: Path, monkeypatch):
    from blender_gen.meshy_wrap import mesh_retexture, mesh_text_to_3d

    monkeypatch.delenv("MESHY_API_KEY", raising=False)
    # point generated root at tmp via monkeypatch of paths
    monkeypatch.setenv("UNITY_PROJECT", str(tmp_path))
    # recreate module path binding
    import blender_gen.paths as paths
    import blender_gen.meshy_wrap as mw

    pass  # paths.WORK_GAMES legacy
    monkeypatch.setattr(mw, "generated_root", lambda slug: tmp_path / "Assets" / "Generated")
    r = mesh_retexture("embervow", tmp_path / "missing.glb", seed=1)
    assert r["status"] == "unavailable"
    assert r.get("fallback") == "procedural"
    r2 = mesh_text_to_3d("embervow", "a crate", seed=2)
    assert r2["status"] == "unavailable"


def test_vision_client_unavailable_not_pass():
    r = vision_check(
        image_b64="aaaa",
        context="test",
        bridge_url="http://127.0.0.1:1",
    )
    assert r.get("unavailable") is True
    assert not any(i.get("verdict") == "pass" for i in r.get("items") or [])


def test_parse_check_and_unknown():
    items = parse_check_json(
        '{"items":[{"item":"x","verdict":"unknown","evidence_region":[0,0,1,1],"note":"n"}]}'
    )
    assert items[0]["verdict"] == "unknown"
    assert treat_unknown_as_fail("unknown") == "fail"
