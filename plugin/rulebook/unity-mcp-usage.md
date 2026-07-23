Unity MCP usage (CoplayDev/unity-mcp, project-scoped via .mcp.json)

Loaded by: conditional-routing.md when the task involves editor-state operations on a Unity game (scene/prefab/asset/component manipulation, running Unity tests, reading Unity Console, materials, animations, profiler, build automation). Token-efficient alternative to hand-editing scene/prefab YAML or shelling out to Unity batch-mode.


PREREQUISITES (BOTH must be true or tool calls fail)

Host side: .mcp.json contains the unityMCP entry pointing at uvx (already wired). Verify with: cat .mcp.json | rg unityMCP
Unity side: the MCPForUnity package must be installed in the active game project AND the bridge window must be running. Install once per game project via:
  Window > Package Manager > "+" > "Add package from git URL" > https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main
Start once per Unity Editor session: Window > MCP for Unity > Start Server
If the Unity Editor is not open or the bridge is not running, ALL Unity MCP tool calls return errors. The model MUST check for "MCP server not connected" style errors and fall back to file-level edits / CLI batch-mode rather than spiraling.


WHEN TO USE THE MCP (preferred over file-level edits)

Reading editor state:
  - read_console > grep Editor.log
  - find_gameobjects > Read on every scene .unity file
  - manage_scene (list/load) > inspect scene YAML
  - manage_packages (list) > read Packages/manifest.json

Writing editor state:
  - manage_gameobject (add/remove/parent/move) > hand-editing scene YAML fileIDs
  - manage_components (add/configure/remove) > hand-editing scene YAML componentIDs
  - manage_prefabs (create/instantiate/apply) > hand-writing .prefab YAML
  - manage_material / manage_shader / manage_texture > editing .mat / .shader / .meta
  - manage_animation > editing .anim / .controller YAML
  - manage_scriptable_object (create/configure) > hand-writing SO .asset YAML

Running tests / builds:
  - run_tests (EditMode + PlayMode) > Unity -batchmode -runTests CLI invocation when the Editor is already open. CLI is still acceptable when the Editor is closed or for headless CI.
  - manage_build > shelling out to Unity -batchmode -buildTarget

Scripts (caveat — see RULES below):
  - apply_text_edits / script_apply_edits / create_script for atomic scoped edits the LLM can verify
  - validate_script before saving a multi-line C# edit
  - find_in_file for symbol locality without a full Read

Performance:
  - manage_profiler for Profiler.BeginSample/EndSample data, GC alloc tracking, frame time samples — avoid hand-rolling profiler runs
  - batch_execute groups multiple ops into ONE call (10-100x faster than individual tool calls per Coplay docs); use it whenever you have 3+ sequential MCP ops on the same Unity Editor


WHEN NOT TO USE THE MCP

  - Pure logic edits to a .cs file that don't need editor state — use Edit / Write directly. Faster, no Unity round-trip.
  - Reading project structure or .cs symbols — Unity MAP-file (.projects/<folder>/map.txt) is faster, deterministic, and works without Unity running. Map first, MCP second.
  - Bulk read of source code — Read / Grep / Glob, not MCP. The MCP is for editor state, not source navigation.
  - Memory-bank / workflow / .claude file edits — never. These are tooling files, not Unity assets.
  - Cross-game operations — MCP binds to ONE Unity Editor instance. The bridge connects to whichever Editor is currently open. Switching games = restart Editor + restart bridge.


RULES (HARD)

1. FSM gate first. Call mcp_fsm_get_state before any Unity MCP call that mutates editor state. EXECUTING / TESTING_FIRST / AUDITING-RUN_TESTS only. CONFIGURING + IDLE are read-only states (find_gameobjects, read_console, manage_packages list). PreToolUse hook will block mutations from non-EXECUTING states.
2. Bridge connectivity check. On the first MCP call of a session, verify connection by calling read_console (cheap, returns immediately if connected). If it errors with "not connected" or similar, surface the failure to the user immediately and fall back. Do NOT retry blindly — that's a spiral.
3. Game scope. Per project boundary rule, the bridge is bound to ONE Unity Editor. Verify the open project matches workflow/sessions/{id}/current-game.txt before mutating. If mismatched: STOP, surface to user.
4. Auditor sole test runner. The main model NEVER calls run_tests. Only the auditor agent calls run_tests, and only in AUDITING/RUN_TESTS sub-state. This rule overrides MCP convenience.
5. No prefab YAML edits. If a task seems to require editing a .prefab or .unity file directly, use the MCP equivalents (manage_prefabs / manage_gameobject / manage_components) or write a C# Builder script. Hand-editing those YAML files is BLOCK per anti-slopsquatting (fileID/GUID hallucination risk).
6. Batch over loops. If you need 3+ sequential MCP ops, use batch_execute. Looping individual calls in chat costs 10-100x more wall time and makes the Editor flicker on every refresh.
7. Read after write. After any mutation (manage_gameobject, manage_components, manage_prefabs, etc.), call refresh_unity then a confirming read (find_gameobjects, find_in_file) to verify the mutation took. The Editor occasionally rejects ops silently when in Play mode or with a compile error pending.
8. Compile error first. If validate_script or read_console reports a compile error, STOP all other MCP work until the compile is green. The Editor will reject most ops while compilation is broken.
9. No script bodies via apply_text_edits for files >150 lines. The hard BLOCK from file-discipline.md still applies. Split first.
10. Debug log strip. Never leave Debug.Log calls inserted via create_script in a finished phase — they violate the "Debug.Log boxing/allocation" rule from anti-stale-unity-csharp.md. Strip with #if UNITY_EDITOR or remove entirely before MEMORIZING.


TOOL REFERENCE (30+ tools, name = canonical MCP tool name)

State / discovery:
  read_console               read Unity Console (errors, warnings, logs) since last clear
  find_gameobjects           query scene for GameObjects by name/component/tag
  find_in_file               grep within a single .cs file via the Editor's index
  unity_reflect              query type/method/field metadata via reflection
  unity_docs                 fetch official Unity docs for a symbol
  manage_editor              query/set Editor state (play mode, selection, active scene)
  set_active_instance        if multiple Editors are open, target one specifically

GameObject / component / scene:
  manage_gameobject          create / delete / parent / move / activate
  manage_components          add / configure / remove components on a GameObject
  manage_scene               create / load / save / unload scenes
  manage_prefabs             create / instantiate / apply prefab variants
  manage_camera              configure camera component
  manage_physics             configure physics components, materials, layers (21 actions in v9.6.x)

Asset:
  manage_asset               import / export / move / delete assets
  manage_material            create / configure materials
  manage_shader              configure shader assets
  manage_texture             import / configure textures (compression, filtering)
  manage_animation           create / configure animation clips and controllers
  manage_vfx                 VFX Graph integration
  manage_ui                  UI Toolkit / Canvas operations
  manage_probuilder          ProBuilder mesh ops (if package installed)
  manage_scriptable_object   create / configure SO instances

Script:
  create_script              create a new .cs file
  delete_script              delete a .cs file
  manage_script              broader script ops
  manage_script_capabilities query what the MCP can edit safely
  validate_script            compile-check a script before save
  apply_text_edits           atomic scoped edits to a .cs file
  script_apply_edits         alias / variant of apply_text_edits

Build / test / profile:
  run_tests                  EditMode + PlayMode tests (auditor only)
  manage_build               build automation, multi-platform
  manage_profiler            profiler data (14 actions in v9.6.x)
  refresh_unity              force AssetDatabase.Refresh + recompile

Misc:
  batch_execute              run multiple MCP ops in one call (10-100x faster)
  execute_menu_item          fire an Editor menu item (Window > X > Y)
  execute_custom_tool        custom user-registered tool
  manage_packages            install / list / remove UPM packages
  manage_graphics            URP / HDRP / built-in pipeline ops
  manage_tools               meta — list available tools, capabilities
  debug_request_context      diagnostic dump for bug reports
  get_test_job               poll an async test job
  get_sha                    fetch git SHA of the running MCP server (version pinning)


VERSION PINNING

Current pin: mcpforunityserver from PyPI (latest at uvx invocation). v9.6.8 (2026-04-27) is the verified-working baseline; the v9.4.6 Windows stdio bug (issue #773) is fixed in 9.6.x.
Unity package version: github main branch via Package Manager. To pin a specific commit, swap #main for #<sha> in the git URL.
If MCP behavior changes unexpectedly, check get_sha and the Releases page for breaking changes.


FALLBACK LADDER (when Unity MCP is unreachable)

  1. Verify Unity Editor is running with MCPForUnity package + bridge started (Window > MCP for Unity > Start Server).
  2. If Editor is closed: fall back to Unity -batchmode CLI for builds/tests, file-level Edit/Write for .cs sources, MAP-file query for symbol lookup. Surface the fallback to the user explicitly.
  3. If bridge is hung: ask user to restart it before retrying. Do NOT spam reconnect attempts.
  4. If MCP is uninstalled in the active game project: install via Package Manager git URL above, then retry. This is a one-time per-game-project setup.


CROSS-REFERENCE

Install + config: .mcp.json (host-side, project root)
Symbol search before MCP: .claude/rules/unity-map-usage.md
File-discipline limits still apply: .claude/rules/file-discipline.md
Unity-specific staleness rules: .claude/rules/anti-stale-unity-csharp.md
Auditor RUN_TESTS sub-state: .claude/agents/auditor.md
Repo: https://github.com/CoplayDev/unity-mcp (MIT)
