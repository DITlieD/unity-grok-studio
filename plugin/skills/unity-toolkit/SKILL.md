---
name: unity-toolkit
description: >
  Catalog of in-engine Unity tools shipped in unity-packages/com.unitygrok.uitools
  and com.unitygrok.agentdebug — placement (scene_validate, place_object, adjust_object,
  place_relative, scatter_objects), VFX (vfx_preview, vfx_census, VfxLintAllowlist),
  UISnapshot/SceneSnapshot/ViewProbe, anim arm (anim_snapshot, anim_filmstrip,
  anim_fit_state_speed, anim_clip_events), agentdebug runtime dumps. Triggers when the
  user asks about placement tools, spatial tools, scene tools, vfx tools, anim tooling,
  View Probe, or which in-engine tool covers a placement/measurement/visual/anim/vfx job.
  Read-only reference; points at package CODEMAP files.
---

# UNITY TOOLKIT (package catalog)

## What this is
Every in-engine tool in the standalone UPM packages, one line each, plus where the
deep doc lives. When a job matches a tool here, read that tool's CODEMAP BEFORE
improvising with raw manage_gameobject/YAML.

Package roots (under `$UNITY_GROK_ROOT`):
- `unity-packages/com.unitygrok.uitools/`
- `unity-packages/com.unitygrok.agentdebug/`

Wire into a project with:
```bash
./scripts/wire-unity-project.sh /path/to/UnityProject
```

Menus: **Tools/UnityGrok/** (Editor menus).

## PLACEMENT TOOLKIT (world objects, measured placement)
Editor-only tools in `unity-packages/com.unitygrok.uitools/Editor/Placement/` (see CODEMAP.txt).
Act+measure contract: every mutating call returns engine-measured grounded/penetration
numbers; positional claims come from those numbers, never from a screenshot alone.

| Tool | Role |
|------|------|
| scene_validate | read-only defect report: floating/buried, penetration, containment, suggested fix |
| place_object | instantiate/move: ground-snap, depenetrate, measure, one undo step |
| adjust_object | snap \| depenetrate \| face \| align |
| place_relative | subject relative to anchor(s): on \| beside \| facing \| between |
| scatter_objects | N instances into box/radius, seeded, rejection-sampled, deterministic |

CAVEAT: if they did not register as first-class MCP tools this session, route by name
through batch_execute (`{tool:"scene_validate", params:{...}}`). Corner-pivot env tiles:
place by renderer bounds, never by pivot.

## SNAPSHOT / PROBE
Same package, `Editor/`:

| Tool | Role |
|------|------|
| UISnapshot | Tools/UnityGrok menu — resolved UI layout JSON |
| SceneSnapshot | per-renderer world pos/bounds/frustum JSON |
| View Probe | frozen-frame POINT/ARROW/LINE/BOX export; always Read the referenced PNG first |

## ANIM ARM
`Editor/Anim/`:

| Tool | Role |
|------|------|
| anim_snapshot | AnimatorController graph JSON |
| anim_filmstrip | 6-tile contact-sheet + pose JSON |
| anim_fit_state_speed | fit state clip duration via speed param |
| anim_clip_events | get/set animation events |

## VFX PIPELINE
`Editor/Vfx/`:

| Tool | Role |
|------|------|
| vfx_preview | capture prefab timestamps + contact sheet + metadata |
| vfx_census | per-system facts JSON (HDR, soft/fading, sortingOrder, …) |
| VfxLintAllowlist | marker on intentional accent systems |
| VfxEffectController | runtime param surface (colors, scale, duration, intensity) |

CAVEAT: prefer TryGetComponent over GetComponent where analyzers require it.

## RUNTIME (play mode / dev builds)
`com.unitygrok.agentdebug`: RuntimeStateExporter + AgentLogBridge + AnimRuntimeRecorder
dump live state to `persistentDataPath/AgentDebug/`.

## PYTHON VISUAL / STATIC GATES
Under `$UNITY_GROK_ROOT/tools/gates/`:
- `run_unity_static_gates.sh` (toban001, symbol census, mono_wire, pattern scan)
- fixture smoke: `bash tools/gates/run_unity_static_gates.sh --fixture`

## Deep docs
- Placement CODEMAP: `unity-packages/com.unitygrok.uitools/Editor/Placement/CODEMAP.txt`
- Anim CODEMAP: `unity-packages/com.unitygrok.uitools/Editor/Anim/CODEMAP.txt`
- Rulebook: `$GROK_PLUGIN_ROOT/rulebook/unity-mcp-usage.md`
- Skill: `unity-gates` for static gate invocations
