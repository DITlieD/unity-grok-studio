# Official Unity CLI (optional companion)

**MCP alone is enough** for the live Editor agent loop. Coplay Unity MCP (`mcpforunityserver`) remains the default bridge for scene/GO/console/tests. The official **Unity CLI** (`unity` binary) is an **optional companion** for install/open/auth and advanced pipeline eval — never required for package bootstrap or doctor overall health.

Plan / decision record: [plans/UNITY-CLI-INTEGRATION-PLAN.md](plans/UNITY-CLI-INTEGRATION-PLAN.md).

---

## Install the standalone CLI binary

This installs the **CLI tool only**, not a multi-GB Editor. Editor installs still go through Hub or `unity install <version>` with **human confirmation**.

### macOS / Linux

```bash
curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash
```

### Windows (PowerShell)

```powershell
$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex
```

### Verify

```bash
unity --version
unity --help
```

If `unity` is not found, ensure the install directory is on `PATH` (reopen the shell after install).

Via this package (opt-in):

```bash
# Print install guidance only
./scripts/install-deps.sh --with-unity-cli

# Non-interactive CLI binary install (not Editor)
./scripts/install-deps.sh --with-unity-cli --assume-yes
```

Doctor reports a non-blocking component: `./scripts/doctor.sh` → `[ok|warn|missing] unity_cli`.

---

## When to use CLI vs Coplay MCP

| Job | Prefer |
|-----|--------|
| Install / update Editor + modules | **CLI** (`unity install …`) — human confirm large downloads |
| Open project with correct Editor version | **CLI** (`unity open $UNITY_PROJECT`) when present |
| Auth / service account for CI | **CLI** |
| List installed Editors (JSON/TSV) | **CLI** |
| Wire uitools / agentdebug UPM | **Neither** — `./scripts/wire-unity-project.sh` |
| Place / adjust GameObjects, components, prefabs | **Coplay MCP** (default) |
| ViewProbe / Tools/UnityGrok menus | **Coplay MCP** (or human menu) |
| Compile errors / console after script edit | **Coplay MCP** |
| Play mode enter/exit smoke | **Coplay MCP** |
| One-off live C# inspect (no recompile) | **CLI** `unity command eval` only if pipeline is installed + connected |
| Free-model install/open without Hub folklore | **CLI** short shell when present; still **MCP** for mutations |

**Agent decision rules (short)**

1. **Bootstrap / open project** → `unity open $UNITY_PROJECT` if CLI present; else Hub + [UNITY-INSTALL.md](UNITY-INSTALL.md).
2. **Live scene / GO / console / tests** → Coplay MCP (default).
3. **One-shot inspect** → CLI eval only when pipeline is present; **fail soft** to MCP if missing.
4. **Missing CLI** → continue with Hub paths + MCP; do **not** block tasks.

Architecture:

```text
Grok
 ├─ shell tools  ──▶ optional Unity CLI (install/open/auth/eval when present)
 ├─ MCP tools    ──▶ Coplay mcpforunityserver ──▶ open Editor (DEFAULT)
 └─ UPM menus    ──▶ ViewProbe / uitools (wire-unity-project.sh)
```

CLI and Coplay MCP are **complementary**. Neither is a mandatory pipe into the other.

---

## Optional: `com.unity.pipeline`

Experimental package so the CLI can drive a **running** Editor (Unity 6.0 LTS+) or a dev Player over a local API (live C# eval, registered commands).

```bash
# Only when CLI is present and you explicitly want pipeline
unity pipeline install
# or via this package (opt-in; does not run unity if absent):
./scripts/wire-unity-project.sh /path/to/Project --with-pipeline
```

Default `./scripts/wire-unity-project.sh` still wires **only** `com.unitygrok.uitools` + `com.unitygrok.agentdebug`. Pipeline is **never** auto-added.

Example once pipeline is connected:

```bash
unity command eval "return Application.version;"
```

If pipeline or CLI is missing, use Coplay MCP instead — fail soft.

---

## Free-model ergonomics

| Prefer | Why |
|--------|-----|
| Short CLI checks (`unity --version`, `unity open $UNITY_PROJECT`) when CLI is on PATH | Avoid inventing Hub/Editor path folklore that burns context |
| Coplay MCP for rich scene ops | Shell cannot replace scene tool schemas |
| “CLI present ⇒ install/open; MCP ⇒ mutate” | Reduces dual-stack thrash |
| Do **not** dump full CLI reference into system prompts | Context size |

---

## Non-goals

| Non-goal | Why |
|----------|-----|
| Requiring CLI for package bootstrap | Breaks MCP-only coworkers |
| Replacing Coplay as default live Editor bridge | Maturity / Phase 4 gate |
| Silent multi-GB Editor downloads | User must confirm |
| Auto-installing pipeline into every project | Opt-in only |
| Making CLI the mandatory pipe into Coplay | Wrong architecture |
| Replacing ViewProbe / uitools UPM | Independent product surface |

---

## Official MCP mode (experimental — not default)

Unity positions an **MCP mode** on the official CLI stack. This package **does not** switch default MCP from Coplay until a documented spike passes reliability, free-path, and multi-instance gates. See [Phase 4 spike notes](plans/UNITY-CLI-MCP-SPIKE.md).

Until then: keep `plugin/.mcp.json` on `mcpforunityserver` (Coplay).

---

## Risks / notes

- **Experimental** CLI and pipeline APIs may change.
- Binary name `unity` is the **standalone CLI**, not the Editor executable; doctor probes `--version` / CLI-like behavior.
- Domain-reload / session friction can affect pipeline and official MCP mode — prefer Coplay for multi-step scene authoring.
- Never run `unity install <editor-version>` from agents without explicit human confirmation (multi-GB).
- LIA shell policy may need an allowlist entry if it blocks the `unity` binary; fail soft and document override.

---

## Related

| Resource | Path / URL |
|----------|------------|
| Unity CLI docs | https://docs.unity.com/en-us/unity-cli/use-unity-cli |
| Meet the Unity CLI | https://unity.com/blog/meet-the-unity-cli |
| Coplay Unity MCP | https://github.com/CoplayDev/unity-mcp |
| This package MCP defaults | `plugin/.mcp.json` |
| Unity + MCP wire | [UNITY-INSTALL.md](UNITY-INSTALL.md) |
| Doctor | `scripts/doctor.sh` |
| Install deps | `scripts/install-deps.sh` |
| Integration plan | [plans/UNITY-CLI-INTEGRATION-PLAN.md](plans/UNITY-CLI-INTEGRATION-PLAN.md) |
