# Phase 4 spike notes: official Unity CLI MCP mode vs Coplay

| Field | Value |
|-------|--------|
| **Status** | **SPIKE REPORT — Coplay remains default** |
| **Date** | 2026-07-24 |
| **Related plan** | [UNITY-CLI-INTEGRATION-PLAN.md](UNITY-CLI-INTEGRATION-PLAN.md) |

## Scope of this report

Compare official CLI MCP mode vs Coplay (`mcpforunityserver`) on the plan’s matrix. A full side-by-side run requires a live Unity Editor, both stacks installed, and interactive sessions. **This environment did not exercise a live Editor + official MCP mode.** Outcome therefore defaults to the plan’s decision gate failure path: **keep Coplay as default**.

## Comparison matrix (planned observations)

| Task | Coplay (baseline in product) | Official CLI MCP mode | This environment |
|------|------------------------------|------------------------|------------------|
| Place a cube / basic GO | Primary path via MCP tools; mature | Not measured | Not run |
| Read console after intentional compile error | `read_console` after domain reload — product rules assume this works | Not measured | Not run |
| Survive domain reload / play mode | Session assumed stable enough for coworker loop | Field reports of token/session friction | Not run |
| Multi-Editor / instance selection | `set_active_instance` / Name@hash routing | Not measured | Not run |
| Cost / license free for baseline coworker | Yes (OSS + uvx wheel) | Unknown without Unity license/AI product check | Assumed not proven free |

## Decision gate (from integration plan)

Switch default MCP **only if all** hold:

1. Equal or better reliability on spike matrix.
2. Free for baseline coworker path (no paid Unity AI subscription required).
3. Multi-editor / multi-instance behavior acceptable.
4. Documented fallback: keep Coplay install path.

**Result:** Gate **not met** (spike could not run live). **Default remains Coplay** (`plugin/.mcp.json` → `mcpforunityserver`).

## Product defaults after this spike note

- `plugin/.mcp.json` unchanged: Coplay `mcpforunityserver==10.1.0`.
- Official CLI MCP mode: experimental alternate only; document in [UNITY-CLI.md](../UNITY-CLI.md); do not flip defaults.
- Re-run this spike on a machine with Unity Editor + CLI MCP mode before any future default change; record results in a new dated section or superseding report.

## How to re-run the spike (when Editor is available)

1. Install CLI + Coplay as today; open the same project in one Editor.
2. For each matrix row, time and note failures on Coplay, then on official MCP mode (same tasks).
3. Force domain reload (script touch) and play mode enter/exit; check session survival.
4. If multi-instance: open two Editors; verify routing.
5. Confirm no paid Unity AI subscription is required for the official path.
6. Only if all gates pass **and** maintainers explicitly approve: open a separate PR to change `.mcp.json` with a documented fallback.
