# Vision routing

## Path A — FreeLLMAPI native
Image `image_url` blocks route only to models with `supportsVision`.
Enable ≥1 vision model. If none → HTTP 422.

## Path B — Package pre-describe (companion)
Hook: `plugin/hooks/bin/vision-predescribe.sh` on UserPromptSubmit.
When model id looks text-only and image paths are present, calls `mcp/vision-check/server.py` and injects:
```
[vision-predescribe]
...description...
[/vision-predescribe]
```
Env: `FREELLM_BASE_URL`, `FREELLM_API_KEY`, `VISION_MODEL`, `UGS_FORCE_PREDESCRIBE=1`, `UGS_TEXT_ONLY_MODELS`.

## img2threejs / ViewProbe
Require vision (A or B). Do not send images through bridges known to drop image parts.
