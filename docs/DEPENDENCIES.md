# Dependencies matrix

| Bucket | What | How |
|--------|------|-----|
| A In git | blender-gen, sfx/ardy CLIs, gates, skills, img2threejs, UPM packages, **devin-bridge source** | clone |
| B Package managers | uv/uvx, venv Python deps, grok plugin, mcpforunityserver wheel, bridge `requirements.txt` | bootstrap / install-deps |
| C Host apps | Unity Editor, **Blender 5.x**, FreeLLMAPI, **Devin Desktop**, optional Meshy/Freesound keys | guided; user approval for sudo |

Agent auto-install: Bucket B yes. Bucket C only after explicit user confirmation.
Never invent API keys. Never silent multi-GB Unity downloads.

## Host apps detail

### Blender 5.x (optional — materials / meshes)

| OS | Install |
|----|---------|
| Linux | `sudo snap install blender --classic` **or** download from https://www.blender.org/download/ |
| macOS | `brew install --cask blender` |
| Windows | `winget install BlenderFoundation.Blender` or blender.org installer |

Env: `BLENDER_BIN` if not on `PATH`. Doctor component: `blender`.

### Devin Desktop (optional — free Devin models)

1. Install Devin Desktop from Cognition (own account).
2. Log in once → `credentials.toml`.
3. `./scripts/install-deps.sh --with-devin-bridge` (Python deps only).
4. `./tools/devin-bridge/run.sh` → `:8810`.

Doctor components: `devin_bridge`, `devin_credentials`.

### FreeLLMAPI (optional — free-auto / vision)

- Listen on `http://127.0.0.1:3001/v1`
- Env: `FREELLM_API_KEY`, optional `FREELLM_BASE_URL`, `VISION_MODEL`
- Doctor component: `freellmapi`

### Unity Editor

- Install via Unity Hub (large download — confirm first).
- MCP For Unity (CoplayDev) required for live Editor MCP.
- See [UNITY-INSTALL.md](UNITY-INSTALL.md).

## Script entry points

| Script | Role |
|--------|------|
| `scripts/bootstrap.sh` | venv, core pip, chmod, apply_models mention |
| `scripts/install-deps.sh` | bootstrap + uv; `--with-blender`; `--with-devin-bridge` |
| `scripts/doctor.sh` | component matrix (`--json` supported) |
| `scripts/apply_models.sh` | merge free model stanzas into Grok config |
| `tools/devin-bridge/run.sh` | start Messages proxy |
