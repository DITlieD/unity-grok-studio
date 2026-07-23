---
name: unity-scaffold
description: Scaffold a new Unity feature module or new game project skeleton to the studio's purpose-driven layout: the Features/Worlds/Shared folder shape plus the runtime/editor/test asmdef quartet with correct references and settings. Triggers when the user says "scaffold a new feature", "set up a new module", "create the <X> feature", "stub the asmdefs for <X>", "new game skeleton", "lay out a new system", or points at unity-architecture.md and asks to materialize it. Writes .asmdef JSON + folders + a CODEMAP stub (all plain text, NOT scene/prefab YAML). Does NOT generate gameplay code or prefabs.
---

UNITY SCAFFOLD (materialize the architecture layout for new work)

Turns the greenfield guidance in unity-architecture.md into real folders + asmdef files for a new feature module (the common case) or a new game skeleton (rare). The point is that every feature module comes out with the same repetitive inner shape and a correct assembly graph, so it is testable from day one and an agent's blast radius stays inside one feature root.

Why this is a skill and not hand edits: .asmdef files are plain JSON, safe for an agent to author directly (this is NOT the .prefab/.unity YAML BLOCK case in unity-mcp-and-builders.md). The risk is getting the reference graph and settings wrong, which this skill standardizes.

WHEN TO INVOKE

- "scaffold a new feature", "create the <Name> feature/module/system", "stub the asmdefs for <Name>"
- "new game skeleton" / "lay out a new game" (the rarer whole-project case)
- the user read unity-architecture.md and wants the folder taxonomy + asmdef triple made real

When NOT:
- generating gameplay code, prefabs, ScriptableObject assets, or scenes > that is normal implementation (coding-standards.md, unity-mcp-and-builders.md), not this skill
- adding to an EXISTING game whose layout is dev-named subtrees (EO) > do not impose Features/Worlds; ask Raian whether the new module goes under his owned subtree instead (folder-ownership.md). This skill's taxonomy is for a new game or a self-contained module that does not fight the established layout

PREREQUISITE CHECKS (do these before writing anything)

1. Confirm CURRENT_GAME and the target root. Read workflow/sessions/{id}/current-game.txt. New work targets {CURRENT_GAME}/ only (project boundary, CLAUDE.md).
2. Ownership gate (folder-ownership.md). On a game with _Main, default there. On EO and any per-dev-folder game, default to Raian's subtree and surface the exact path before writing. Reading other devs' folders is fine, writing is not.
3. Backup any file you would overwrite into _Backups/{timestamp}/ first (memory:feedback_backup_before_edit). Scaffolding should only CREATE; if a path already exists, stop and surface it rather than clobbering.
4. Pick the studio/company/namespace prefix from project-config.md.

FEATURE MODULE SHAPE (the default)

Create under the game's feature root (Features/<Name>/ on a taxonomy game, or the agreed owned subtree otherwise):

  Features/<Name>/
    Runtime/        <Company>.<Game>.<Name>.asmdef
    Editor/         <Company>.<Game>.<Name>.Editor.asmdef
    Tests/
      EditMode/     <Company>.<Game>.<Name>.EditModeTests.asmdef
      PlayMode/     <Company>.<Game>.<Name>.PlayModeTests.asmdef
    Data/           ScriptableObject assets (authored later via Builder/MCP) + *.source.json where a dataset is large
    Prefabs/        built later via Builder/MCP, never hand-authored YAML
    UI/             <Name>Screen.uxml + .uss when the feature has UI (text-first)
    CODEMAP.md      public symbols, owning asmdef, entrypoints, test files (dr-7 per-feature code map; the studio map.txt is the global version)

ASMDEF TEMPLATES (JSON, written directly)

Runtime (<Company>.<Game>.<Name>):
  {
    "name": "<Company>.<Game>.<Name>",
    "rootNamespace": "<Company>.<Game>.<Name>",
    "references": ["GUID:<Core/Foundation asmdef guid>"],
    "autoReferenced": true,
    "overrideReferences": false,
    "noEngineReferences": false
  }
  Pure-domain runtime assemblies (no Transform/Physics/Time needed) set "noEngineReferences": true so they stay Unity-independent and fast to test. Reference shared contracts by GUID, never reach across sibling feature assemblies (that is the cycle smell from unity-asset-hygiene.md).

Editor (<Company>.<Game>.<Name>.Editor):
  {
    "name": "<Company>.<Game>.<Name>.Editor",
    "rootNamespace": "<Company>.<Game>.<Name>.Editor",
    "references": ["GUID:<this feature's Runtime asmdef guid>"],
    "includePlatforms": ["Editor"],
    "autoReferenced": false
  }
  Runtime must never reference this back.

EditMode tests (<Company>.<Game>.<Name>.EditModeTests):
  {
    "name": "<Company>.<Game>.<Name>.EditModeTests",
    "references": ["GUID:<Runtime guid>", "UnityEngine.TestRunner", "UnityEditor.TestRunner"],
    "includePlatforms": ["Editor"],
    "precompiledReferences": ["nunit.framework.dll"],
    "overrideReferences": true,
    "autoReferenced": false,
    "defineConstraints": ["UNITY_INCLUDE_TESTS"]
  }

PlayMode tests (<Company>.<Game>.<Name>.PlayModeTests): same as EditMode but drop "includePlatforms" (so it runs in a Player too).

Use GUID references ("GUID:...") not name strings, so renaming an .asmdef does not break downstream (unity-asset-hygiene.md). To get a referenced asmdef's GUID, read its sibling .asmdef.meta or query the map.

NEW GAME SKELETON (rare)

Only when standing up a brand-new game. Create the full taxonomy from unity-architecture.md: Assets/<Project>/{Bootstrap,Shared,Features,Worlds}, Assets/Sandboxes/, Assets/ThirdParty/, a Bootstrap.Runtime asmdef as the composition root, a Core/Foundation.Runtime asmdef (often noEngineReferences) that features depend on, and the verify settings from unity-asset-hygiene.md (Force Text, Visible Meta). Register the game in project-config.md GAMES. Drop .keep files in empty folders for Git safety.

AFTER WRITING

1. refresh_unity (Unity MCP) so the Editor imports the new asmdefs and generates their .meta GUIDs.
2. read_console for compile errors (an asmdef typo or a missing GUID reference surfaces here). Fix before handing back.
3. State the FULL absolute paths of every folder + asmdef created (memory:feedback_always_full_paths).
4. Do NOT commit. Scaffolding is scaffolding; the commit happens after real work lands (commit-cadence.md), and one-shot scaffold output is not shipped game code.

GUARDRAILS

- never write .prefab / .unity / .asset YAML here (those come from Builders or Unity MCP)
- never scaffold into another dev's folder; surface the path and ask (folder-ownership.md)
- do not draw an asmdef around a trivial subfolder; one per stable feature seam (unity-asset-hygiene.md)
- a feature that needs to reach into 3+ other features at scaffold time is a design smell; write the integration contract in systemPatterns.md first (codeRules 24)

Cross-reference

  .claude/rulebook/unity-architecture.md      the design intent this skill materializes
  .claude/rulebook/unity-asset-hygiene.md      asmdef settings + the cycle/seam rules
  .claude/rulebook/folder-ownership.md         who owns which subtree
  .claude/rulebook/project-config.md           GAMES table, namespace/company prefix
  .claude/rulebook/unity-mcp-and-builders.md   how prefabs/SO/scenes get built later (not here)
