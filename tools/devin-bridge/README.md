# Devin bridge (portable)

Local Anthropic Messages proxy for free Devin models, using **your** Devin Desktop login.

## Coworker setup

1. Install [Devin Desktop](https://app.devin.ai/) from Cognition (your own account).
2. Log in once in the Desktop app (creates `credentials.toml`).
3. From the package root:
   ```bash
   ./tools/devin-bridge/run.sh
   ```
4. Health: `curl -s http://127.0.0.1:8810/health`
5. Point Grok models (`devin-free`, `devin-glm`, `devin-swe`) at `http://127.0.0.1:8810/v1` with `api_backend = "messages"` (see `config/models.example.toml`).

## Env

| Variable | Default | Meaning |
|----------|---------|---------|
| `DEVIN_PROXY_PORT` | `8810` | Bind port |
| `DEVIN_TOOL_DESC` | `generic` | Content-filter survival (`generic` recommended) |
| `DEVIN_PROXY_MODEL` | (optional) | Default model if request model unknown |
| `DEVIN_CREDS` | auto-discover | Path to `credentials.toml` |
| `DEVIN_BRIDGE_FOREGROUND` | `0` | `1` = run in foreground |

## Credential discovery

- Linux: `~/.local/share/devin/credentials.toml`, `~/.config/devin/`, `~/.config/Devin/`
- macOS: `~/Library/Application Support/devin/`
- Windows/WSL: `/mnt/c/Users/$USER/AppData/Roaming/devin/credentials.toml`
- Override: `DEVIN_CREDS=/path/to/credentials.toml`

## Troubleshooting

- Content filter: ensure `DEVIN_TOOL_DESC=generic`
- No credentials: install Devin Desktop, log in, re-run
- Port in use: set `DEVIN_PROXY_PORT=8811` or stop the other process

See also: `docs/DEVIN-BRIDGE.md` at package root.
