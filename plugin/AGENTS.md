# Unity Grok Studio — agent instructions

## Roots
- `UNITY_GROK_ROOT` — package repo root (set by bootstrap)
- `GROK_PLUGIN_ROOT` — this plugin directory
- `SFX_LIB` — default `$UNITY_GROK_ROOT/sfx_library`
- `UNITY_PROJECT` — optional path to open Unity project

Never hardcode absolute owner machine paths. Prefer env + relative paths.

## Honest limits
1. Free LLMs cannot invent a Unity license or replace Unity Hub for first install.
2. Do not `sudo` without explicit user approval.
3. blender-gen without Blender → fail soft + install hint.
4. Unity MCP without Editor → server may start; Editor tools unavailable until connected.
5. img2threejs / ViewProbe image workflows need vision (FreeLLMAPI vision model or pre-describe hook).

## Before DONE
Run static gates on touched C#: `$UNITY_GROK_ROOT/tools/gates/run_unity_static_gates.sh`
Run `./scripts/doctor.sh` when environment health is uncertain.
