# Unity MAP-file usage (LLM instructions)

Loaded when the task involves reading/understanding game code, locating a symbol,
tracing callers, finding scene/prefab references, or scouting a file's neighborhood.
The MAP is a token-efficient alternative to Read/Grep across many .cs files.

## When to use the map
Use `map.txt` BEFORE reading any .cs file for:
- "where is X defined" / "what file is X in"
- "what calls X" / "what does X call"
- "what's in this scene/prefab" / "which MonoBehaviour is attached"
- lifecycle / SerializeField / singleton / reflection scans

Prefer one `rg` against map.txt over multiple Read/Grep across Assets/Scripts/.

## Where the map lives (standalone)
Generate **per Unity project**, next to that project's Assets (or under a tools cache):

```
$UNITY_PROJECT/map.txt
# or
$UNITY_PROJECT/Tools/map.txt
```

Optional extractor (if present in the host environment):
```bash
python3 tools/unity_map_extractor.py --project-root "$UNITY_PROJECT" --out "$UNITY_PROJECT/map.txt"
```

If no extractor is installed, agents may fall back to targeted Grep/Read of `Assets/**/*.cs`.
Do **not** assume a monorepo `$UNITY_PROJECT/<Game>/map.txt` layout.

Maps are typically gitignored and regenerated on demand. If a map header timestamp is older
than the most recent .cs mtime, regenerate before trusting.

## Line format (v1 schema)
Header (line 1):
```
# unity-map v1 schema=<64-hex> generated=<iso8601> game=<slug>
```

Data lines (one symbol per line, pipe-delimited tag prefixes):
```
def:<name>|file:<posix-path>|line:<int>|kind:<class|struct|interface|enum|record|method>|
signature:<oneline>|inherit:<base-or-empty>|lifecycle:<comma-list>|serialized:<comma-list>|
call:<comma-list>|called_by:<comma-list>|scene_refs:<comma-list of path@fileID>|
asmdef:<name>|author:<path-segment>|singleton:<true|false>|reflection:<true|false>|partial_of:<class-or-empty>
```

## Standard queries (against `$UNITY_PROJECT/map.txt`)
```bash
MAP=$UNITY_PROJECT/map.txt
rg -n "^def:<Name>\|"                                "$MAP"
rg -n "^def:<Class>\.<Method>\|"                     "$MAP"
rg -n "\|kind:class\|.*\|inherit:MonoBehaviour"      "$MAP"
rg -n "\|lifecycle:[^|]*Awake"                       "$MAP"
rg -n "\|reflection:true\|"                          "$MAP"
rg -n "\|singleton:true\|"                           "$MAP"
rg -n "\|scene_refs:[^|]*\.prefab"                   "$MAP"
```

## Optional live codegraph
Some environments run a tree-sitter codegraph MCP pinned to a project's Assets/. Prefer
map.txt for offline/deterministic symbol lookup; use codegraph when wired for live call chains.
This package does **not** ship per-game codegraph servers.

## Limits
- map.txt call/called_by is often a regex second-pass and may drop cross-module/UnityEngine edges
- always verify critical writes against the live .cs source before editing
