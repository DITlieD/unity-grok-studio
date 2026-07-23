---
name: cheap-harness
description: Free / any-model routing via FreeLLMAPI, vision routing, and static Unity gates. Use when setting up free-auto models or verifying coworker-safe config.
---
# cheap-harness

1. Apply models: `./scripts/apply_models.sh` (from `$UNITY_GROK_ROOT`)
2. FreeLLMAPI on `:3001` OR `python tools/free_chat_shim.py`
3. Export `FREELLM_API_KEY` (any non-empty local key for FreeLLMAPI)
4. Prefer `-m free-auto` for coding; enable ≥1 vision model for image turns
5. Vision sticky-coding: use UserPromptSubmit `vision-predescribe` hook for text-only models
6. Before DONE claims: run `$UNITY_GROK_ROOT/tools/gates/run_unity_static_gates.sh`

See `docs/VISION-ROUTING.md` and `config/models.example.toml`.
