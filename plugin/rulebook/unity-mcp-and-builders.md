Unity MCP first + Procedural Builder + UI Toolkit text-first (HARD RULES)

Loaded by: any task touching scene/prefab/asset YAML, ScriptableObject .asset files, UXML/USS, or component manipulation in a Unity game project.

These three rules form a family: they all prevent fileID/GUID hallucination by routing edits through the Editor's serialization pipeline (Unity MCP) or through deterministic C# Builder code. Hand-editing YAML is BLOCK.

Unity MCP first

For any Unity Editor-state operation (scene/prefab/asset/component/material/animation/shader/profiler/build/test) on a game where the Unity Editor is running with the MCPForUnity bridge connected, USE Unity MCP tools instead of hand-editing YAML or shelling to Unity batch-mode.

Tools (mcp__unityMCP__):
  - manage_gameobject, manage_components, manage_scene, manage_prefabs
  - manage_material, manage_shader, manage_texture, manage_animation, manage_vfx
  - manage_ui (UXML / USS), manage_scriptable_object
  - read_console, find_gameobjects, find_in_file
  - manage_editor (play mode, selection, active scene)
  - run_tests (AUDITOR ONLY, in AUDITING/RUN_TESTS sub-state)
  - batch_execute (10-100x faster when 3+ ops; use it)
  - refresh_unity (after writes, before reading state back)

Bridge required:
  Install MCPForUnity Unity package per-game (one-time, Package Manager git URL: https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main).
  Start per-session: Window > MCP for Unity > Start Server.

Fallback (bridge unreachable):
  Editor closed: Unity -batchmode CLI for builds/tests, file-level Edit/Write for .cs sources, MAP-file query for symbol lookup. Surface the fallback explicitly.
  Bridge hung: ask user to restart it before retrying. Do NOT spam reconnect attempts.

See .claude/rules/unity-mcp-usage.md for full tool list, FSM gates, and version pinning.

Procedural Builder over prefab YAML

NEVER hand-write .prefab or .unity YAML. fileID and GUID hallucination is the most common LLM failure mode for Unity assets.

To create a new prefab:
  Option A — write a C# Builder script either as an edit-time MenuItem (Editor folder, [MenuItem("Tools/Build/MyPrefab")]) or a runtime Awake/Start initializer. The Builder constructs the GameObject, AddComponent<T>, sets serialized field values, and (for MenuItem variant) PrefabUtility.SaveAsPrefabAsset.
  Option B — use Unity MCP manage_prefabs / manage_gameobject / manage_components, which mediate the YAML write through the Editor's serialization pipeline.

Same rule for ScriptableObject .asset files — use ScriptableObject.CreateInstance + AssetDatabase.CreateAsset in a Builder, OR Unity MCP manage_scriptable_object.

UI Toolkit text-first

For any new UI Toolkit work, write UXML (XML markup) and USS (CSS-shaped styling) as text directly. UXML is XML, USS is CSS-shaped — both are LLM-native.

Edit UXML/USS via Edit/Write or Unity MCP manage_ui. Do NOT require the user to round-trip through the UI Builder visual editor for layouts expressible as markup.

Unity Toolkit (Unity 6+) is preferred for menus, HUD, inventory, metagame UI. Unity UI + TextMeshPro acceptable for world-space UI (health bars over enemies). No legacy OnGUI / GUIText / GUITexture (removed Unity 2022+).

Cross-reference

  .claude/rules/unity-mcp-usage.md — full Unity MCP tool catalog, FSM rules, fallback ladder
  .claude/rules/unity-map-usage.md — symbol lookup BEFORE reading .cs files
  .claude/rules/coding-standards.md — coding-side rules for UI authoring + prefab construction
