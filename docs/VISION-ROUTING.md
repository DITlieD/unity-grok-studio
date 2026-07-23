# Vision routing

How images reach free/text-only models in unity-grok-studio.

## Overview

| Path | When | Mechanism |
|------|------|-----------|
| **A — FreeLLMAPI native vision** | Model has vision (`supportsVision` / profile) | Send `image_url` (or multimodal content) through FreeLLMAPI |
| **B — Pre-describe hook** | Model is text-only (`free-coder`, `devin-*`, …) | UserPromptSubmit hook describes image via FreeLLMAPI vision, injects text |

Bridges known to drop image parts (e.g. some Messages proxies) must use Path B or a host that supports vision natively.

## Path A — FreeLLMAPI native

1. FreeLLMAPI on `FREELLM_BASE_URL` (default `http://127.0.0.1:3001/v1`).
2. Enable ≥1 vision-capable model in the active profile.
3. Use models such as `free-auto` when the selected upstream model supports vision.
4. If no vision model is available, FreeLLMAPI may return HTTP 422 for image turns — fall back to Path B or enable a vision model.

Env:

| Variable | Default | Role |
|----------|---------|------|
| `FREELLM_BASE_URL` | `http://127.0.0.1:3001/v1` | OpenAI-compatible base |
| `FREELLM_API_KEY` | (required non-empty for FreeLLMAPI) | Auth |
| `VISION_MODEL` | `auto` | Model id for vision-check MCP / describe |

## Path B — vision-predescribe hook (text-only)

Hook: `plugin/hooks/bin/vision-predescribe.sh` (UserPromptSubmit via `plugin/hooks/hooks.json`).

When the active model id looks text-only **and** image file paths are present (attachments or absolute paths in the prompt), the hook:

1. Calls `mcp/vision-check/server.py --image <path>` (CLI mode).
2. Injects JSON with `additionalContext` containing:

```text
[vision-predescribe]
### /path/to/image.png
...description...
[/vision-predescribe]
```

### Text-only model list

Default (`UGS_TEXT_ONLY_MODELS`):

`free-coder,devin-free,devin-glm,devin-swe,kimi,glm-5,swe-1`

### Force predescribe (tests / debugging)

```bash
export UGS_FORCE_PREDESCRIBE=1
```

### Failure behaviour

If FreeLLMAPI is down, the block still appears with a graceful error line:

```text
(vision-describe failed: ...)
```

or an `error:` line from the vision server — so the agent sees that description was attempted.

## vision-check MCP

- Server: `mcp/vision-check/server.py`
- Wrapper: `mcp/wrappers/vision-check.sh` / plugin mcp-wrappers
- Tool: `vision_describe` when MCP SDK present; CLI `--image` for hooks

## img2threejs

- Skill: `plugin/skills/img2threejs/SKILL.md`
- Forge scripts: **`$UNITY_GROK_ROOT/tools/img2threejs/forge/...`** (not skill-root-relative only)
- Probe (no vision): `python $UNITY_GROK_ROOT/tools/img2threejs/forge/stage1_intake/probe_image.py <image>`
- Full self-correction loop needs **agent vision** (Path A host vision, or Path B descriptions + comparison sheets)

Do not send raw images through bridges known to drop image parts; use Path B or FreeLLMAPI vision.

## Env summary

| Variable | Purpose |
|----------|---------|
| `FREELLM_BASE_URL` | Vision + FreeLLMAPI base |
| `FREELLM_API_KEY` | Auth |
| `VISION_MODEL` | Describe model id |
| `UGS_FORCE_PREDESCRIBE` | `1` = always run predescribe when images present |
| `UGS_TEXT_ONLY_MODELS` | Comma list of model id substrings treated as text-only |
| `UNITY_GROK_ROOT` | Package root (hook + MCP resolve paths) |
| `GROK_MODEL` | Fallback model id if hook payload omits model |

## Related

- `plugin/skills/cheap-harness/SKILL.md`
- `mcp/vision-check/server.py`
- `tools/asset_gen/vision_client.py`
