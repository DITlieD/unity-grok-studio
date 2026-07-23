# Full coworker setup

End-to-end procedure for a machine that already has (or will install) Unity, Grok, and optional free-model backends.

## Prerequisites matrix

| Tool | Why | Install |
|------|-----|---------|
| Python 3.10+ | bootstrap, MCP, forge scripts | distro / python.org |
| `uv` / `uvx` | MCP wheels (`mcpforunityserver`) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Grok CLI | plugin host | install Grok Build |
| Unity Hub + Editor | project assumed | Unity Hub (confirm large download) |
| Official Unity CLI (optional) | open/install/auth companion | [UNITY-CLI.md](UNITY-CLI.md) — **MCP alone is enough** for live Editor |
| FreeLLMAPI (optional) | `free-auto` / vision | run your FreeLLMAPI instance on `:3001` |
| Devin Desktop (optional) | free Devin models | Cognition installer; own account |
| Blender 5.x (optional) | blender-gen materials/meshes | see OS section below |
| LIA Trust ≥ 0.3.0 (optional recommended) | PreToolUse GATE mediation | see [LIA-TRUST.md](LIA-TRUST.md) |

## 1. Clone + bootstrap

```bash
git clone <this-repo> unity-grok-studio
cd unity-grok-studio
./scripts/bootstrap.sh
export UNITY_GROK_ROOT="$(pwd)"
```

## 2. Install remaining deps

```bash
./scripts/install-deps.sh
# Optional:
./scripts/install-deps.sh --with-blender --assume-yes
./scripts/install-deps.sh --with-devin-bridge
./scripts/install-deps.sh --with-lia          # LIA Trust ≥ 0.3.0 (recommended GATE)
./scripts/install-deps.sh --with-unity-cli    # print official Unity CLI install; binary only with --assume-yes
```

`--with-devin-bridge` only creates `tools/devin-bridge/.venv` and prints login instructions. It does **not** start the proxy without credentials.

`--with-lia` runs the public install one-liner from `DITlieD/lia-trust` main (user network). Prefer **≥ 0.3.0**; v0.2.x is broken for multi-harness/Grok. Details: [LIA-TRUST.md](LIA-TRUST.md).

`--with-unity-cli` prints the official CLI install command by default. With `--assume-yes` it may run the **CLI binary** installer only — never silent multi-GB Editor installs. Full matrix: [UNITY-CLI.md](UNITY-CLI.md).

## 3. FreeLLMAPI one-liner pointers

- Prefer a real FreeLLMAPI with a coding profile of tool-capable models ≥32k context.
- Default base: `http://127.0.0.1:3001/v1`
- Env: `FREELLM_API_KEY=freellmapi-local` (or your key), optional `FREELLM_BASE_URL`
- Profiles notes: `config/freellmapi.profiles.md`, `config/freellmapi.coding.env.example`
- Local fallback only: `python tools/free_chat_shim.py` (not a full FreeLLMAPI replacement)

Health:

```bash
curl -s http://127.0.0.1:3001/v1/models -H "Authorization: Bearer $FREELLM_API_KEY" | head
```

## 4. Apply free model stanzas

```bash
./scripts/apply_models.sh
# or manually merge config/models.example.toml into ~/.grok/config.toml
```

## 5. Plugin

```bash
grok plugin install "$UNITY_GROK_ROOT/plugin" --trust
grok plugin enable unity-grok-studio
```

## 6. Devin free models (optional)

```bash
# After Devin Desktop install + login:
./tools/devin-bridge/run.sh
curl -s http://127.0.0.1:8810/health
grok -m devin-free
```

Step-by-step: [DEVIN-BRIDGE.md](DEVIN-BRIDGE.md).

## 7. Blender install (exact)

### Linux

```bash
# Option A
sudo snap install blender --classic
# Option B
# download from https://www.blender.org/download/  (5.x recommended)
which blender
export BLENDER_BIN=$(which blender)
```

### macOS

```bash
brew install --cask blender
```

### Windows

```text
winget install BlenderFoundation.Blender
# or installer from blender.org
```

Confirm:

```bash
blender --version   # or %BLENDER_BIN%
./scripts/doctor.sh # [ok] blender when on PATH
```

## 8. Unity + MCP For Unity

Unity is **assumed present**. Focus:

1. Install CoplayDev MCP For Unity Editor package.
2. Open your project; ensure the MCP bridge is running.
3. Wire package UPM: `./scripts/wire-unity-project.sh /path/to/Project`
4. Domain reload → Tools/UnityGrok menus.

**MCP alone is enough** for the live Editor agent loop. Optional official Unity CLI companion (install/open/auth; never required): [UNITY-CLI.md](UNITY-CLI.md).

Details: [UNITY-INSTALL.md](UNITY-INSTALL.md).

## 9. Doctor matrix

```bash
./scripts/doctor.sh
./scripts/doctor.sh --json
```

Expect components including: `python`, `uvx`, `grok_plugin`, `blender`, `unity_editor`, `unity_cli` (optional companion; missing does not fail overall doctor), `freellmapi`, `devin_bridge`, `devin_credentials`, `lia` (≥ 0.3.0 → `ok`), MCP wrappers, UPM packages.

Statuses:

- `ok` — ready
- `warn` — optional missing (e.g. bridge not running, FreeLLMAPI down)
- `missing` — install or fix

## 10. Isolated sandbox session (if you use unity-grok-sandbox)

```bash
# sibling checkout
export UNITY_GROK_ROOT=/path/to/unity-grok-studio
./start-grok.sh
# or: ./start-grok.sh --unity /path/to/UnityProject
# model: GROK_MODEL=devin-free ./start-grok.sh
```

## Verify checklist

- [ ] `./scripts/hygiene_grep.sh` → OK
- [ ] `./scripts/doctor.sh` shows python/uvx ok
- [ ] FreeLLMAPI health **or** Devin bridge health (depending on path)
- [ ] Plugin enabled
- [ ] Unity project wired if doing Editor work
- [ ] Blender on PATH if using blender-gen
- [ ] LIA Trust ≥ 0.3.0 if using PreToolUse GATE (`lia --version`; doctor `[ok] lia`)
- [ ] `python tools/img2threejs/forge/stage1_intake/probe_image.py fixtures/ref.png` exits 0
