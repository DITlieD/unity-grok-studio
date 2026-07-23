Unity MAP-file usage (LLM instructions)

Loaded by: conditional-routing.md when the task involves reading/understanding game code, locating a symbol, tracing callers, finding scene/prefab references, or scouting a file's neighborhood. The MAP is a token-efficient alternative to Read/Grep across many .cs files.


WHEN TO USE THE MAP

Use map.txt BEFORE reading any .cs file for any of the following:
  - "where is X defined" / "what file is X in"
  - "what calls X" / "what does X call"
  - "what's in this scene/prefab" / "which MonoBehaviour is attached"
  - "what lifecycle methods does this class have"
  - "what are the SerializeField fields on this class"
  - "list all singletons" / "list all MonoBehaviours" / "list all reflection usage"
  - "what does <author> own"

Prefer one rg against map.txt over multiple Read/Grep across Assets/Scripts/. A single rg hit returns the full symbol neighborhood.


WHERE THE MAPS LIVE

  .projects/Zombie_Citizen/map.txt              game=zombie-citizen
  .projects/Final_Fantasy_Tactics/map.txt       game=everlasting-odyssey

Both files are gitignored (.gitignore entry). They are regenerated on demand via:
  python .claude/tools/unity_map_extractor.py --game <slug> --project-root .projects/<folder>

If a map.txt is missing, regenerate it before querying. If a map.txt header timestamp is older than the most recent .cs mtime in the project, regenerate before trusting.


LINE FORMAT (v1 schema, locked)

Header (line 1):
  # unity-map v1 schema=<64-hex> generated=<iso8601> game=<GAMES-key-slug>

Data lines (one symbol per line, pipe-delimited tag prefixes):
  def:<name>|file:<posix-path>|line:<int>|kind:<class|struct|interface|enum|record|method>|
  signature:<oneline>|inherit:<base-or-empty>|lifecycle:<comma-list>|serialized:<comma-list>|
  call:<comma-list>|called_by:<comma-list>|scene_refs:<comma-list of path@fileID>|
  asmdef:<name>|author:<path-segment>|singleton:<true|false>|reflection:<true|false>|partial_of:<class-or-empty>

Tag prefixes are stable. Additions append new prefixes (additive-only forward compat).


STANDARD QUERIES

Definition lookup:
  rg -n "^def:<Name>\|"                                .projects/<folder>/map.txt
  rg -n "^def:<Class>\.<Method>\|"                     .projects/<folder>/map.txt

Symbol by kind:
  rg -n "\|kind:class\|.*\|inherit:MonoBehaviour"      .projects/<folder>/map.txt
  rg -n "\|kind:method\|"                              .projects/<folder>/map.txt

Neighborhood by file:
  rg -n "\|file:Assets/Scripts/_Main/PlayerScripts/"   .projects/<folder>/map.txt

Unity lifecycle cross-cut:
  rg -n "\|lifecycle:[^|]*Awake"                       .projects/<folder>/map.txt
  rg -n "\|lifecycle:[^|]*Update"                      .projects/<folder>/map.txt

Risk scans (IL2CPP / mobile):
  rg -n "\|reflection:true\|"                          .projects/<folder>/map.txt
  rg -n "\|singleton:true\|"                           .projects/<folder>/map.txt

Scene/prefab attachments:
  rg -n "\|scene_refs:[^|]*BattleArena1.unity"         .projects/<folder>/map.txt
  rg -n "\|scene_refs:[^|]*\.prefab"                   .projects/<folder>/map.txt

Author ownership (maps to teamRoster.md):
  rg -n "\|author:_Main\|"                             .projects/<folder>/map.txt
  rg -n "\|author:Stephen\|"                           .projects/<folder>/map.txt

Partial-class surface:
  rg -n "\|partial_of:<ClassName>\|"                   .projects/<folder>/map.txt


QUERY-THEN-READ PATTERN

  1. rg the map.txt for the symbol you care about.
  2. If the map row is sufficient to answer, stop there.
  3. If you need implementation detail, Read the specific file:line the map cites.
  4. NEVER Read the whole file when the map already tells you what you need.


RAG INGESTION

Both map.txt files are ingested into the local RAG under project tags:
  project=zombie-citizen (9 chunks)
  project=everlasting-odyssey (1 chunk)

For semantic symbol queries ("what handles player damage?"), prefer:
  mcp_search_context("player damage handler", project="zombie-citizen")

For exact-name lookups, prefer rg against map.txt (faster and deterministic).


LIMITATIONS (v1)

  - call / called_by columns ARE filled in v1 via second-pass regex extraction in unity_scanner.py. Resolution is unqualified-name against the in-project symbol index, so cross-module / stdlib / UnityEngine calls are dropped (deliberate, keeps signal high). If a map predates 2026-05-04 it has these columns empty — regenerate.
  - Symbol extraction is regex-based. Tree-sitter-c-sharp upgrade is optional and pluggable via ISymbolExtractor.
  - partial_of tag is emitted only when the class declaration uses the `partial` keyword explicitly.
  - Known false-positive: `?.Invoke(...)` on delegate fields trips reflection:true. If a file shows reflection:true but `rg "GetField|GetMethod|GetProperty|GetType\(\)\.Get" <file>` returns nothing, treat as false-positive. Tracked in docs/bugs/architecture.md.

If the map returns no hit for a symbol you expect, regenerate the map (it may be stale) before concluding the symbol doesn't exist.


REGENERATION (mandatory at session start)

The map MUST be regenerated at session start for the selected game, before any other read of map.txt this session. Codebase is the source of truth — a stale map produces wrong wiring discovery. session-protocol.md step 0 enforces this.

Command:
  python .claude/tools/unity_map_extractor.py --game <CURRENT_GAME>

Behavior:
  - If .projects/<folder>/Assets/Scripts/ exists: regen runs (~0.07s for ZC, <0.01s for FFT). Exit 0.
  - If project root missing (e.g. the current Unity game has no Unity project yet): exit 1. Treat as INFO ("no Unity project for current_game, skipping map regen"), continue session normally.
  - If exit 1 for any other reason: surface to user, continue session.

Additional regeneration triggers (mid-session):
  - Assets/Scripts/ tree changes by more than one file
  - New .meta file added (guid index stale)
  - New scene or prefab added under Assets/
  - asmdef files added or moved
  - After merging a feature branch into main

Regeneration is cheap. Over-regenerating is not a concern.


CODEGRAPH (C# CALL CHAINS) — COMPLEMENTARY TO map.txt, NOT A REPLACEMENT

As of 2026-06-10 a second source for C# structure is wired: the codegraph MCP (one server per game, pinned to that game's Assets/). Tools mcp__codegraph-zc__* (Zombie_Citizen) and mcp__codegraph-eo__* (Everlasting Odyssey). It tree-sitter-parses the C# into a live SQLite call-graph that a file watcher keeps current mid-session (no regen step), so for pure C# call chains it is both fresher and higher-coverage than map.txt (map.txt's call/called_by is regex second-pass and deliberately drops cross-module/UnityEngine edges; codegraph resolves in-project C# references more completely).

SPLIT OF DUTIES (use the right tool per question):
  codegraph (mcp__codegraph-<zc|eo>__*) for PURE C# structure:
    codegraph_explore  "how does X work" / "how does X reach Y" — one call returns the relevant source grouped by file + relationship map + blast radius
    codegraph_callers / codegraph_callees   walk a C# call chain
    codegraph_impact   blast radius before editing a symbol
    codegraph_search / codegraph_node        locate / fully dump a symbol
  map.txt (rg) for UNITY-SPECIFIC wiring codegraph cannot see:
    MonoBehaviour lifecycle dispatch (Awake/Start/Update/OnEnable — these are engine-invoked, no C# caller exists)
    scene_refs / prefab attachments (asset GUID edges)
    singleton / reflection risk scans, author ownership, asmdef, partial_of, SerializeField surface

WHY BOTH: codegraph has zero Unity awareness — it cannot follow engine lifecycle dispatch, asset GUID edges, prefab references, or event-bus wiring. That layer is exactly what map.txt adds. A C# method called only by Unity's lifecycle looks "uncalled" to codegraph but is live; map.txt's lifecycle column is authoritative there. Conversely, for "what actually calls this method in our code", codegraph beats map.txt. Scope: codegraph indexes <game>/Assets only (the game root carries ~8000 third-party .cs under Library/PackageCache that would bury the game graph; Assets/ excludes Library/ entirely). Index lives at Assets/.codegraph/ (example project: ignored via .gitignore; legacy project: a local-only VCS ignore entry, never committed). MCP servers load at Claude Code startup — after a fresh .mcp.json they require one restart to appear. Background: workflow/research/external-tools-integration-plan.md TIER 1.


CROSS-REFERENCE

Integration contract: workflow/memory-bank/studio/systemPatterns.md
Schema source: .claude/tools/unity_map/schema.py
CLI source: .claude/tools/unity_map_extractor.py
Plan + phase history: workflow/memory-bank/studio/plans/unity-map-file-system.md