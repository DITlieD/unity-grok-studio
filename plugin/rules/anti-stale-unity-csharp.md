Unity anti-stale C# (HARD RULE, Unity pack)

Loaded by: any task editing a .cs file in a Unity project.

Training data is 1+ year old and Unity's API surface drifts across LTS lines. Default to verified-current over training instinct; when unsure if a symbol exists in the target Unity version, clear it via unity_reflect / unity_docs BEFORE writing it (verify-before-write).

- Object lookup: FindObjectsByType / FindFirstObjectByType (2022.2+) replace the deprecated FindObjectsOfType; verify the target version supports them (the unity_symbol_census gate BLOCKs a deny-tier symbol used with no receipt).
- Input: the new Input System (PlayerInput / InputAction) is a package that may not be installed; verify before wiring it, and never assume Active Input Handling.
- Async: UnityEngine.Awaitable is 2023.1+; coroutines are the portable default.
- Content: prefer Addressables / serialized references over Resources.Load (a deprecated sync content path); verify the package is installed.
- Never hand-write a fileID / GUID: scene/prefab/asset YAML is mutated via unityMCP or a builder, never by hand (GUID hallucination corrupts the project).

This is the Unity analog of the general anti-stale-training rule; the toban001 + unity_symbol_census gates enforce the deny-tier subset off-agent.
