---
name: install-deps
description: Install and diagnose unity-grok-studio dependencies (venv, uv, plugin, optional Blender/Unity CLI/Unity wiring).
---
# install-deps

```bash
cd $UNITY_GROK_ROOT
./scripts/doctor.sh --json
./scripts/install-deps.sh          # Bucket B auto
./scripts/install-deps.sh --with-blender   # guided; needs user OK for sudo
./scripts/install-deps.sh --with-unity-cli # print official Unity CLI install (binary only with --assume-yes)
./scripts/wire-unity-project.sh /path/to/UnityProject
# Opt-in pipeline UPM only when user asked + CLI companion desired:
# ./scripts/wire-unity-project.sh /path/to/UnityProject --with-pipeline
./scripts/doctor.sh --json
```

Doctor component `unity_cli` is optional (`ok` / `warn` / `missing`). Missing CLI does **not** fail overall doctor.

Rules for free models:
- Auto-install Bucket B (venv, uv, plugin)
- Never silent `sudo` for Blender/Unity without explicit user approval
- Never invent API keys
- Do not claim green while Unity/Blender are red/missing
- Official Unity CLI is optional; **MCP alone is enough** for live Editor work
- Prefer `unity open $UNITY_PROJECT` when CLI is on PATH; else Hub + Coplay MCP
- Never run multi-GB `unity install <editor-version>` without explicit human confirm
- See `$UNITY_GROK_ROOT/docs/UNITY-CLI.md`
