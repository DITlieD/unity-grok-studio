Unity UI Toolkit practices (HARD RULE, Unity pack, UI tasks)

Loaded by: any Unity task touching UI (UXML/USS, a UI screen, uGUI, an HUD/menu).

- UI is UI Toolkit text-first: author UXML (structure) + USS (style) as TEXT via Edit/Write, NOT by hand-editing a .uxml through binary tooling. uGUI is mutated only via a builder / unityMCP manage_ui, never hand-edited YAML.
- Responsive layout: use flex (flex-grow/flex-shrink/flex-direction) + percentage/auto sizing, not hardcoded pixel positions, so the UI survives resolution/aspect changes.
- Full state coverage for any data-bound UI surface: empty / loading / error / populated. A view that only renders the happy path is incomplete.
- The UI change is judged by the visual-ui-loop (the auditor renders the deterministic ui-diff first to pick WHERE to look, then a schema-constrained pass|fail|unknown critique with unknown=fail) + uss-taste-lint; never an executor self-pass.
- Accessibility/focus: a navigable UI declares focusable elements + a sane tab order; do not ship a mouse-only menu.
