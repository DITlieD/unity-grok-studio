"""CoreSkeleton27 hierarchy (from nv-tlabs/ardy skeleton definitions, frozen).

Source: https://github.com/nv-tlabs/ardy/blob/main/ardy/skeleton/definitions.py
Offsets are approximate rest-pose meters for BVH export; hierarchy is authoritative.
"""
from __future__ import annotations

ROOT_NAME = "Hips"

# name, parent, offset(x,y,z meters)
CORE_SKELETON_27: list[dict] = [
    {"name": "Hips", "parent": None, "offset": [0.0, 0.95, 0.0]},
    {"name": "Spine", "parent": "Hips", "offset": [0.0, 0.12, 0.0]},
    {"name": "Spine1", "parent": "Spine", "offset": [0.0, 0.12, 0.0]},
    {"name": "Spine2", "parent": "Spine1", "offset": [0.0, 0.12, 0.0]},
    {"name": "Neck", "parent": "Spine2", "offset": [0.0, 0.10, 0.0]},
    {"name": "Head", "parent": "Neck", "offset": [0.0, 0.12, 0.0]},
    {"name": "LeftShoulder", "parent": "Spine2", "offset": [0.08, 0.08, 0.0]},
    {"name": "LeftArm", "parent": "LeftShoulder", "offset": [0.14, 0.0, 0.0]},
    {"name": "LeftForeArm", "parent": "LeftArm", "offset": [0.25, 0.0, 0.0]},
    {"name": "LeftHand", "parent": "LeftForeArm", "offset": [0.22, 0.0, 0.0]},
    {"name": "RightShoulder", "parent": "Spine2", "offset": [-0.08, 0.08, 0.0]},
    {"name": "RightArm", "parent": "RightShoulder", "offset": [-0.14, 0.0, 0.0]},
    {"name": "RightForeArm", "parent": "RightArm", "offset": [-0.25, 0.0, 0.0]},
    {"name": "RightHand", "parent": "RightForeArm", "offset": [-0.22, 0.0, 0.0]},
    {"name": "LeftUpLeg", "parent": "Hips", "offset": [0.10, -0.08, 0.0]},
    {"name": "LeftLeg", "parent": "LeftUpLeg", "offset": [0.0, -0.42, 0.0]},
    {"name": "LeftFoot", "parent": "LeftLeg", "offset": [0.0, -0.40, 0.0]},
    {"name": "LeftToeBase", "parent": "LeftFoot", "offset": [0.0, -0.02, 0.12]},
    {"name": "RightUpLeg", "parent": "Hips", "offset": [-0.10, -0.08, 0.0]},
    {"name": "RightLeg", "parent": "RightUpLeg", "offset": [0.0, -0.42, 0.0]},
    {"name": "RightFoot", "parent": "RightLeg", "offset": [0.0, -0.40, 0.0]},
    {"name": "RightToeBase", "parent": "RightFoot", "offset": [0.0, -0.02, 0.12]},
    # ARDY extras / aliases often present in CoreSkeleton27
    {"name": "LeftHip", "parent": "Hips", "offset": [0.09, -0.05, 0.0]},
    {"name": "RightHip", "parent": "Hips", "offset": [-0.09, -0.05, 0.0]},
    {"name": "Chest", "parent": "Spine1", "offset": [0.0, 0.10, 0.0]},
    {"name": "LeftCollar", "parent": "Chest", "offset": [0.07, 0.05, 0.0]},
    {"name": "RightCollar", "parent": "Chest", "offset": [-0.07, 0.05, 0.0]},
]

# Mixamo retarget map: CoreSkeleton27 -> mixamo bone name
MIXAMO_BONE_MAP: dict[str, str] = {
    "Hips": "mixamorig:Hips",
    "Spine": "mixamorig:Spine",
    "Spine1": "mixamorig:Spine1",
    "Spine2": "mixamorig:Spine2",
    "Neck": "mixamorig:Neck",
    "Head": "mixamorig:Head",
    "LeftShoulder": "mixamorig:LeftShoulder",
    "LeftArm": "mixamorig:LeftArm",
    "LeftForeArm": "mixamorig:LeftForeArm",
    "LeftHand": "mixamorig:LeftHand",
    "RightShoulder": "mixamorig:RightShoulder",
    "RightArm": "mixamorig:RightArm",
    "RightForeArm": "mixamorig:RightForeArm",
    "RightHand": "mixamorig:RightHand",
    "LeftUpLeg": "mixamorig:LeftUpLeg",
    "LeftLeg": "mixamorig:LeftLeg",
    "LeftFoot": "mixamorig:LeftFoot",
    "LeftToeBase": "mixamorig:LeftToeBase",
    "RightUpLeg": "mixamorig:RightUpLeg",
    "RightLeg": "mixamorig:RightLeg",
    "RightFoot": "mixamorig:RightFoot",
    "RightToeBase": "mixamorig:RightToeBase",
}

# Unity Humanoid required bones checklist (Mixamo naming)
UNITY_HUMANOID_REQUIRED = [
    "mixamorig:Hips",
    "mixamorig:Spine",
    "mixamorig:Head",
    "mixamorig:LeftUpperArm",  # may map from LeftArm depending on importer
    "mixamorig:RightUpperArm",
    "mixamorig:LeftUpperLeg",
    "mixamorig:RightUpperLeg",
    "mixamorig:LeftHand",
    "mixamorig:RightHand",
    "mixamorig:LeftFoot",
    "mixamorig:RightFoot",
]


def children_map() -> dict[str | None, list[str]]:
    m: dict[str | None, list[str]] = {}
    for j in CORE_SKELETON_27:
        m.setdefault(j["parent"], []).append(j["name"])
    return m


def joint_by_name() -> dict[str, dict]:
    return {j["name"]: j for j in CORE_SKELETON_27}
