unityMCP usage (HARD RULE, Unity pack, MCP/build tasks)

Loaded by: any Unity task that drives the Editor via the unityMCP bridge (scene/prefab/component mutation, run_tests, console reads, builds).

- The bridge is the fragile leg (forwarded localhost WSL->Windows, AOR-D7). The orient brief reports EDITOR/BRIDGE STATE; follow the fallback ladder: bridge connected -> MCP tools; bridge down -> CLI batch-mode + flag the limitation; Editor closed -> Edit/Write the .cs/.uxml/.uss text + surface the fallback (NEVER silently hand-edit scene/prefab/asset YAML).
- After EVERY .cs write: read_console + poll editor_state.isCompiling until the domain reload finishes BEFORE using the new symbol. A new symbol used before the reload completes is a compile error you will not see. This is the Unity cadence the generic packs do not have.
- Mutate scene/prefab/asset via manage_* (manage_gameobject / manage_components / manage_prefabs / manage_scriptable_object / manage_material), never raw YAML.
- run_tests (EditMode + PlayMode) is the auditor's job; it is the off-agent NUnit-XML artifact the agent did not author (AOR-D10). The executor does not self-certify a PlayMode pass.
- find_gameobjects / unity_reflect / unity_docs are read tools; use them to verify before write.
