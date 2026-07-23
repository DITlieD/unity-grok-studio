Anti-Stale-Training: Unity and C# (HARD RULE)

Training data is 1+ year old. The following substitutions are mandatory. When unsure about any Unity API or C# pattern, WebSearch before using it.
Research basis: Gemini Deep Research 2026-04-13 (111 sources consolidated).

Unity API staleness — verified compile/runtime breakage (highest risk):

NEVER use FindObjectOfType<T>(). Use FindFirstObjectByType<T>() (Unity 2023+). Old version does full-scene traversal. COMPILE_ERROR in future versions.
NEVER use Physics2D.RaycastNonAlloc(). Removed. Use Physics2D.Raycast() with NativeArray overloads.
NEVER use PhysicMaterialCombine. Renamed to PhysicsMaterialCombine (typo fix). COMPILE_ERROR.
NEVER use UnityEngine.Social.*. Removed in Unity 6. Use third-party SDKs.
NEVER use Advertisement.AddListener() (Unity Ads 4.x). Use LevelPlayRewardedAd.LoadAd() (Ads 9.x).
NEVER use ExecuteDefaultAction() in UI Toolkit. Use HandleEventTrickleDown(). COMPILE_ERROR.
NEVER use UxmlFactory classes. Use [UxmlElement] attribute (Unity 2023.2+). Deprecated.
NEVER use class MySystem : ComponentSystem (DOTS). Use partial struct MySystem : ISystem (DOTS 1.0+). COMPILE_ERROR.
NEVER use evt.PreventDefault() in UI Toolkit. Deprecated. Use evt.StopPropagation().

Unity API staleness — performance/correctness:

NEVER use OnGUI() for runtime UI. Use UI Toolkit (UIDocument + UXML + USS) or Unity UI (Canvas + TMP). OnGUI is editor-only in modern Unity.
NEVER use PlayerPrefs for anything beyond trivial settings. Use a serialization system for game state.
NEVER use Resources.Load at runtime in production. Use Addressables. Resources/ folder bakes everything into binary, causes massive startup delay. Universally condemned for production (research Part 11).
NEVER use WWW class. Removed. Use UnityWebRequest.
NEVER use GUIText, GUITexture, or legacy UI. Removed in Unity 2022+.
NEVER use Input.GetKey/GetAxis/GetButton (legacy Input). Use Input System package (InputAction). RUNTIME_ERROR if old system disabled in Player Settings.
NEVER use SendMessage/BroadcastMessage. Reflection + allocation. Use events, interfaces, or direct references.
NEVER use Application.LoadLevel. Use SceneManager.LoadSceneAsync.
NEVER use string-based Animator parameters. Cache with Animator.StringToHash() in static readonly fields.
NEVER use Camera.main in Update — calls FindGameObjectWithTag internally. Cache the reference.
NEVER use Renderer.material (silently clones material -> VRAM leak). Use Renderer.sharedMaterial or MaterialPropertyBlock. CAVEAT: MaterialPropertyBlock breaks SRP Batcher (research Part 7 item 176) — prefer sharedMaterial with variant switching for SRP projects.
NEVER use AudioSettings.speakerMode directly. Use AudioSettings.GetConfiguration().
NEVER use NavMesh.CalculatePath synchronously in gameplay. Use NavMeshQuery + Job System + Burst.
NEVER use continuous ServerRpc in Update for state sync. Use NetworkVariable<T> with OnValueChanged.
NEVER use [Command]/[ClientRpc] (Mirror) if project uses Netcode for GameObjects. Namespace mismatch = COMPILE_ERROR.

Prefer async Awaitable (Unity 6+) over coroutines for new async code. NEVER use async Task/void for Unity async — thread pool bypasses PlayerLoop, causes memory leaks (research top hallucination #1).
Prefer TextMeshPro (TMP) over legacy Text component. Built-in since Unity 2021.
Prefer ObjectPool<T> from UnityEngine.Pool over custom List<GameObject> pooling implementations.
Prefer Burst-compiled jobs (IJobParallelFor + [BurstCompile]) for CPU-heavy work over manual threading.
Prefer Sprite Atlas v2 over legacy Sprite Packer.
Prefer VContainer or Reflex for DI over Zenject (Zenject uses runtime reflection, slow startup, high allocs, IL2CPP unsafe — research Part 8).
Prefer UI Toolkit for layout menus/inventories/metagame (3x faster CPU, 2.6x less memory vs Canvas — research Part 10). Legacy Canvas still needed for world-space UI (health bars).

C# language constraints in Unity 6 (CRITICAL — LLMs generate code that won't compile):

Unity 6 locks Roslyn compiler to C# 9.0 by default. The following C# 10+ features WILL NOT COMPILE unless the project explicitly upgrades the compiler:
- File-scoped namespaces (C# 10) — VERIFY project supports before using.
- Primary constructors (C# 12) — VERIFY.
- Required members (C# 11) — VERIFY.
- Collection expressions (C# 12) — VERIFY.
- List/property patterns (C# 10/11) — VERIFY.
Record types: compile in C# 9 BUT Unity serialization silently drops data (Inspector blank, JsonUtility fails). Do NOT use records for serialized data.
init-only setters: need IsExternalInit polyfill (missing in .NET Standard 2.1). COMPILE_ERROR without polyfill.
RULE: before using any C# feature above 9.0, grep the project for LangVersion in .csproj or verify in Player Settings. Default = C# 9.0.

C# general staleness:

NEVER use ArrayList, Hashtable, or non-generic collections. Use List<T>, Dictionary<TKey,TValue>, HashSet<T>.
NEVER use string concatenation in loops. Use StringBuilder or string.Join.
NEVER use Thread directly for game logic. Use Unity's Job System + Burst or async/await with Awaitable.
NEVER use lock(this) or lock on public objects. Use a private readonly object for locks.
NEVER use System.Random for security. Use System.Security.Cryptography.RandomNumberGenerator. For game randomness, Unity.Mathematics.Random (deterministic, seedable).

Mobile-specific staleness:

NEVER use LINQ in gameplay code — it allocates. Use manual loops or NativeArray + Jobs.
NEVER use async void except for Unity event handlers. Use async Awaitable or async UniTask. Always attach destroyCancellationToken to prevent orphaned tasks after scene change/object destroy.
NEVER use reflection at runtime on mobile (IL2CPP High stripping strips it -> MissingMethodException on device only, works fine in Editor). Serialization must be AOT-safe. Maintain link.xml whitelists.
NEVER use Debug.Log in production builds — boxing + string allocation. Strip with #if UNITY_EDITOR or Conditional attribute.
Prefer IL2CPP over Mono for release builds (required for iOS, mandatory for performance on Android).
Prefer ARM64 only for Android builds. Google Play mandates Android 15 (API 35) + ARM64 by late 2025. 32-bit is EOL.
Prefer ASTC 6x6 texture compression (standard 2024-2026). ETC2 only for legacy GLES 3.0 fallback. Force max 1024x1024 for standard 3D background assets.
Prefer GPU instancing or SRP Batcher over dynamic batching (deprecated and unreliable).
Prefer half-precision floats in shaders (2 ops per cycle on mobile GPU). Minimize texture samples (memory lookups > math ops on mobile).

Top 10 AI hallucination patterns (from research, ranked by frequency):

1. async Task/void instead of async Awaitable — thread pool bypasses PlayerLoop, memory leaks
2. Hallucinated namespaces (e.g. UnityEngine.AI.Navigation sub-namespaces that don't exist) — supply chain attack vector via slopsquatting
3. Continuous ServerRpc in Update instead of NetworkVariable<T> with OnValueChanged
4. GetComponent<T>() in Update() instead of cached references
5. renderer.material.color instead of sharedMaterial/MaterialPropertyBlock — VRAM leak
6. evt.PreventDefault() (deprecated) instead of evt.StopPropagation()
7. Missing destroyCancellationToken on async methods — orphaned tasks
8. Mixing incompatible architectural styles ("zebra pattern")
9. Synchronous NavMesh.CalculatePath instead of NavMeshQuery + Jobs + Burst
10. Custom List<GameObject> pooling instead of UnityEngine.Pool.ObjectPool<T>