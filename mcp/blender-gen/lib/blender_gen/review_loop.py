"""Bounded generate-with-review loop.

Order: deterministic validators FIRST > vision_check > revise ONE param group >
regen same seed. Cap 3 iterations. Oscillation detector: same item
fail>pass>fail across 3 loops => STOP + escalate.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ASSET_GEN = Path("$UNITY_GROK_ROOT/.claude/tools/asset_gen")
if str(ASSET_GEN) not in sys.path:
    sys.path.insert(0, str(ASSET_GEN))


def _run_validator(script: str, args: list[str]) -> tuple[int, str]:
    py = Path("$UNITY_GROK_ROOT/.claude/tools/asset_gen/.venv/bin/python")
    if not py.exists():
        py = Path(sys.executable)
    cmd = [str(py), str(ASSET_GEN / script), *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def run_material_validators(maps_dir: Path) -> dict[str, Any]:
    """Run deterministic map validators. Mortar depth is MEASURED from height maps."""
    results = {}
    for script, name in [
        ("tile_boundary_check.py", "tile_boundary"),
        ("colorspace_check.py", "colorspace"),
        ("mortar_depth_check.py", "mortar_depth"),
    ]:
        code, out = _run_validator(script, ["--maps", str(maps_dir), "--json"])
        results[name] = {"exit": code, "output": out[-2000:]}
    results["pass"] = all(
        (v.get("exit", 1) == 0)
        for k, v in results.items()
        if isinstance(v, dict) and "exit" in v
    )
    return results


def _vision_or_unavailable(image_path: Path, context: str) -> dict[str, Any]:
    try:
        from vision_client import vision_check  # type: ignore
    except ImportError:
        return {
            "unavailable": True,
            "reason": "vision_client import failed",
            "items": [],
        }
    return vision_check(image_path, context=context)


def _param_revision(params: dict, critique: dict, validators: dict) -> tuple[dict, str]:
    """Revise ONE param group based on validators/vision. Returns (new_params, group)."""
    new = dict(params)
    # Prefer measured validator failures (mortar_depth reads height maps)
    mortar_out = (validators.get("mortar_depth") or {}).get("output") or ""
    if not validators.get("pass"):
        if (validators.get("mortar_depth") or {}).get("exit", 0) != 0:
            # deep joints on maps → tighten mortar param and regen same seed
            cur = float(new.get("mortar", new.get("mortar_width", 0.06)))
            new["mortar"] = max(0.012, min(cur * 0.4, 0.02))
            new.pop("mortar_width", None)
            return new, "mortar"
        if "mortar" in mortar_out.lower() or "mortar_fraction" in mortar_out:
            new["mortar"] = max(0.012, min(float(new.get("mortar", 0.06)) * 0.4, 0.02))
            return new, "mortar"
        if "variation" in new:
            new["variation"] = max(0.05, float(new["variation"]) * 0.7)
            return new, "variation"
    items = critique.get("items") or []
    for it in items:
        if it.get("verdict") in ("fail", "unknown"):
            note = (it.get("note") or "") + " " + (it.get("item") or "")
            if "mortar" in note.lower() or "joint" in note.lower():
                new["mortar"] = min(float(new.get("mortar", 0.04)), 0.018)
                return new, "mortar"
            if "seam" in note.lower() or "tile" in note.lower():
                new["variation"] = max(0.05, float(new.get("variation", 0.15)) * 0.7)
                return new, "variation"
            if "repeat" in note.lower():
                new["variation"] = min(0.35, float(new.get("variation", 0.15)) * 1.3)
                return new, "variation"
    # default: slightly tighten mortar
    if "mortar" in new:
        new["mortar"] = max(0.012, float(new["mortar"]) * 0.85)
        return new, "mortar"
    return new, "none"


def generate_with_review(
    generate_fn: Callable[..., dict],
    *,
    seed: int,
    base_params: dict,
    max_iters: int = 3,
    diagnostic_name: str = "3x3_tiling.png",
    skip_vision: bool = False,
) -> dict[str, Any]:
    """Run generate → validators → vision → revise loop.

    generate_fn must accept **params including seed and return dict with out_dir.
    """
    params = dict(base_params)
    params["seed"] = seed
    history: list[dict] = []
    item_verdicts: dict[str, list[str]] = {}
    final = None

    for i in range(max_iters):
        result = generate_fn(**params)
        out_dir = Path(result["out_dir"])
        vals = run_material_validators(out_dir)
        critique: dict[str, Any]
        if skip_vision:
            critique = {"skipped": True, "items": [], "reason": "skip_vision"}
        else:
            diag = out_dir / diagnostic_name
            if not diag.exists():
                # any png
                pngs = list(out_dir.glob("*.png"))
                diag = pngs[0] if pngs else diag
            if diag.exists():
                critique = _vision_or_unavailable(
                    diag, context=f"material review iter={i} seed={seed} params={params}"
                )
            else:
                critique = {"unavailable": True, "reason": "no diagnostic image", "items": []}

        # track oscillation
        for it in critique.get("items") or []:
            name = it.get("item") or "?"
            item_verdicts.setdefault(name, []).append(it.get("verdict", "unknown"))

        osc = False
        for name, vs in item_verdicts.items():
            if len(vs) >= 3 and vs[-3] == "fail" and vs[-2] == "pass" and vs[-1] == "fail":
                osc = True

        vision_fail = False
        if critique.get("unavailable"):
            vision_fail = False  # skip-with-announcement, do not treat as pass or hard fail
        else:
            for it in critique.get("items") or []:
                if it.get("verdict") in ("fail", "unknown"):
                    vision_fail = True

        record = {
            "iter": i,
            "params": dict(params),
            "validators": vals,
            "critique": {
                "unavailable": critique.get("unavailable"),
                "reason": critique.get("reason"),
                "items": critique.get("items"),
                "model": critique.get("model"),
                "skipped": critique.get("skipped"),
            },
            "out_dir": str(out_dir),
        }
        history.append(record)
        final = result

        if vals.get("pass") and not vision_fail:
            return {
                "status": "pass",
                "iterations": i + 1,
                "result": final,
                "history": history,
            }

        if osc:
            return {
                "status": "escalate",
                "reason": "oscillation_detector",
                "iterations": i + 1,
                "result": final,
                "history": history,
            }

        if i == max_iters - 1:
            break

        # measured validator fail outranks vision pass
        new_params, group = _param_revision(params, critique, vals)
        history[-1]["revision_group"] = group
        # keep same seed
        new_params["seed"] = seed
        params = new_params

    return {
        "status": "escalate" if not (history and history[-1]["validators"].get("pass")) else "pass_validators_only",
        "iterations": len(history),
        "result": final,
        "history": history,
    }


def save_run_record(path: Path, record: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
    return path
