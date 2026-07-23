#!/usr/bin/env python3
"""CoreSkeleton27 ARDY payload -> BVH converter.

Golden-file tested. Euler order XYZ degrees (BVH common). Root translation
from root_positions; joint local rotations from local_rotations.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

from ardy_skeleton import CORE_SKELETON_27, ROOT_NAME, children_map, joint_by_name


def load_payload(path: Path | str) -> dict[str, Any]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    # unwrap client envelope if present
    if "response" in doc and "local_rotations" not in doc:
        resp = doc["response"]
        if isinstance(resp, dict) and "local_rotations" in resp:
            return resp
        if isinstance(resp, list) and resp and isinstance(resp[0], dict):
            return resp[0]
        if isinstance(resp, dict) and "data" in resp:
            data = resp["data"]
            if isinstance(data, list) and data:
                if isinstance(data[0], dict):
                    return data[0]
                if isinstance(data[0], str):
                    try:
                        return json.loads(data[0])
                    except json.JSONDecodeError:
                        pass
    return doc


def _fmt(n: float) -> str:
    return f"{n:.6f}"


def build_hierarchy_lines() -> list[str]:
    cmap = children_map()
    jmap = joint_by_name()
    lines: list[str] = []

    def emit(name: str, indent: int) -> None:
        pad = "  " * indent
        j = jmap[name]
        off = j["offset"]
        is_root = j["parent"] is None
        if is_root:
            lines.append(f"{pad}ROOT {name}")
        else:
            lines.append(f"{pad}JOINT {name}")
        lines.append(f"{pad}{{")
        lines.append(f"{pad}  OFFSET {_fmt(off[0])} {_fmt(off[1])} {_fmt(off[2])}")
        if is_root:
            lines.append(
                f"{pad}  CHANNELS 6 Xposition Yposition Zposition Xrotation Yrotation Zrotation"
            )
        else:
            lines.append(f"{pad}  CHANNELS 3 Xrotation Yrotation Zrotation")
        kids = cmap.get(name, [])
        if not kids:
            lines.append(f"{pad}  End Site")
            lines.append(f"{pad}  {{")
            lines.append(f"{pad}    OFFSET 0.000000 0.100000 0.000000")
            lines.append(f"{pad}  }}")
        for ch in kids:
            emit(ch, indent + 1)
        lines.append(f"{pad}}}")

    lines.append("HIERARCHY")
    emit(ROOT_NAME, 0)
    return lines


def _rot_for(frame_rots: dict, name: str) -> tuple[float, float, float]:
    r = frame_rots.get(name) or frame_rots.get(name.lower()) or [0.0, 0.0, 0.0]
    if isinstance(r, dict):
        return float(r.get("x", 0)), float(r.get("y", 0)), float(r.get("z", 0))
    if isinstance(r, (list, tuple)) and len(r) >= 3:
        return float(r[0]), float(r[1]), float(r[2])
    return 0.0, 0.0, 0.0


def _root_pos(frame_pos: Any, i: int) -> tuple[float, float, float]:
    if isinstance(frame_pos, list) and frame_pos:
        # list of [x,y,z] per frame
        if isinstance(frame_pos[0], (list, tuple)):
            p = frame_pos[i] if i < len(frame_pos) else frame_pos[-1]
            return float(p[0]), float(p[1]), float(p[2])
        if isinstance(frame_pos[0], dict):
            # posed joints style
            return 0.0, 0.0, 0.0
    return 0.0, 0.0, 0.0


def convert_to_bvh(payload: dict[str, Any], out_path: Path | str) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fps = float(payload.get("fps") or 20.0)
    frame_time = 1.0 / fps
    rots = payload.get("local_rotations") or []
    roots = payload.get("root_positions") or []
    nframes = max(len(rots), len(roots), 1)

    # joint channel order = DFS hierarchy order
    order: list[str] = []

    def walk(name: str) -> None:
        order.append(name)
        for ch in children_map().get(name, []):
            walk(ch)

    walk(ROOT_NAME)

    lines = build_hierarchy_lines()
    lines.append("MOTION")
    lines.append(f"Frames: {nframes}")
    lines.append(f"Frame Time: {_fmt(frame_time)}")

    for i in range(nframes):
        fr = rots[i] if i < len(rots) else {}
        if not isinstance(fr, dict):
            fr = {}
        rx, ry, rz = _root_pos(roots, i)
        # if root_positions empty, try posed_joints Hips
        if roots == [] and payload.get("posed_joints"):
            pj = payload["posed_joints"][i]
            if isinstance(pj, dict) and ROOT_NAME in pj:
                p = pj[ROOT_NAME]
                rx, ry, rz = float(p[0]), float(p[1]), float(p[2])
        chans: list[str] = []
        for name in order:
            if name == ROOT_NAME:
                chans.extend([_fmt(rx), _fmt(ry), _fmt(rz)])
            e = _rot_for(fr, name)
            chans.extend([_fmt(e[0]), _fmt(e[1]), _fmt(e[2])])
        lines.append(" ".join(chans))

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # sidecar
    side = {
        "fps": fps,
        "frames": nframes,
        "foot_contacts": payload.get("foot_contacts"),
        "seed": payload.get("seed"),
        "skeleton": payload.get("skeleton", "CoreSkeleton27"),
        "bvh": str(out_path),
    }
    side_path = out_path.with_suffix(".sidecar.json")
    side_path.write_text(json.dumps(side, indent=2) + "\n", encoding="utf-8")
    return out_path


def humanoid_bone_checklist(mapped_names: list[str] | None = None) -> dict[str, Any]:
    """Blender-side checklist when Unity project is not open."""
    from ardy_skeleton import MIXAMO_BONE_MAP, UNITY_HUMANOID_REQUIRED

    mapped = mapped_names or list(MIXAMO_BONE_MAP.values())
    # accept both LeftArm and LeftUpperArm style
    aliases = {
        "mixamorig:LeftUpperArm": "mixamorig:LeftArm",
        "mixamorig:RightUpperArm": "mixamorig:RightArm",
        "mixamorig:LeftUpperLeg": "mixamorig:LeftUpLeg",
        "mixamorig:RightUpperLeg": "mixamorig:RightUpLeg",
    }
    missing = []
    for req in UNITY_HUMANOID_REQUIRED:
        if req in mapped:
            continue
        alt = aliases.get(req)
        if alt and alt in mapped:
            continue
        missing.append(req)
    return {
        "pass": len(missing) == 0,
        "mapped": mapped,
        "missing_required": missing,
        "note": "Unity Humanoid auto-map checklist (no project open)",
    }


def retarget_record(
    bvh_path: Path | str,
    out_fbx_stub: Path | str | None = None,
) -> dict[str, Any]:
    """Produce Mixamo-named retarget record + optional FBX placeholder path.

    Full FBX binary export needs Blender; we write a JSON retarget table and a
    humanoid checklist. When Blender is available, a driver can apply this map.
    """
    from ardy_skeleton import MIXAMO_BONE_MAP

    bvh_path = Path(bvh_path)
    out = {
        "bvh": str(bvh_path),
        "bone_map": MIXAMO_BONE_MAP,
        "checklist": humanoid_bone_checklist(),
        "status": "map_ready",
    }
    if out_fbx_stub:
        p = Path(out_fbx_stub)
        p.parent.mkdir(parents=True, exist_ok=True)
        # FBX ASCII minimal marker (not a full mesh) for path contract tests
        p.write_text(
            "; FBX stub for pipeline path — open BVH in Blender, retarget via bone_map, export FBX\n"
            + json.dumps({"bone_map": MIXAMO_BONE_MAP, "source_bvh": str(bvh_path)}, indent=2),
            encoding="utf-8",
        )
        out["fbx_stub"] = str(p)
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("payload", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--fbx-stub", type=Path, default=None)
    args = ap.parse_args(argv)
    payload = load_payload(args.payload)
    bvh = convert_to_bvh(payload, args.output)
    rec = retarget_record(bvh, args.fbx_stub)
    print(json.dumps({"bvh": str(bvh), "retarget": rec}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
