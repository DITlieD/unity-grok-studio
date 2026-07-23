---
name: unity-scaffold
description: >
  Scaffold a new Unity feature module or new game project skeleton to the purpose-driven
  layout: Features/Worlds/Shared folder shape plus the runtime/editor/test asmdef quartet
  with correct references and settings. Triggers on "scaffold a new feature", "set up a new
  module", "create the <X> feature", "stub the asmdefs for <X>", "new game skeleton".
  Writes .asmdef JSON + folders + a CODEMAP stub (plain text, NOT scene/prefab YAML).
  Does NOT generate gameplay code or prefabs.
---

# UNITY SCAFFOLD

Turns the greenfield guidance in `rulebook/unity-architecture.md` into real folders +
asmdef files for a new feature module (common) or a new game skeleton (rare).

## When to invoke
- "scaffold a new feature", "create the <Name> feature/module/system", "stub asmdefs"
- "new game skeleton" / "lay out a new game"
- user wants the folder taxonomy + asmdef triple made real

## When NOT
- generating gameplay code, prefabs, ScriptableObject assets, or scenes — that is normal
  implementation (Unity MCP / builders), not this skill
- force-migrating an existing game whose layout is already established — ask the owner
  where the new module should live

## Prerequisite checks
1. Confirm the target Unity project root (`UNITY_PROJECT` or explicit path). New work
   stays inside that project.
2. Backup any file you would overwrite into `_Backups/{timestamp}/` first. Scaffolding
   should only CREATE; if a path already exists, stop and surface it.
3. Pick company/namespace prefix from the project (or `Company.Game` placeholder).

## Feature module shape (default)

```
Features/<Name>/
  Runtime/        <Company>.<Game>.<Name>.asmdef
  Editor/         <Company>.<Game>.<Name>.Editor.asmdef
  Tests/
    EditMode/     <Company>.<Game>.<Name>.EditModeTests.asmdef
    PlayMode/     <Company>.<Game>.<Name>.PlayModeTests.asmdef
  Data/
  Prefabs/
  UI/             optional <Name>Screen.uxml + .uss
  CODEMAP.md
```

## Asmdef templates

Runtime:
```json
{
  "name": "<Company>.<Game>.<Name>",
  "rootNamespace": "<Company>.<Game>.<Name>",
  "references": ["GUID:<Core/Foundation asmdef guid>"],
  "autoReferenced": true,
  "overrideReferences": false,
  "noEngineReferences": false
}
```
Pure-domain assemblies may set `"noEngineReferences": true`. Reference shared contracts by
GUID; never reach across sibling feature assemblies.

Editor: `includePlatforms: ["Editor"]`, reference this feature's Runtime GUID,
`autoReferenced: false`. Runtime must never reference Editor back.

EditMode tests: reference Runtime + TestRunner assemblies, `includePlatforms: ["Editor"]`,
`precompiledReferences: ["nunit.framework.dll"]`, `defineConstraints: ["UNITY_INCLUDE_TESTS"]`.

PlayMode tests: same without `includePlatforms`.

## New game skeleton (rare)
Create taxonomy from unity-architecture.md: `Assets/<Project>/{Bootstrap,Shared,Features,Worlds}`,
`Assets/Sandboxes/`, `Assets/ThirdParty/`, Bootstrap.Runtime as composition root,
Core/Foundation.Runtime for features to depend on. Force Text + Visible Meta serialization.

## After writing
1. refresh_unity (Unity MCP) so the Editor imports asmdefs and generates .meta GUIDs.
2. read_console for compile errors; fix before handing back.
3. State full paths of every folder + asmdef created.
4. Do NOT commit scaffolding alone as ship code.

## Guardrails
- never write .prefab / .unity / .asset YAML here
- do not draw an asmdef around a trivial subfolder
- a feature that needs 3+ sibling features at scaffold time is a design smell

## Cross-reference
- `$GROK_PLUGIN_ROOT/rulebook/unity-architecture.md`
- `$GROK_PLUGIN_ROOT/rulebook/unity-asset-hygiene.md`
- `$GROK_PLUGIN_ROOT/rulebook/unity-mcp-and-builders.md`
- UPM tools: `unity-packages/com.unitygrok.uitools` menus under Tools/UnityGrok/
