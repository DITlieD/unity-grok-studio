# unity-grok-studio

Standalone **Grok Build plugin** + vendored MCP servers + CLI tools + optional Unity UPM packages for Unity game work — **zero dependency on any private monorepo or owner machine**.

---

## 1. What you need

| Required / optional | What |
|---------------------|------|
| **Assumed present** | A Unity project + Unity Editor (Hub install) |
| **Required** | Grok CLI (`grok`), Python 3.10+, `uv`/`uvx` |
| **Optional free coding** | FreeLLMAPI on `:3001` → models `free-auto` / `free-coder` |
| **Optional free Devin models** | Devin Desktop (own account) + `./tools/devin-bridge/run.sh` → `devin-free` / `devin-glm` / `devin-swe` |
| **Optional materials/meshes** | Blender 5.x on `PATH` (or `BLENDER_BIN`) for blender-gen |
| **Optional recommended GATE** | [LIA Trust ≥ 0.3.0](docs/LIA-TRUST.md) for PreToolUse tool trust (v0.2.x broken) |
| **Optional** | MCP For Unity (CoplayDev) so the `unity` MCP can drive the Editor |

---

## 2. 10-minute install

```bash
git clone <this-repo> unity-grok-studio
cd unity-grok-studio
./scripts/bootstrap.sh
export UNITY_GROK_ROOT="$(pwd)"
export FREELLM_API_KEY=freellmapi-local   # if using FreeLLMAPI
./scripts/apply_models.sh                # merges config/models.example.toml → ~/.grok/config.toml
grok plugin install "$(pwd)/plugin" --trust
grok plugin enable unity-grok-studio
./scripts/doctor.sh
```

For a fuller dependency pass (uv + optional Blender/bridge):

```bash
./scripts/install-deps.sh                 # core
./scripts/install-deps.sh --with-blender --assume-yes   # optional Blender
./scripts/install-deps.sh --with-devin-bridge           # bridge venv only; does not start without login
./scripts/install-deps.sh --with-lia                    # optional LIA Trust ≥ 0.3.0
```

### Optional: LIA Trust ≥ 0.3.0

Recommended for PreToolUse GATE mediation. **Do not use v0.2.x** (broken for multi-harness/Grok). Plugin fail-opens if LIA is missing.

```bash
curl -fsSL https://raw.githubusercontent.com/DITlieD/lia-trust/main/install.sh | bash
lia --version   # expect 0.3.0+
```

Full notes: [docs/LIA-TRUST.md](docs/LIA-TRUST.md).

---

## 3. FreeLLMAPI path

1. Run FreeLLMAPI (or compatible shim) on `http://127.0.0.1:3001/v1`.
2. Set `FREELLM_API_KEY` (any non-empty local key for FreeLLMAPI).
3. Use Grok models `free-auto` or `free-coder` (`api_backend = "chat_completions"`).
4. Enable ≥1 vision-capable model in FreeLLMAPI for native image turns.
5. Fallback shim: `python tools/free_chat_shim.py` (limited; prefer real FreeLLMAPI).

See `config/models.example.toml` and `config/freellmapi.profiles.md`.

---

## 4. Devin free models path

1. Install **Devin Desktop** from Cognition (coworker’s own account).
2. Log in once in the Desktop app (creates `credentials.toml`).
3. `./tools/devin-bridge/run.sh` → proxy on `http://127.0.0.1:8810`
4. Grok models `devin-free`, `devin-glm`, `devin-swe` use `api_backend = "messages"`.
5. Select: `grok -m devin-free` (or after apply_models, pick in UI).

Details: [docs/DEVIN-BRIDGE.md](docs/DEVIN-BRIDGE.md).

---

## 5. Wire Unity project

```bash
./scripts/wire-unity-project.sh /path/to/YourUnityProject
# Open Unity → domain reload → Tools/UnityGrok menus
```

Assumes Unity is already installed. See [docs/UNITY-INSTALL.md](docs/UNITY-INSTALL.md) for MCP For Unity + UPM.

---

## 6. Blender install (optional)

**Linux**
```bash
# Option A
sudo snap install blender --classic
# Option B — download 5.x from https://www.blender.org/download/
which blender
export BLENDER_BIN=$(which blender)
```

**macOS**
```bash
brew install --cask blender
```

**Windows**
```text
winget install BlenderFoundation.Blender
# or installer from blender.org
```

Full matrix: [docs/SETUP.md](docs/SETUP.md), [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md).

---

## 7. MCP For Unity

Install CoplayDev **MCP For Unity** Editor package so `uvx mcpforunityserver` can talk to the open Editor. Then enable the `unity` MCP in Grok config (plugin ships defaults).

---

## 8. Vision / img2threejs

- **Path A**: FreeLLMAPI vision models (native `image_url`).
- **Path B**: `vision-predescribe` hook for text-only models (`free-coder`, `devin-*`, …).
- **img2threejs**: forge scripts at `$UNITY_GROK_ROOT/tools/img2threejs/forge/...` (skill + vendored tree).

See [docs/VISION-ROUTING.md](docs/VISION-ROUTING.md).

---

## 9. Verify checklist

```bash
./scripts/hygiene_grep.sh
./scripts/doctor.sh --json
python -m pytest tests/ tools/anim/tests/ mcp/blender-gen/tests/ -q
bash tools/gates/run_unity_static_gates.sh --fixture
# FreeLLMAPI
curl -s http://127.0.0.1:3001/v1/models | head
# Devin bridge (if used)
curl -s http://127.0.0.1:8810/health
# img2threejs probe
python tools/img2threejs/forge/stage1_intake/probe_image.py fixtures/ref.png
```

---

## What you get

| Capability | Location |
|------------|----------|
| Unity Editor MCP | `uvx mcpforunityserver` via plugin |
| blender-gen materials/meshes | `mcp/blender-gen/` |
| img2threejs | `tools/img2threejs/` + skill |
| Devin free Messages bridge | `tools/devin-bridge/` |
| SFX pipeline | `tools/sfx/` + skill (empty `sfx_library/`) |
| ARDY → BVH | `tools/anim/` |
| Static Unity C# gates | `tools/gates/` |
| ViewProbe / placement / anim / vfx | `unity-packages/com.unitygrok.uitools` |
| Vision pre-describe | `mcp/vision-check` + UserPromptSubmit hook |
| Free model templates | `config/models.example.toml` |

## Docs

- [SETUP.md](docs/SETUP.md) — full coworker procedure
- [LIA-TRUST.md](docs/LIA-TRUST.md) — optional PreToolUse GATE (≥ 0.3.0)
- [DEVIN-BRIDGE.md](docs/DEVIN-BRIDGE.md)
- [TOOL-CATALOG.md](docs/TOOL-CATALOG.md)
- [UNITY-INSTALL.md](docs/UNITY-INSTALL.md)
- [VISION-ROUTING.md](docs/VISION-ROUTING.md)
- [DEPENDENCIES.md](docs/DEPENDENCIES.md)
- [EXCLUDE.md](EXCLUDE.md) — what is intentionally out

## Tests

```bash
./scripts/hygiene_grep.sh
python -m pytest tests/ tools/anim/tests/ mcp/blender-gen/tests/ -q
bash tools/gates/run_unity_static_gates.sh --fixture
```

## License

MIT for package original code. img2threejs is Apache-2.0 (see NOTICE).
