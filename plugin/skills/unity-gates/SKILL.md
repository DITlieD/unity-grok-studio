---
name: unity-gates
description: Run the shareable Unity static gates (toban001 banned-API, symbol census, mono-wire census, pattern scan) on a changeset or project tree. Triggers when the user says "run unity gates", "toban001", "symbol census", "mono wire check", "static unity check", or before claiming DONE on Unity C# work. Off-agent — free models must not self-certify.
---

UNITY STATIC GATES (off-agent hygiene)

These scripts are the cheap fail-closed floor for Unity C#. They are regex-unsound and
necessary-not-sufficient; PlayMode/EditMode tests and the Unity compiler remain the
runtime backstop. **Never claim DONE on Unity C# without running the relevant gates.**

PACKAGE LOCATION

Gates live under the plugin root:

```
$GROK_PLUGIN_ROOT/gates/
  toban001_check.py
  unity_symbol_census.py
  mono_wire_census.py
  scan_unity_patterns.py
  unity-symbol-policy.json
  run_unity_static_gates.sh
```

If `GROK_PLUGIN_ROOT` is unset, resolve via the installed `unity-grok` plugin path
(`grok plugin details unity-grok`) or the checkout `packs/unity-grok/gates/`.

COMMANDS

```bash
# Whole tree
bash "$GATES/run_unity_static_gates.sh" --root /path/to/Assets

# Touched files only
bash "$GATES/run_unity_static_gates.sh" --files a.cs,b.cs --project /path/to/UnityProject

# Package fixture smoke
bash "$GATES/run_unity_static_gates.sh" --fixture
```

Individual:

```bash
python3 toban001_check.py --files a.cs,b.cs --json
python3 unity_symbol_census.py --files a.cs --policy unity-symbol-policy.json --json
python3 mono_wire_census.py --new-files NewMono.cs --project /path/to/Project --json
python3 scan_unity_patterns.py /path/to/dir
```

EXIT CODES

- 0 clean / nothing to judge
- 1 BLOCK findings
- 2 config error (missing file/policy) — fail-closed

WHAT THEY CATCH

| Gate | Blocks |
|------|--------|
| toban001 | GameObject.Find, FindObject(s)OfType, DateTime.Now, Thread.Sleep, .cs > 600 lines, … |
| symbol census | deny-tier symbols (FindObjectsByType, Awaitable, …) without `// UNITY-VERIFY[sym]` |
| mono_wire | new MonoBehaviour/SO not attached/referenced and without `// WIRE-DARK[id]` |
| pattern scan | hot-path allocs, LINQ in Update, deprecated patterns |

CHEAP-MODEL RULE

Free models hallucinate Unity APIs. After edits:

1. Run toban001 + symbol census on touched `.cs`
2. Run mono_wire on **new** MonoBehaviours
3. Do not hand-edit `.unity`/`.prefab`/`.asset` YAML
4. Prefer Unity MCP for scene/prefab mutations when Editor is up
