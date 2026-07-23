---
name: install-deps
description: Install and diagnose unity-grok-studio dependencies (venv, uv, plugin, optional Blender/Unity wiring).
---
# install-deps

```bash
cd $UNITY_GROK_ROOT
./scripts/doctor.sh --json
./scripts/install-deps.sh          # Bucket B auto
./scripts/install-deps.sh --with-blender   # guided; needs user OK for sudo
./scripts/wire-unity-project.sh /path/to/UnityProject
./scripts/doctor.sh --json
```

Rules for free models:
- Auto-install Bucket B (venv, uv, plugin)
- Never silent `sudo` for Blender/Unity without explicit user approval
- Never invent API keys
- Do not claim green while Unity/Blender are red/missing
