Unity architecture (HARD RULE, Unity pack)

Loaded by: any task adding or restructuring a MonoBehaviour, ScriptableObject, or system in a Unity project.

- Every NEW MonoBehaviour/ScriptableObject MUST be reachable: attached to a GameObject/prefab/scene by its GUID, OR referenced by another script (AddComponent<T>, a typed field, GetComponent<T>). A component attached to nothing and referenced by nothing is WIRE-DARK (the mono_wire_census gate BLOCKs it). This is the Unity producer-without-consumer rule (wiring-enforcement R6/R7): ship the producer AND its attachment/reference in the same change.
- Cache references in Awake/Start, never per-frame in Update (GameObject.Find / GetComponent / Camera.main in a hot path are toban001 findings). Inject or serialize dependencies; do not scan the scene.
- Keep MonoBehaviours small and single-responsibility; the .cs production cap is 600 lines (toban001 TOBAN-FILESIZE BLOCK). Extract systems/helpers rather than growing a god-component.
- Prefer composition (small components) + ScriptableObject config over deep inheritance; data that designers tune lives in a ScriptableObject asset, not hardcoded.
- Determinism: no DateTime.Now (use Time.time or a seeded clock); no Thread.Sleep on the main thread (coroutine/async).
