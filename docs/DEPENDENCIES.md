# Dependencies matrix

| Bucket | What | How |
|--------|------|-----|
| A In git | blender-gen, sfx/ardy CLIs, gates, skills, img2threejs, UPM packages | clone |
| B Package managers | uv/uvx, venv Python deps, grok plugin, mcpforunityserver wheel | bootstrap / install-deps |
| C Host apps | Unity Editor, Blender 5.x, FreeLLMAPI, optional Meshy/Freesound keys | guided; user approval for sudo |

Agent auto-install: Bucket B yes. Bucket C only after explicit user confirmation.
Never invent API keys. Never silent multi-GB Unity downloads.
