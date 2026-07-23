Unity architecture reference (OPT-IN guidance, new-work only)

Loaded by: scaffolding a NEW game, a NEW feature/system module, or an explicit architecture/refactor decision on how to lay out a Unity codebase. NOT always-on, and NOT a hard rule. This is the gold-standard end-state dr-5/dr-6 recommend; existing games (EO multi-dev per-folder, ZC solo) do not match it and must NOT be force-migrated. Use it to shape new modules, and as the target when someone explicitly asks to restructure.

Relationship to the hard rules: codeRules.md (1-28) and gameRules.md (1-39) are the always-on invariants and already cover null/alloc/lifecycle/networking/testing/IDD. This file does not restate them; it FRAMES them into a layered model and adds the structural + design-pattern choices those rule files leave open. unity-asset-hygiene.md holds the always-on asset/asmdef/addressables invariants. Grounded in dr-5 + dr-6 (Unity 6 large-project structure + scalable architecture, both cite Unity 6 manuals, Unity Learn MVP/MVVM, Microsoft DI, VContainer docs).

LAYERED ARCHITECTURE (the frame for codeRules 19-22)

Pick clear layers, keep dependency arrows pointing inward. codeRules 19/20 ("logic in plain C#, MonoBehaviour is an integration point") is the two-line version; this is the full shape:
  Presentation   Views (uGUI MonoBehaviour or UI Toolkit UXML wrapper) + Presenters/ViewModels (screen logic only)
  Application    use cases, coordinators, game-flow services, commands/queries, orchestration, policies
  Domain         pure C# game rules + state transitions, NO UnityEngine dependency
  Infrastructure scene loading, persistence, input, audio, networking, analytics; MonoBehaviour glue + ScriptableObject authordata + engine callbacks
  Bootstrap      one composition root that wires the graph and owns lifetimes
Mental model: MonoBehaviour = adapter, ScriptableObject = authored/shared asset, pure C# = rules. Every class then has an expected job and review gets easier.
MVC/MVP/MVVM belong ONLY in the presentation layer, never as the whole-game architecture. Forcing MVP/MVVM to stand in for gameplay shoves domain rules into presenters. The architectural test for any screen: "where does this button change game state?" The answer must be View raises intent > Presenter/ViewModel calls use case > Domain changes > UI refreshes, not "an Inspector event eventually hits a singleton".

PRESENTATION CHOICE

uGUI + MVP is the safe default for screens that lean on serialized events, in-scene authoring, or Animation/Timeline. Keep the view a thin MonoBehaviour: it owns local widget references and translates onClick/slider/toggle into intent calls on a presenter. A button points to OnCraftPressed(), never directly at a save system or quest singleton in the Inspector.
UI Toolkit + MVVM-lite for new, data-rich menus/inventories/codexes/settings/HUDs with lots of synchronized state (Unity 6 runtime data binding makes this pay off). Caveat: binding has setup overhead, it pays off on state-rich UI, not on a two-button dialog.
Do not rewrite working uGUI screens for architectural purity. This is consistent with coding-standards.md UI-Toolkit-text-first (text-first is for agent-authorability; MVP/MVVM is the logic split on top).

DEPENDENCY MANAGEMENT (extends gameRules 22)

gameRules 22 already says prefer VContainer/Reflex, never Zenject on mobile. The hierarchy underneath that:
  1 Manual constructor/method injection is the BASELINE. Constructor injection for pure C# services; method injection or an explicit Initialize(...) for MonoBehaviours (Unity owns their construction, so no constructor injection). Most explicit, least magical, easiest to migrate incrementally.
  2 Service locator is a MIGRATION SEAM, not an architecture. Tolerable as a transitional bridge when refactoring a legacy scene; a bad default because every consumer depends on the locator and dependencies go hidden, the same "hidden global" problem singletons have.
  3 A DI container (VContainer) only when the composition problem is real: reserve it for composition boundaries, not for resolving every bullet. A container that resolves everything plus a bus that replaces every call is indirection overload, not clean architecture.

CROSS-SYSTEM COMMUNICATION (extends codeRules 20)

Use the smallest abstraction that matches the relationship:
  interfaces      for stable directional command/query collaborations (IInventoryReadService, ISaveGameWriter, ISceneNavigator, IPathfinder)
  C# events       for LOCAL publisher/subscriber notifications where the publisher must not know its listeners (HealthChanged, CooldownStarted). Subscribe in OnEnable, unsubscribe in OnDisable (codeRules 25 / gameRules 1 lifecycle pairing)
  typed bus/channel  ONLY for coarse-grained cross-module fire-and-forget broadcasts that would otherwise create ugly reference chains
The mistake is never "using a bus", it is using it for "give me the player position" or "open this popup and return a value" (those are normal dependencies that should stay explicit). One giant GameEvents hub is an unsearchable global nexus; split channels by bounded context (UI events, health events, inventory events).

BOOTSTRAP + SCENE FLOW

One composition root. A dedicated Boot scene or a root lifetime object that exists before other scenes and composes shared services exactly once (logging, settings, save I/O, localization, audio facade, analytics, message bus, scene navigator, scene-flow state machine). Startup-by-convention across scattered Awake/Start/RuntimeInitializeOnLoadMethod is fragile because order within those phases is not guaranteed.
Centralize scene flow. A scene orchestrator in the bootstrap/application layer loads/unloads feature and level scenes explicitly; features REQUEST navigation, they do not call SceneManager directly. Prefer LoadSceneMode.Additive with explicit unloads; put long-living systems in a dedicated persistent scene rather than leaning on DontDestroyOnLoad as the default (gameRules 13 covers async-load, this covers ownership of the flow).

FOLDER TAXONOMY (greenfield recommendation, NOT a retrofit rule)

dr-5's purpose-driven shape for a NEW game. Organize by purpose, not by asset type (Assets/Prefabs, Assets/Textures is fine only while tiny). Path encodes ownership + purpose, name encodes role: Features/Combat/Prefabs/EnemyGoblin.prefab beats Prefabs/Goblin.prefab.
  Assets/<Project>/Bootstrap/        boot + persistent scenes, startup data
  Assets/<Project>/Shared/           genuinely-global art/audio/materials/vfx/prefabs/data (a curated public API, things graduate here only once truly shared)
  Assets/<Project>/Features/<Name>/  Runtime/ Editor/ Tests/ Data/ Prefabs/ (domain ownership; feature-specific stays in the feature)
  Assets/<Project>/Worlds/<Name>/    Scenes/ Lighting/ Nav/ Data/ (location/level content sliced by concern)
  Assets/Sandboxes/<UserName>/       the ONLY place for throwaway prefabs/test scenes/experiments; production graduates out, junk dies here
  Assets/ThirdParty/                 third-party content kept separate from owned work
  Packages/com.<studio>.<project>.*  mature/reusable subsystems graduate into internal UPM packages (Runtime/ Editor/ Tests/)
Make the per-feature inner shape repetitive so modules are easy to package, validate, and review. Reuse the same shape via an Editor template (see the unity-scaffold skill).
Existing-game reality: Existing projects may use a different layout. Do not impose Features/Worlds on a mature tree; apply it to a brand-new game or a self-contained module that does not fight the established layout. When in doubt, ask the project owner.

PREFAB TIERS

The healthy structure for a new authored object: base prefab (stable reusable thing) > nested child prefabs (sockets, FX anchors, health bars, shared modules) > variants (recurring authored differences). Scene instance stays boring. The always-on discipline (variant depth cap, override rules, Unpack-sparingly) lives in unity-asset-hygiene.md; this is the design intent behind it.

TESTABILITY SHAPE (frames gameRules 28-32)

Domain tests: pure C#, no UnityEngine, many fast EditMode tests. Application/use-case tests: EditMode with fakes (fake save service, fake clock, fake repository). Presenter/ViewModel tests: EditMode with fake view interfaces. Adapter contract tests: thin, prove a Unity adapter satisfies its port. PlayMode smoke tests: one or two per key scene/bootstrap path plus scene-load and critical prefab-wiring proof (this is the wiring-enforcement.md runtime leg). Push test VOLUME to EditMode; reserve PlayMode for the Unity-facing seams.

Cross-reference

  unity-asset-hygiene.md        always-on asset/asmdef/addressables/prefab-discipline invariants (the enforcement arm of this guidance)
  .claude/skills/unity-scaffold/SKILL.md   materializes the folder taxonomy + asmdef triple for a new feature/game
  workflow/memory-bank/studio/codeRules.md   always-on code invariants (19-22 architecture)
  workflow/memory-bank/studio/gameRules.md   always-on game invariants (13-14 scene/asset, 19-23 architecture, 28-32 testing)
  .claude/rules/wiring-enforcement.md   the runtime-reachability proof the PlayMode smoke tests satisfy
