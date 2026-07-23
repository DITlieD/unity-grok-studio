---
name: cheap-harness
description: Free / any-model routing via FreeLLMAPI and Devin bridge, vision routing, and static Unity gates. Use when setting up free-auto or devin-* models or verifying coworker-safe config.
---
# cheap-harness

Two free-model paths (no paid xAI/Claude required as default):

## Path 1 — FreeLLMAPI (`free-auto`, `free-coder`)

1. Apply models: `./scripts/apply_models.sh` (from `$UNITY_GROK_ROOT`)
2. FreeLLMAPI on `:3001` OR `python tools/free_chat_shim.py`
3. Export `FREELLM_API_KEY` (any non-empty local key for FreeLLMAPI)
4. Prefer `-m free-auto` for coding; enable ≥1 vision model for image turns
5. `api_backend = "chat_completions"`, base `http://127.0.0.1:3001/v1`

## Path 2 — Devin free models (`devin-free`, `devin-glm`, `devin-swe`)

1. Install Devin Desktop, log in once (creates `credentials.toml`)
2. Install bridge deps: `./scripts/install-deps.sh --with-devin-bridge`
3. Start bridge: `./tools/devin-bridge/run.sh` → `http://127.0.0.1:8810`
4. Models use `api_backend = "messages"` and base `http://127.0.0.1:8810/v1`
5. Select: `grok -m devin-free` (kimi-k2-7), `-m devin-glm` (glm-5-2), `-m devin-swe` (swe-1-6)
6. Keep `DEVIN_TOOL_DESC=generic` on the bridge to survive gateway content filters

## Vision for text-only free models

- UserPromptSubmit hook `vision-predescribe` injects `[vision-predescribe]...` for text-only ids
- Text-only list includes `free-coder`, `devin-free`, `devin-glm`, `devin-swe`, etc.
- Requires FreeLLMAPI vision endpoint for the describe call (see `docs/VISION-ROUTING.md`)

## Gates

Before DONE claims: run `$UNITY_GROK_ROOT/tools/gates/run_unity_static_gates.sh`

See `docs/VISION-ROUTING.md`, `docs/DEVIN-BRIDGE.md`, and `config/models.example.toml`.
