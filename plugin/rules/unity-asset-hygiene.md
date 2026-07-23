Unity asset hygiene (HARD RULE, Unity pack)

Loaded by: any task that moves, renames, or creates a Unity asset (scene/prefab/material/ScriptableObject/texture), or edits scene/prefab/asset YAML.

- NEVER hand-edit .unity / .prefab / .asset YAML. Mutate via unityMCP (manage_prefabs / manage_gameobject / manage_components / manage_scriptable_object / manage_material) or a Procedural Builder script. Hand-writing a fileID/GUID is a BLOCK (the Unity executor profile + the mono_wire_census enforce this).
- Move/rename assets in the Editor (or via unityMCP manage_asset), NEVER raw mv: the .meta GUID must travel with the file or every reference breaks.
- Keep the .meta sidecar in lockstep with its asset; a .cs with no .cs.meta has no GUID, so it can never be attached (the wire census treats it as unattachable).
- FormerlySerializedAs on a renamed serialized field so existing scene/prefab data survives the rename.
- Prefab variant depth cap 2 (deeper variant trees are a maintenance hazard).
- Keep Asset Serialization = Force Text (so YAML diffs are reviewable + the analyzers can read GUIDs).

These invariants surface into the orient brief's ASSET-HYGIENE never-change list (AOR 9.4).
