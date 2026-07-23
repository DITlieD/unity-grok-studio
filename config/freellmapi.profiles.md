# FreeLLMAPI profiles for Unity Grok Studio

## Coding profile
- Enable tool-capable models with context ≥32k
- Point Grok `free-auto` at `http://127.0.0.1:3001/v1` `chat_completions`
- Set `context_window` to the **smallest** model window in the profile

## Vision profile
- Enable ≥1 `supportsVision` model (e.g. Gemini flash free tier)
- FreeLLMAPI routes `image_url` blocks only to vision models
- If none enabled → 422 `no_vision_model`

## Sticky coding after vision
- Prefer package UserPromptSubmit hook `vision-predescribe` so the coding model stays selected
- Optional FreeLLMAPI: `FREELLMAPI_CONTEXT_HANDOFF=on_model_switch`
