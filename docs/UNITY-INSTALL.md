# Unity install + UPM wiring

**Assumption:** Unity Hub + an Editor matching your project version are already present (or you will install them yourself — large download; confirm before any agent runs installers).

This package focuses on **MCP For Unity** + **wiring UPM packages**, not full Editor setup.

**Companion:** optional official [Unity CLI](UNITY-CLI.md) for install/open/auth. **MCP alone is enough** for the live Editor agent loop; CLI is never required.

## 1. Unity Editor (assumed)

- Install Unity Hub + your project’s Editor version (e.g. 6000.x LTS).
- Open the project once so Library/ and package resolution settle.

## 2. MCP For Unity (CoplayDev)

Install the Editor-side **MCP For Unity** package so the `unity` MCP server (`uvx mcpforunityserver`) can talk to the open Editor.

- Follow CoplayDev / mcpforunity docs for the current UPM / install path.
- Keep the Editor running with the MCP bridge connected when agents need live scene tools.
- Multiple Unity instances: set the active instance in the MCP client before mutating.

Grok plugin defaults typically include:

```toml
[mcp_servers.unity]
command = "uvx"
args = ["--from", "mcpforunityserver==10.1.0", "mcp-for-unity"]
enabled = true
```

(`uv`/`uvx` required — see [DEPENDENCIES.md](DEPENDENCIES.md).)

## 3. Wire unity-grok UPM packages

```bash
export UNITY_GROK_ROOT=/path/to/unity-grok-studio
./scripts/wire-unity-project.sh /path/to/Project
# Opt-in only (does not replace Coplay MCP):
# ./scripts/wire-unity-project.sh /path/to/Project --with-pipeline
```

Adds to `Packages/manifest.json` (file: URLs into this repo):

- `com.unitygrok.uitools` → ViewProbe, Placement, Anim, Vfx editors
- `com.unitygrok.agentdebug` (optional) → runtime dumps / log bridge

Default wiring does **not** add `com.unity.pipeline`. Use `--with-pipeline` only when the official CLI is present and you want pipeline eval; see [UNITY-CLI.md](UNITY-CLI.md).

## 4. Verify menus

After domain reload, expect **Tools / UnityGrok** (or equivalent) entries for View Probe and placement.

Agents may call Unity MCP `execute_menu_item` / `batch_execute` when first-class tools are unavailable.

## 5. Working with the agent

- Prefer Resources for read-only editor state; Tools for mutations.
- After script edits: `read_console` for compile errors.
- Before DONE claims on C#: `$UNITY_GROK_ROOT/tools/gates/run_unity_static_gates.sh`
