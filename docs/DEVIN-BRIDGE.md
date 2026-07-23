# Devin bridge (standalone)

Portable local proxy that turns Devin Desktop credentials into an Anthropic **Messages** API on `127.0.0.1:8810` for free Devin models (`kimi-k2-7`, `glm-5-2`, `swe-1-6`, …).

**Does not depend on any private monorepo.** All code lives under `tools/devin-bridge/`.

## Steps

### 1. Install Devin Desktop

Install from Cognition (coworker’s **own** account). Do not share credentials.

### 2. Log in once

Open Devin Desktop and complete login. This creates `credentials.toml` under the Desktop app’s data dir.

Common paths:

| OS | Path |
|----|------|
| Linux | `~/.local/share/devin/credentials.toml` |
| Linux (alt) | `~/.config/devin/credentials.toml`, `~/.config/Devin/credentials.toml` |
| macOS | `~/Library/Application Support/devin/credentials.toml` |
| Windows / WSL | `%APPDATA%\devin\credentials.toml` (WSL: `/mnt/c/Users/$USER/AppData/Roaming/devin/`) |

Override: `export DEVIN_CREDS=/path/to/credentials.toml`

### 3. Start the bridge

```bash
cd /path/to/unity-grok-studio
./tools/devin-bridge/run.sh
# Health
curl -s http://127.0.0.1:8810/health
```

First run creates `tools/devin-bridge/.venv` and installs `requirements.txt`.

Idempotent: if already healthy on the port, exits 0.

Foreground debug: `DEVIN_BRIDGE_FOREGROUND=1 ./tools/devin-bridge/run.sh`

### 4. Grok model stanzas

From `config/models.example.toml` (apply with `./scripts/apply_models.sh`):

- `devin-free` → model `kimi-k2-7`
- `devin-glm` → model `glm-5-2`
- `devin-swe` → model `swe-1-6`

All use:

- `base_url = "http://127.0.0.1:8810/v1"`
- `api_backend = "messages"`
- `api_key = "devin-local"` (local placeholder; real auth is Desktop credentials)

### 5. Select model in Grok

```bash
grok -m devin-free
# or
GROK_MODEL=devin-glm grok
```

After `apply_models`, models appear in the Grok model picker.

### 6. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Content filter / empty tools | Keep `DEVIN_TOOL_DESC=generic` (default in `run.sh`) |
| No credentials | Install Devin Desktop, log in, re-run. Or `DEVIN_CREDS=...` |
| Port in use | `DEVIN_PROXY_PORT=8811 ./tools/devin-bridge/run.sh` and update model `base_url` |
| Bridge not healthy | Check `tools/devin-bridge/proxy.log`; re-login Desktop |
| Doctor warns `devin_bridge` | Expected when proxy not running; start `run.sh` |

## Defaults

| Env | Default |
|-----|---------|
| `DEVIN_PROXY_PORT` | `8810` |
| `DEVIN_TOOL_DESC` | `generic` |
| `DEVIN_PROXY_MODEL` | optional empty (request body model wins when recognised) |

## Related

- `tools/devin-bridge/README.md`
- `plugin/skills/cheap-harness/SKILL.md`
- `scripts/doctor.sh` component `devin_bridge`
- `scripts/install-deps.sh --with-devin-bridge`
