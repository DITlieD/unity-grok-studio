---
name: unity-toolkit
description: Catalog of the in-engine Unity tools available across ZC/EO — the placement toolkit (scene_validate, place_object, adjust_object, place_relative, scatter_objects), VFX pipeline (vfx_preview, vfx_census, vfx-lint, cel baker, master integrity), UISnapshot/SceneSnapshot/ViewProbe, the anim arm, the WorldGen PCG (RoadPath spline + RoadsideSpawner + DirtDisc), agentdebug runtime dumps, and the python visual checkers. Triggers when Raian says "the placement tool", "the map tool", "toolkit", "what tools do we have", "the spatial tools", "scene tools", "worldgen", "road tool", "vfx tool", "vfx_preview", "vfx-lint", or a session needs to discover which in-engine tool covers a placement/measurement/visual/anim/vfx job. Read-only reference; points at the deep docs instead of duplicating them.
---

UNITY TOOLKIT (one-page catalog, brief on purpose)

WHAT THIS IS
Every in-engine tool we built or adopted for agent-driven Unity work, one line each, plus where the full doc lives. When a job matches a tool here, read that tool's deep doc BEFORE improvising with raw manage_gameobject/YAML. Deep catalogs: workflow root unity-inventory.md (full list), each package CODEMAP.txt (per-tool detail).

PLACEMENT TOOLKIT (world objects, measured placement)
Editor-only custom MCP tools in .projects/_shared/com.unitygrok.uitools/Editor/Placement/ (CODEMAP.txt there). Act+measure contract: every mutating call returns engine-measured grounded/penetration numbers, positional claims come from those numbers never from a screenshot.
  scene_validate    read-only defect report: floating/buried, penetration pairs, containment, per-object suggested fix
  place_object      instantiate prefab or move object: ground-snap, depenetrate, measure, one undo step
  adjust_object     one op on an existing object: snap | depenetrate | face | align
  place_relative    subject relative to anchor(s): on | beside | facing | between
  scatter_objects   N instances into a box/radius region, seeded, rejection-sampled, deterministic
CAVEAT: if they did not register as first-class MCP tools this session, route by name through batch_execute ({tool:"scene_validate", params:{...}}) — works identically. Corner-pivot Synty env tiles: place by renderer bounds, never by pivot. Sweep scatter results for position.y above ground level (roof/canopy landings).

WORLDGEN PCG (roads, clearings, roadside villages — raian-editable)
Components in .projects/Zombie_Citizen/Assets/Scripts/Raian/WorldGen/, editors in Assets/Editor/Raian/. Personal tooling, never committed.
  RoadPath + RoadPathEditor   select the RoadPath object: drag orange sphere handles, shift+click ground adds a point, road ribbon rebuilds live; width/edgeJitter/sampleSpacing/seed on the component
  RoadsideSpawner             on the same object: buildings re-flow along both road sides as the spline changes; prefabs/spacing/sideOffset/jitter/tStart/tEnd/seed, shuffled-bag variety
  DirtDiscDef                 round organic dirt clearings; menu Tools/Raian/WorldGen (Create/Rebuild)
  generated assets            Assets/Raian/Generated/ (meshes + shared M_Raian_Dirt material, one draw call for all ground decals)

SNAPSHOT / PROBE (geometry facts an agent cannot infer from markup)
Same package, Editor/: full detail in the package CODEMAP + .claude/rules/visual-ui-loop.md.
  UISnapshot      Tools/UI Tools menu, dumps resolved UI layout (worldBound/anchors/classes) to UISnapshots/*.layout.json
  SceneSnapshot   dumps per-renderer world pos/bounds/frustum/pxRect to UISnapshots/scene.layout.json (maps screenshot pixels to scene objects)
  View Probe      raian marks a frozen frame (POINT/ARROW/LINE/BOX), pastes the export; ALWAYS Read the referenced png first, protocol in visual-ui-loop.md VIEW PROBE INPUT

ANIM ARM (Animator graph evidence)
Same package, Editor/Anim/ (deep doc: workflow/handoff/anim-agent-tooling.md).
  anim_snapshot          AnimatorController graph to UISnapshots/anim.*.graph.json (states/transitions/conditions/blendtrees)
  anim_filmstrip         6-tile contact-sheet png + pose json, proves a clip retargeted
  anim_fit_state_speed   fit a state's clip to a target duration via speed param
  anim_clip_events       get/set animation events, normalizedTime/seconds round-trip

VFX PIPELINE (deterministic Shuriken preview + authoring gates — ZC primary, package shared)
Shared editor package .projects/_shared/com.unitygrok.uitools/Editor/Vfx/ + ZC builders/runtime + .claude/tools/. Deep handoff: workflow/handoff/agent-vfx-pipeline.md. Goal: stop blank-slate VFX authoring; agents capture, lint, and compose from library ingredients. Masters under Assets/VFX/Library/Masters/ are tool proof fixtures, not finished ship art.
  vfx_preview            MCP capture any prefab: normalized timestamps, contact sheet + metadata json, backgrounds gray|black|bright|gameplay, cameras close(3.5 default)|game(7)|side, optional tier/instanceCount. Static fallback VfxStage.Capture(VfxStageRequest). Judgment default close+gray; game for gameplay-size truth. FORK: if schema missing, call static Capture via execute_code.
  vfx_census             MCP dump per-system facts json (HDR channels, soft/fading keywords, sortingOrder, scalingMode, RandomColor Fixed, sizes, maxParticles, allowlist marker). Static VfxPrefabCensus.Dump / DumpFolder.
  VfxLintAllowlist       empty MonoBehaviour marker on intentional accent systems (not name heuristics)
  VfxEffectController    runtime param surface: PrimaryColor/SecondaryColor/EffectScale/Duration/Intensity, LDR clamp, scalingMode Local on Apply
  menus                  Tools/Build/ZC VFX Library/Bake All ; Tools/Build/ZC VFX Masters/Build All|(Force) — create-once masters (force overwrites + version bump)
  vfx-lint.py            census consumer: BLOCK HDR>1 without allowlist, soft/fading, sortingOrder!=0; WARN tiny additive, RandomColor not Fixed, maxParticles. SOURCE leg greps builders HDR(k>1). exit 0/1/2. --self-test. D4 freeze into gate-manifest is raian-gated (do not self-edit).
  procedural_vfx_bake.py offline cel singles+flipbooks to Assets/VFX/Library/Textures/
  vfx_library_parity.py  set-diff Library vs VFX_LIBRARY.md
  vfx_master_integrity.py Masters/*.prefab sha256 vs masters_integrity.json
  vfx_perf_budget.py     capture metadata perf vs budget (NEED_BUDGET defaults), --self-test
CAVEAT: ZC csc.rsp treats UNT0026 as error — TryGetComponent not GetComponent in shared Vfx package. tier=Performance with missing RP path can wash capture frames; omit tier for judgment goldens.

RUNTIME (live game evidence, play mode / dev builds)
  com.unitygrok.agentdebug   RuntimeStateExporter + AgentLogBridge + AnimRuntimeRecorder dump live state and threaded logs to persistentDataPath/AgentDebug/ (rulebook: runtime-debugging.md)
  playtester skill          AgentDriver + ExceptionWatchdog drive the real game E2E, ZC only (.claude/skills/playtester/SKILL.md)
  agentmcp runtime bridge   staged, not enabled; runtime MCP into a dev build (workflow/handoff/agentmcp-runtime-bridge.md)

PYTHON VISUAL CHECKERS (.claude/tools/)
  ui-diff.py       deterministic image diff, hotspots + judge-ready crops, runs BEFORE any vision call (visual-ui-loop.md)
  vlm-prep.py      resize + JPEG re-encode a full frame for a vision read
  uss-taste-lint.py  WCAG contrast + engine-font + dead-neutral USS lint
  vfx-lint.py / vfx_library_parity.py / vfx_master_integrity.py / vfx_perf_budget.py / procedural_vfx_bake.py   VFX pipeline (see VFX PIPELINE)

WHERE THE DEEP DOCS LIVE
  unity-inventory.md (root)                              full inventory, all sections
  .projects/_shared/com.unitygrok.uitools/.../CODEMAP.txt placement toolkit detail + extension seam
  .claude/rulebook/unity-mcp-usage.md                    the CoplayDev bridge tool catalog + FSM gates
  .claude/rules/visual-ui-loop.md                        capture/diff/critique discipline + View Probe
  workflow/handoff/zc-forest-scenes.md                   worldgen PCG usage + scene-build gotchas
  workflow/handoff/agent-vfx-pipeline.md                 VFX pipeline tools + usage + open gates
