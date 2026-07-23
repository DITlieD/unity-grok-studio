# Unity install + UPM wiring

## 1. Unity Editor
Install Unity Hub + a 6000.x LTS (or your project version). Large download — confirm before agent runs installers.

## 2. MCP For Unity (CoplayDev)
Install the Editor plugin so the `unity` MCP server can talk to the Editor. See CoplayDev / mcpforunity docs.

## 3. Wire unity-grok UPM packages
```bash
./scripts/wire-unity-project.sh /path/to/Project
```
Adds to `Packages/manifest.json`:
- `com.unitygrok.uitools` → ViewProbe, Placement, Anim, Vfx editors
- `com.unitygrok.agentdebug` (optional) → runtime dumps

## 4. Verify menus
After domain reload, expect Tools/UnityGrok (or equivalent) entries for View Probe and placement.

Agents may call Unity MCP `execute_menu_item` / `batch_execute` when first-class tools are unavailable.
