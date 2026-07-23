# Plan: Optional Unity CLI integration for unity-grok-studio

| Field | Value |
|-------|--------|
| **Status** | **PLAN ONLY — not implemented** |
| **Authored** | 2026-07-24 |
| **Author** | DITlieD |
| **Related product** | [DITlieD/unity-grok-studio](https://github.com/DITlieD/unity-grok-studio) |
| **Scope of this doc** | Architecture, phases, acceptance criteria — **no code changes required to adopt this plan** |

This document is a decision record and implementation roadmap. It must **not** be read as shipping Unity CLI as a required dependency. Coplay Unity MCP remains the default live-Editor path until a later phase explicitly re-evaluates that default.

---

## Motivation

Unity has announced an official **Unity CLI** (experimental standalone `unity` binary) plus the experimental **`com.unity.pipeline`** package for driving a running Editor (or dev Player) over a local API, including live C# evaluation and agent-oriented automation. Unity also states an **MCP mode** on the official stack as a transition path for agent setups.

Today, **unity-grok-studio** uses **Coplay Unity MCP** (`mcpforunityserver` / MCP For Unity) as the live Editor tool surface. That path is already wired in `plugin/.mcp.json`, documented in `docs/UNITY-INSTALL.md`, and reinforced by plugin rules and the unity-toolkit skill.

**Goal:** improve Grok coworker setup and agent ergonomics by documenting and optionally detecting the official CLI — **without forcing CLI**, without silent multi-GB Editor installs, and without replacing Coplay MCP as the default Editor bridge.

**Non-goal of motivation:** “Grok must go through Unity CLI to talk to the Editor.” Shell tools and MCP tools are parallel surfaces. CLI and Coplay MCP are complementary.

---

## Landscape (accurate as of mid-2026 research)

### 1. Official Unity CLI (`unity` binary)

Unity ships an experimental **standalone** CLI binary named `unity` (not the Editor executable path). It is designed for terminal-first, CI, and agent workflows.

**What it does well**

| Capability | Examples |
|------------|----------|
| Install / manage Editors | `unity install lts`, `unity install 6000.x.yf1` |
| Modules | `unity install-modules -e <version> -m android ios` |
| List installs | `unity editors`, `unity editors --format json` |
| Open projects | `unity open ./MyProject` (or `unity ./MyProject`) |
| Auth | `unity auth login`, `unity auth status`; service-account env for headless CI |
| Structured output | JSON / TSV formats; clear exit codes (0 / 1 / 130) |
| Self-update | `unity upgrade` |
| Environment diagnostics | `unity doctor` (Unity’s own) |

**Install (docs.unity.com/unity-cli)**

```bash
# macOS or Linux (beta channel as of docs mid-2026)
curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash

# Windows (PowerShell)
$env:UNITY_CLI_CHANNEL='beta'; irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex
```

Verify:

```bash
unity --version
unity --help
```

If `unity` is not found after install, the install directory may need to be on `PATH`, or the shell reopened.

**Notes for this package**

- CLI is **self-contained** and can exist on machines without Unity Hub UI (CI workers).
- Editor installs remain **large** and must never be silent from our scripts.
- Binary name `unity` can collide with mental models of the Editor binary / Hub paths; detection must distinguish **CLI** vs **Editor** (see Risks).

Primary docs: [Use the Unity CLI](https://docs.unity.com/en-us/unity-cli/use-unity-cli), [Meet the Unity CLI](https://unity.com/blog/meet-the-unity-cli).

### 2. `com.unity.pipeline`

The experimental **Unity Pipeline** package (`com.unity.pipeline`) adds a **local API** so the CLI can drive a **running** Editor (Unity **6.0 LTS+**) or, optionally, a **development Player** runtime.

**Highlights**

| Feature | Behavior |
|---------|----------|
| Install into project | `unity pipeline install` (when CLI present) |
| Discover commands | `unity command` (no args) — Editor self-describes exposed ops |
| Run registered command | `unity command <name> ...` |
| Custom project commands | Static methods with `[CliCommand]` / `[CliArg]` |
| Live C# without domain-reload cycle | `unity command eval "return Application.version;"` (Roslyn on main thread) |
| File eval | `unity command eval_file path/to/script.cs` |
| Player runtime (optional) | `unity command --runtime <player>` — localhost, off by default; not for production |

Pipeline is the layer that makes “agent opens project → inspects live state → mutates → verifies” plausible without human console relay. It is **experimental** and expected to evolve.

Pipeline is **orthogonal** to Coplay MCP: different product, different wire format, overlapping *intent* (drive the Editor).

### 3. CLI MCP mode (Unity-stated)

Unity positions an **MCP mode** on the official CLI stack so existing MCP-based agents can adopt the new surface without a full rewrite. Unity discussions and field blogs describe this as a recommended direction for **new** agent setups, while stating that existing Unity MCP setups remain supported.

**Caveats for our product**

- Mode is **experimental**.
- Field reports (blogs / community) mention friction such as **domain-reload / token** issues when the Editor reloads assemblies after script changes or play-mode transitions.
- Tool quality and stability relative to Coplay **must not be assumed** — that comparison is Phase 4.

Until a spike passes, unity-grok-studio **does not** switch default MCP from Coplay to official CLI MCP mode.

### 4. Coplay Unity MCP (what we ship)

**CoplayDev/unity-mcp** (MCP For Unity Editor package + `mcpforunityserver` on PyPI) is the mature OSS Editor tool surface already integrated:

| Artifact | Role |
|----------|------|
| `plugin/.mcp.json` | `uvx --from mcpforunityserver==10.1.0 mcp-for-unity` |
| `docs/UNITY-INSTALL.md` | Install / wire guidance |
| Plugin rules (`unity-mcp-usage`, executor/auditor profiles) | Hard rules for mutation via MCP, no hand-YAML |
| Skills (`unity-toolkit`, `unity-scaffold`, `unity-gates`) | Menus, placement, gates — assume MCP for live Editor ops |

Coplay is a **different product** from official CLI + pipeline. It provides a rich, stable tool catalog (scene/GO/components/prefabs/console/tests/instances, etc.) that Grok already depends on in rulebooks.

### Wrong vs right architecture

```text
WRONG (do not design toward this as mandatory):
  Grok ──must──▶ Unity CLI ──must──▶ Coplay MCP ──▶ Editor

RIGHT (target model):
  Grok
   ├─ shell tools  ──▶ optional Unity CLI (install/open/auth/eval when present)
   ├─ MCP tools    ──▶ Coplay mcpforunityserver ──▶ open Editor (DEFAULT)
   └─ UPM menus    ──▶ ViewProbe / uitools (wire-unity-project.sh)
```

CLI and Coplay MCP are **complementary surfaces**. Agents may use both in one session. Neither is a mandatory pipe into the other.

---

## Best-fit usage matrix for unity-grok-studio

Prefer the surface that is simplest and most reliable for the job. “Either” means both work; pick by what is already running. “Neither” means this package’s other tools or human/Hub steps.

| Job | Prefer CLI | Prefer Coplay MCP | Either | Neither |
|-----|:----------:|:-----------------:|:------:|:-------:|
| Install / update Editor + modules | ✓ | | | |
| Open project with correct Editor version | ✓ | | | |
| Auth / service account for CI | ✓ | | | |
| Structured list of installed Editors (JSON/TSV) | ✓ | | | |
| Wire UPM packages into project (`manifest.json`) | | | | ✓ `wire-unity-project.sh` |
| Place / adjust GameObjects, components, prefabs | | ✓ | | |
| ViewProbe / Tools/UnityGrok menus | | ✓ (menu execute) | | or human menu |
| Read compile errors / console after script edit | | ✓ | | |
| Play mode enter/exit smoke | | ✓ | | CLI eval if pipeline up |
| Live one-off C# query (inspect state, no recompile) | ✓ (eval + pipeline) | | possible via custom tools | |
| Discover custom project `[CliCommand]` ops | ✓ | | | |
| CI headless install + open + batch automation | ✓ | limited | | batchmode Editor flags still exist |
| Free-model context size (avoid huge MCP tool schemas) | ✓ for install/open | needed for rich scene ops | | |
| Coworker Windows / Linux / macOS Editor loop | | ✓ default | CLI companion when installed | |
| Replace ViewProbe / uitools UPM | | | | ✓ out of scope |
| Domain-reload-heavy multi-step scene authoring | | ✓ (mature surface) | | avoid sole reliance on fragile MCP mode |

**Reading the table for agents**

1. **Bootstrap machine / project path** → CLI if present; else Hub + docs/UNITY-INSTALL.md.
2. **Live scene / GO / console / tests** → Coplay MCP (default).
3. **One-shot inspect with pipeline installed** → CLI `unity command eval` is attractive; fail soft to MCP if missing.
4. **Free models** → short shell sequences (`unity --version`, `unity open $UNITY_PROJECT`) before inventing Hub paths; still use MCP for mutations.

---

## Recommended integration strategy (phased, optional)

All phases are **optional** from the user’s perspective. Implementation order is risk-ordered. **Do not skip Phase 0 documentation before wiring detection into doctor.**

### Phase 0 — Docs only (low risk)

**Deliverable:** coworker-facing guide `docs/UNITY-CLI.md` (not yet written; this plan authorizes it).

**Contents (future doc)**

- How to install official CLI (`UNITY_CLI_CHANNEL=beta` curl / PowerShell).
- When to use CLI vs Coplay MCP (matrix summary).
- Explicit **non-goals**: MCP alone is enough for the Editor agent loop; CLI not required for package bootstrap.
- Link pipeline install only as optional advanced path (`unity pipeline install`).
- Warnings: experimental, multi-GB installs need human confirm, never silent Editor download from our scripts.

**Links**

| From | To |
|------|----|
| README Docs section | UNITY-CLI.md (when written) + this plan |
| SETUP.md | optional CLI subsection |
| DEPENDENCIES.md | Bucket optional / companion |
| UNITY-INSTALL.md | “Companion: official CLI” pointer |

**Exit criteria:** a coworker can install CLI from docs without reading this plan; a coworker who ignores CLI still succeeds with MCP-only path.

### Phase 1 — Detection (non-blocking)

**Doctor component `unity_cli`**

| Status | Meaning |
|--------|---------|
| `ok` | `unity` on PATH and behaves like CLI (`unity --version` succeeds; optional check that it is not only an Editor binary mis-named) |
| `warn` or `missing` | Not installed or not on PATH |
| **Never** | Fail overall doctor `ok` solely because CLI is missing |

Today `scripts/doctor.sh` sets top-level `ok` from **python** only. Any `unity_cli` component must follow the **lia / blender** pattern: optional component, warn/missing allowed, fix string prints install hint only.

**install-deps.sh**

- Add opt-in flag: `--with-unity-cli`.
- Default behavior: **print** the official install command; do **not** pipe curl to bash unless user also passed something equivalent to `--assume-yes` **and** explicitly opted into `--with-unity-cli`.
- Never run `unity install <editor>` from install-deps (multi-GB). Document that Editor install is a separate human-confirmed step.

**Exit criteria:** `./scripts/doctor.sh` shows `[ok|warn|missing] unity_cli` without breaking existing tests that assert overall health; CI/coworker without CLI still green on required components.

### Phase 2 — Skills (agent guidance)

Update or extend agent-facing guidance (skill sections and/or AGENTS.md):

| Guidance | Rule |
|----------|------|
| Open project | Prefer `unity open $UNITY_PROJECT` when CLI present |
| Scene / GO / menus | Prefer Coplay MCP |
| One-off inspect | Prefer CLI eval when pipeline package present and connected |
| Missing CLI | **Fail soft** — continue with Hub paths + MCP; do not block tasks |
| AGENTS.md | State CLI is optional companion; never required for DONE |

Likely touch points (implementation later): `plugin/skills/install-deps/SKILL.md`, `plugin/skills/unity-toolkit/SKILL.md`, `plugin/AGENTS.md`. Do not bloat free-model prompts with full CLI reference — short decision rules only.

**Exit criteria:** agent traces show soft degradation when CLI absent; no hard requirement in rulebook language.

### Phase 3 — Project wiring helpers

- Optional helper script or flag: ensure `com.unity.pipeline` in the Unity project **only if** CLI is present **and** user asked (e.g. `wire-pipeline.sh` or `wire-unity-project.sh --with-pipeline`).
- **Keep** `wire-unity-project.sh` focused on **uitools / agentdebug** UPM (ViewProbe, placement, etc.).
- Do **not** remove Coplay MCP from `plugin/.mcp.json` defaults.
- Do **not** auto-add pipeline to every wired project.

**Exit criteria:** pipeline remains opt-in; uitools wiring unchanged for default path.

### Phase 4 — Evaluate official MCP mode

**Spike only** (spike branch or time-boxed experiment, not silent default flip).

Compare official CLI MCP mode vs Coplay on the **same tasks**, same machine, same project:

| Task | Observe |
|------|---------|
| Place a cube / basic GO | Reliability, latency, error clarity |
| Read console after intentional compile error | Correctness after domain reload |
| Survive domain reload / play mode | Token/session survival |
| Multi-Editor / instance selection | Routing quality |
| Cost / license | Free for baseline coworker path? |

**Decision gate — switch default MCP only if all hold:**

1. Equal or better reliability on spike matrix.
2. Free for baseline coworker path (no paid Unity AI subscription required).
3. Multi-editor / multi-instance behavior acceptable for our users.
4. Documented fallback: keep Coplay install path forever or until clear deprecation evidence from Unity + Coplay.

**Default if gate fails:** keep Coplay as default; document CLI MCP as experimental alternate.

### Phase 5 — Free-model ergonomics

| Idea | Rationale |
|------|-----------|
| Prefer short CLI doctor/open shell before inventing Hub paths | Free models burn context on wrong install folklore |
| Keep MCP for rich Editor ops unless CLI MCP mode wins Phase 4 | Shell cannot replace scene tool schemas overnight |
| Document “CLI present ⇒ use for install/open; MCP for mutate” | Reduces dual-stack confusion |
| Avoid dumping full Unity CLI reference into system prompts | Context size |

---

## Non-goals

| Non-goal | Why |
|----------|-----|
| Requiring Unity CLI for package bootstrap | Breaks MCP-only coworkers; multi-GB / experimental |
| Replacing ViewProbe / uitools UPM | First-class product surface independent of CLI |
| Forking Grok | Out of scope; use plugins/skills/docs only |
| Silent Editor downloads | User must confirm large installs |
| Tearing out Coplay without evidence | Phase 4 gate; maturity / field issues on official MCP mode |
| Depending on paid Unity AI subscription for baseline coworker path | FreeLLMAPI / free models / Coplay OSS remain baseline |
| Making CLI the mandatory pipe into Coplay | Wrong architecture |
| Auto-installing pipeline into every project | Opt-in only |

---

## Acceptance criteria for later implementation

Minimum bar before calling Phases 0–2 “done.” Phases 3–5 are stretch and have their own gates.

### Phase 0 checklist

- [ ] `docs/UNITY-CLI.md` exists with install, when-to-use matrix summary, non-goals.
- [ ] README / SETUP / DEPENDENCIES / UNITY-INSTALL link the guide (and optionally this plan).
- [ ] Explicit sentence: **MCP alone is enough** for the live Editor agent loop.
- [ ] No script change that requires CLI to bootstrap the plugin.

### Phase 1 checklist

- [ ] `doctor.sh` reports component `unity_cli` with `ok` / `warn` / `missing`.
- [ ] Missing CLI does **not** flip top-level doctor failure for an otherwise healthy machine.
- [ ] `install-deps.sh --with-unity-cli` documents/prints install; non-interactive run only with explicit assume-yes + opt-in.
- [ ] No path silently runs `unity install <editor-version>`.
- [ ] Existing tests (`tests/test_doctor.py`, package structure) updated only as needed; default CI without CLI still passes.

### Phase 2 checklist

- [ ] Skill or AGENTS guidance: open via CLI when present; scene ops via Coplay MCP; fail soft if CLI missing.
- [ ] No rulebook HARD RULE that CLI must be installed.
- [ ] unity-toolkit still documents Coplay + uitools as primary live loop.

### Phase 3+ (later)

- [ ] Pipeline wiring is opt-in and documented.
- [ ] Phase 4 spike report written before any default MCP change.
- [ ] Phase 5 free-model notes reflected in SETUP or UNITY-CLI.md.

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Experimental CLI / pipeline APIs change under us | High | Docs-first; pin nothing as required; re-verify before Phase 4 default flip |
| Binary name clash: `unity` CLI vs Editor binary / Hub paths | Medium | Doctor checks `--version` / help text; docs clarify “standalone CLI binary” |
| Pipeline security token / session after play mode or domain reload | Medium | Fail soft to Coplay MCP; document re-auth; Phase 4 measures survival |
| Coworker confusion: dual stacks (CLI + Coplay + uitools) | Medium | Clear matrix; “MCP enough”; optional CLI only |
| LIA shell gating blocks `unity` commands | Medium | LIA allowlist / trust notes if shell policy rejects new binary; document coworker override |
| Accidental multi-GB Editor install via agent | High | Never auto-run install Editors; require human confirm; install-deps only prints or opt-in CLI binary install |
| Official MCP mode weaker than Coplay for scene authoring | Medium | Keep Coplay default until Phase 4 |
| Free models thrash between Hub, Editor path, and CLI | Medium | Short prefer-CLI-if-present rules; doctor component |

---

## Decision defaults

If an implementer is unspecified or a PR is ambiguous:

1. **MCP Coplay remains the default live Editor bridge** (`plugin/.mcp.json` unchanged in intent).
2. **CLI is an opt-in documented companion** (detection + docs + soft skill guidance).
3. **No default MCP change** until Phase 4 spike **passes** the decision gate and is explicitly approved.
4. **Missing CLI is never a hard failure** for doctor overall health or package bootstrap.
5. **uitools / ViewProbe UPM** remains independent of CLI and pipeline.

---

## Related links

| Resource | URL / path |
|----------|------------|
| Unity CLI usage docs | https://docs.unity.com/en-us/unity-cli/use-unity-cli |
| Meet the Unity CLI (blog) | https://unity.com/blog/meet-the-unity-cli |
| Coplay Unity MCP | https://github.com/CoplayDev/unity-mcp |
| Plugin MCP defaults | `plugin/.mcp.json` |
| Unity install / MCP wire | `docs/UNITY-INSTALL.md` |
| Doctor | `scripts/doctor.sh` |
| Dep install | `scripts/install-deps.sh` |
| Project UPM wire | `scripts/wire-unity-project.sh` |
| This plan | `docs/plans/UNITY-CLI-INTEGRATION-PLAN.md` |

---

## How another session executes

Prefer smallest useful slice first.

### Suggested `/goal` (Phase 0 only)

```text
/goal Implement Phase 0 only from docs/plans/UNITY-CLI-INTEGRATION-PLAN.md:
write docs/UNITY-CLI.md (install, CLI vs Coplay matrix, non-goals: MCP alone enough),
link from README + SETUP + DEPENDENCIES + UNITY-INSTALL.
Do NOT change doctor.sh or install-deps.sh yet.
Do NOT require Unity CLI. Do NOT remove Coplay MCP.
```

### Suggested `/goal` (Phase 1 after Phase 0)

```text
/goal Implement Phase 1 from docs/plans/UNITY-CLI-INTEGRATION-PLAN.md:
add non-blocking doctor component unity_cli; optional install-deps --with-unity-cli
that prints official install (run only with explicit opt-in + assume-yes).
Never silent Editor install. Missing CLI must not fail doctor overall ok.
Update tests if needed. Keep Coplay MCP default.
```

### One-liner for implementers

**Docs first, detect second, guide agents third, never force CLI, never rip Coplay without a Phase 4 spike.**
