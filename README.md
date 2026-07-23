# unity-grok-studio

Standalone **Grok Build plugin** + vendored MCP servers + CLI tools + optional Unity UPM packages for Unity game work — **zero dependency on any private monorepo or owner machine**.

## Quick start

```bash
git clone <this-repo> unity-grok-studio
cd unity-grok-studio
./scripts/bootstrap.sh
export UNITY_GROK_ROOT="$(pwd)"
export FREELLM_API_KEY=freellmapi-local   # or your FreeLLMAPI key
grok plugin install "$(pwd)/plugin" --trust
./scripts/doctor.sh
```

## What you get

| Capability | Location |
|------------|----------|
| Unity Editor MCP | `uvx mcpforunityserver` via plugin `.mcp.json` |
| blender-gen materials/meshes | `mcp/blender-gen/` |
| img2threejs | `tools/img2threejs/` + skill |
| SFX pipeline | `tools/sfx/` + skill (empty `sfx_library/`) |
| ARDY → BVH | `tools/anim/` |
| Static Unity C# gates | `tools/gates/` |
| ViewProbe / placement / anim / vfx | `unity-packages/com.unitygrok.uitools` |
| Vision pre-describe | `mcp/vision-check` + UserPromptSubmit hook |
| Free model templates | `config/models.example.toml` |

## Wire a Unity project

```bash
./scripts/wire-unity-project.sh /path/to/YourUnityProject
# Open Unity → domain reload → Tools/UnityGrok menus
```

## Docs
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
