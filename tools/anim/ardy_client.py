#!/usr/bin/env python3
"""ARDY prototype client — HF space MCP/HTTP generate_motion + payload persist.

Space: https://hugging-apps-ardy.hf.space
Tool: ardy_generate_motion (prompt, rig, duration, diffusion_steps, cfg_weight, seed)
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(os.environ.get("UNITY_GROK_ROOT", Path(__file__).resolve().parents[2]))
SPACE = os.environ.get("ARDY_SPACE", "https://hugging-apps-ardy.hf.space")
# Gradio call endpoint variants
CALL_URLS = [
    f"{SPACE}/gradio_api/call/ardy_generate_motion",
    f"{SPACE}/call/ardy_generate_motion",
    f"{SPACE}/api/predict",
]


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    tok = os.environ.get("HF_TOKEN")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def anim_out_dir(game_slug: str) -> Path:
    return Path(os.environ.get("ARDY_OUT", str(PACKAGE_ROOT / "outputs" / "anims"))) / game_slug


def ardy_generate(
    prompt: str = "a person walks in a circle",
    *,
    game_slug: str = "demo",
    rig: str = "human",
    duration: float = 2.0,
    diffusion_steps: int = 10,
    cfg_weight: float = 5.0,
    seed: int = 42,
    timeout_s: float = 300.0,
) -> dict[str, Any]:
    """Call HF ARDY space; persist JSON skeleton payload under outputs/{game}/anims/prototype/."""
    out_dir = anim_out_dir(game_slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    payload_path = out_dir / f"ardy_{seed}_{stamp}.json"

    body = {
        "data": [prompt, rig, duration, diffusion_steps, cfg_weight, seed],
    }
    last_err = None
    for url in CALL_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=_headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"raw": raw}
            # Gradio SSE event-id style: may return event_id then need GET
            if isinstance(data, dict) and "event_id" in data:
                eid = data["event_id"]
                poll = url.rstrip("/") + f"/{eid}"
                req2 = urllib.request.Request(poll, headers=_headers(), method="GET")
                with urllib.request.urlopen(req2, timeout=timeout_s) as resp2:
                    text = resp2.read().decode("utf-8", errors="replace")
                # SSE lines data: ...
                for line in text.splitlines():
                    if line.startswith("data:"):
                        chunk = line[5:].strip()
                        if chunk and chunk != "[DONE]":
                            try:
                                data = json.loads(chunk)
                            except json.JSONDecodeError:
                                data = {"raw": chunk}
            result = {
                "status": "ok",
                "prompt": prompt,
                "seed": seed,
                "rig": rig,
                "duration": duration,
                "diffusion_steps": diffusion_steps,
                "cfg_weight": cfg_weight,
                "space": SPACE,
                "response": data,
            }
            payload_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            result["payload_path"] = str(payload_path)
            return result
        except Exception as exc:
            last_err = repr(exc)
            continue

    # ZeroGPU / network failure path
    fail = {
        "status": "error",
        "reason": last_err or "all endpoints failed",
        "prompt": prompt,
        "seed": seed,
        "hint": "set HF_TOKEN; on 3-day unreliability follow FORK F4 (self-host U6) or F5 (kimodo)",
        "fork": "F4_or_F5_if_persistent",
    }
    payload_path.write_text(json.dumps(fail, indent=2) + "\n", encoding="utf-8")
    fail["payload_path"] = str(payload_path)
    return fail


def synthesize_core_skeleton_clip(
    *,
    seed: int = 42,
    frames: int = 40,
    fps: float = 20.0,
) -> dict[str, Any]:
    """Deterministic synthetic CoreSkeleton27-like payload for converter tests.

    Shape matches what ardy_to_bvh expects when live HF is unavailable.
    """
    from ardy_skeleton import CORE_SKELETON_27, ROOT_NAME  # local

    import math
    import random

    rng = random.Random(seed)
    joints = [j["name"] for j in CORE_SKELETON_27]
    posed = []
    local_rot = []
    root_pos = []
    foot = []
    for f in range(frames):
        t = f / fps
        # root walks in a circle
        r = 0.5
        rx = r * math.cos(t * 1.5)
        rz = r * math.sin(t * 1.5)
        root_pos.append([rx, 0.0, rz])
        frame_pos = {}
        frame_rot = {}
        for j in CORE_SKELETON_27:
            name = j["name"]
            rest = j.get("offset", [0.0, 0.0, 0.0])
            frame_pos[name] = [
                rest[0] + rx * (0.01 if name != ROOT_NAME else 1.0),
                rest[1],
                rest[2] + rz * (0.01 if name != ROOT_NAME else 1.0),
            ]
            # local euler XYZ degrees
            if "Left" in name or "Right" in name:
                swing = 25.0 * math.sin(t * 6.0 + (0.5 if "Left" in name else 0.0))
                frame_rot[name] = [swing, 0.0, 0.0]
            else:
                frame_rot[name] = [0.0, rng.uniform(-1, 1) * 0.0, 0.0]
        posed.append(frame_pos)
        local_rot.append(frame_rot)
        foot.append({"left": abs(math.sin(t * 6.0)) < 0.2, "right": abs(math.sin(t * 6.0 + 0.5)) < 0.2})
    return {
        "skeleton": "CoreSkeleton27",
        "joints": joints,
        "fps": fps,
        "seed": seed,
        "posed_joints": posed,
        "local_rotations": local_rot,
        "root_positions": root_pos,
        "foot_contacts": foot,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="a person walks in a circle")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--game", default="default")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("-o", "--output", default=None, help="Write synthetic/live payload JSON path")
    args = ap.parse_args()
    if args.synthetic:
        clip = synthesize_core_skeleton_clip(seed=args.seed)
        if args.output:
            p = Path(args.output)
            p.parent.mkdir(parents=True, exist_ok=True)
        else:
            out = anim_out_dir(args.game)
            out.mkdir(parents=True, exist_ok=True)
            p = out / f"ardy_synthetic_{args.seed}.json"
        p.write_text(json.dumps(clip, indent=2) + "\n")
        print(json.dumps({"status": "ok", "payload_path": str(p)}))
    else:
        print(json.dumps(ardy_generate(args.prompt, game_slug=args.game, seed=args.seed), indent=2))
