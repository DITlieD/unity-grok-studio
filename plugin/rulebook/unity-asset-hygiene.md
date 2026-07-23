Unity asset + structure hygiene (HARD RULE, project-corruption class)

Loaded by: any task that creates/moves/renames a prefab, scene, ScriptableObject, or asset folder; edits an .asmdef; touches Addressables groups; or changes Unity VCS/serialization settings. Pairs with unity-mcp-and-builders.md (the ban-YAML family) and project ownership docs (dev-ownership axis, orthogonal to this file).

Why this exists

unity-mcp-and-builders.md stops the agent hand-writing YAML. This file stops the agent silently corrupting a project's asset graph, prefab inheritance, assembly graph, or memory profile while doing legitimate edits. These are stack invariants, they hold on every game regardless of folder layout, and none were codified before. Grounded in dr-5 (Unity 6 large-project structure, cites Unity 6.4 manuals). Distinct from the greenfield design guidance in unity-architecture.md, which is opt-in when scaffolding new work; everything here is always-on when the trigger fires.

META FILE + VERSION CONTROL HYGIENE

Move and rename assets INSIDE Unity (or via Unity MCP manage_asset), never in Explorer / Finder / a raw mv. A .meta file carries the asset GUID and import settings; separating an asset from its .meta breaks every reference to it. Renaming a folder in Explorer is a classic silent disaster. If the Editor is closed, move the .cs/.meta pair together as one unit and surface that you did the filesystem move by hand.
Serialized-field renames in shipped code use [FormerlySerializedAs("oldName")], never a bare rename. A bare rename drops the serialized value and orphans the override in every scene/prefab that set it.
Empty production folders: Git does not track them but commits the folder .meta, so other machines get a dangling .meta Unity then deletes. Drop a .keep file in any empty folder that must exist, or do not commit it. UVCS handles empty folders as first-class, so this trap is UVCS-safe but the .keep habit is still correct for Git mirrors.
Project settings that are infrastructure, not preference: Asset Serialization = Force Text, Version Control mode = Visible Meta Files, and Reduce version-control noise ON. If a task changes any of these away from those values, that is a BLOCK unless the project owner asked for it.
Configure UnityYAMLMerge (Smart Merge) for .unity and .prefab before any scene/prefab merge. Even so, do not let three people hammer one mega-scene or hero-prefab; split it or treat it as lock-worthy during active work. For non-mergeable binaries (models, images, audio) use UVCS Smart Locks or Git-LFS locks.

PREFAB ARCHITECTURE DISCIPLINE

Compose, do not build god prefabs. The intended Unity 6 model is base prefab + nested child prefabs (sockets, FX anchors, health bars, shared modules) + variants for recurring authored differences (EnemyGoblin_Elite). The scene instance stays boring: placement plus a tiny number of one-off overrides.
Variant depth cap: 2 meaningful inheritance hops. Past that nobody can tell where a property comes from. Deeper chain = extract a smaller nested prefab or pull data into a ScriptableObject.
Override discipline: a change for ALL uses applies to the prefab asset; a change for a recurring subgroup becomes/updates a variant; only genuinely scene-specific values stay as instance overrides. A scene instance carrying more than a handful of persistent overrides is a smell, flag it for a new variant or nested prefab.
Unpack is an explicit exception, never the default edit move. Unpacking severs the link to the source prefab and reintroduces scene drift through the back door. If a task unpacks a prefab as routine editing that is a WARN, justify it or re-link.
Author reusable config as standalone ScriptableObject ASSETS. A ScriptableObject referenced from a scene object but never saved as an asset gets serialized inline into the scene file, which is exactly the fragile graph we are avoiding. Create via ScriptableObject.CreateInstance + AssetDatabase.CreateAsset (Builder) or Unity MCP manage_scriptable_object.

ASSEMBLY DEFINITION SETTINGS (the detail gameRules 19 omits)

gameRules 19 mandates asmdefs past ~10 scripts; this is HOW. Each module gets a runtime/editor/test triple: <Module>.Runtime, <Module>.Editor (references Runtime only), <Module>.Tests (EditMode and/or PlayMode, reference Runtime). Runtime code must never reference Editor code.
Use GUIDs for assembly references ON, so renaming an .asmdef does not force downstream edits.
Auto Referenced OFF for opt-in libraries you do not want the predefined assemblies to pull in automatically.
No Engine References ON for pure C# domain/core assemblies that must stay Unity-independent (and therefore fast-testable in EditMode and reusable). Use Define Constraints for editor-only or optional-package code.
A cyclical assembly reference is a compile error AND a design signal: do not fight it, extract the shared contracts into a smaller lower-level assembly, or admit the two halves are one module and merge them. Never draw an .asmdef around an arbitrary subfolder, draw it around a stable dependency seam. An .asmdef per tiny directory is bureaucracy, none is a hairball.
PlayMode test assemblies cannot reference the predefined Assembly-CSharp, so code you want to test must already live behind a custom asmdef. This is why asmdefs come early, not as a late cleanup.

ADDRESSABLES GROUPING (the detail gameRules 14 omits)

codeRules 7 + gameRules 14 already mandate Resources-banned-in-gameplay and Release-paired-with-LoadAssetAsync; do not restate those, this adds grouping + the decision tree.
Group assets by how they are LOADED AND UNLOADED TOGETHER, by lifetime, never by type. No giant "all prefabs" or "all materials" group. Folder structure and Addressables groups should line up so a misplaced asset is visible twice.
Decision tree: direct reference for always-present base-game content that ships in the install and is not streamed (Unity includes only directly-referenced assets, so this can reduce build size); Addressables for content loaded by lifetime, patched/delivered remotely, or memory-sensitive prefabs/UI; Resources only for tiny bootstrap config where you knowingly accept that every Resources asset is always in the build; raw AssetBundles only when you specifically need lower-level control than Addressables gives. Keep bundles under ~5MB for mobile download (gameRules 14).
If scenes load additively at runtime, bake them additively in authoring (occlusion/lighting data is shared only when the additive group is opened and baked together). Define additive scene groups as a first-class authoring unit, not just a runtime convenience.

Cross-reference

  unity-mcp-and-builders.md      never hand-write YAML; route prefab/SO/scene writes through MCP or a C# Builder
  unity-architecture.md          greenfield folder taxonomy, layered architecture, DI/communication (opt-in, new work only)
  project ownership docs            which dev owns which subtree (a different axis from this file)
  workflow/memory-bank/studio/gameRules.md   rules 14 (addressables), 19 (asmdefs mandatory), 16 (SO data)
  workflow/memory-bank/studio/codeRules.md   rule 7 (Resources/Release), 27 (serialization)
