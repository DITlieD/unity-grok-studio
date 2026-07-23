Unity executor profile (AOR-D9, Unity pack)

Loaded by: the EXECUTOR on any Unity-pack task. The orienter bakes this into the executor prompt as HARD RULES (not advice) when pack=unity. These are acceptance, not suggestions.

MUTATION DISCIPLINE (a violation is a BLOCK):
- Mutate scene/prefab/asset via unityMCP (manage_prefabs / manage_gameobject / manage_components / manage_scriptable_object / manage_material) or a Procedural Builder script. NEVER hand-write .unity / .prefab / .asset YAML: a hand-authored fileID/GUID is a BLOCK (GUID hallucination corrupts the project; the mono_wire_census + asset-hygiene rule enforce it).
- UI is UI Toolkit text-first: author UXML/USS as text via Edit, or manage_ui. uGUI only via builder/MCP, never hand-edited YAML.

COMPILE CADENCE (the domain-reload barrier):
- After EVERY .cs write: read_console + poll editor_state.isCompiling and WAIT for the reload to finish BEFORE using the new symbol. Using a just-written symbol before the reload completes is a compile error you will not see live. This is the Unity cadence vs generic packs that compile inline.

VERIFY-BEFORE-WRITE:
- Before using a version-sensitive / package-gated symbol, clear it via unity_reflect or unity_docs and record a receipt (// UNITY-VERIFY[<symbol>] or a session ledger row). The unity_symbol_census gate BLOCKs a deny-tier symbol with no receipt.

WIRING + ACCEPTANCE (wiring-enforcement R10):
- A new MonoBehaviour/ScriptableObject ships its attachment-or-reference in the SAME change (producer + consumer + smoke). An unattached, unreferenced new component is wire-dark (mono_wire_census BLOCK).
- .cs production cap = 600 lines (toban001 TOBAN-FILESIZE BLOCK); split rather than grow.
- No banned APIs (GameObject.Find / FindObjectsOfType / Camera.main in hot paths / DateTime.Now / Thread.Sleep) -> toban001 BLOCK.
- The slice is DONE when: it compiles clean (read_console verified), the new component is attached/referenced, and the static gates (toban001 / unity_symbol_census / mono_wire_census) are green. The PlayMode run_tests pass is the AUDITOR's off-agent artifact, not the executor's self-claim.

FALLBACK LADDER (AOR-D7): bridge connected -> MCP tools; bridge down -> CLI batch-mode + flag it; Editor closed -> Edit/Write text + surface the fallback. NEVER silently hand-edit YAML to route around a down bridge.
