# LIA Trust (optional PreToolUse GATE)

**LIA Trust** is an optional tool-trust mediator for Grok Build PreToolUse hooks. It is **recommended** for safer tool mediation (shell, write, edit, etc.).

## Version requirement

Use **LIA Trust ≥ 0.3.0**.

- **v0.2.x was broken** for multi-harness / Grok Build adapter paths — do not use it.
- Prefer latest from `DITlieD/lia-trust` **main**.

Doctor component: `lia` (`./scripts/doctor.sh`). Status is `ok` only when `lia` is on `PATH` and the version parses as **≥ 0.3.0**.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/DITlieD/lia-trust/main/install.sh | bash
lia --version   # expect 0.3.0+
lia doctor && lia status
# if needed: lia install --apply-live
```

Or from this package:

```bash
./scripts/install-deps.sh --with-lia
```

## How the plugin uses LIA

- PreToolUse hook: `plugin/hooks/bin/lia-pretool.sh` (wired in `plugin/hooks/hooks.json`).
- Maps Grok tool envelopes to LIA’s Claude-code adapter, then maps LIA’s permission decision back to Grok.
- **Default: fail-open** if `lia` is missing, home is unconfigured, or the binary is too old (tools are allowed with a reason string). Coworkers can use the plugin without LIA installed.

## Environment

| Variable | Default | Notes |
|----------|---------|--------|
| `LIA_HOME` | `~/.lia-trust` | Config / journal / keys root |
| `LIA_BIN` | `lia` on `PATH` | Override binary path |
| `LIA_CONFIG` | `$LIA_HOME/config.json` | |
| `LIA_JOURNAL` | `$LIA_HOME/journal/default.db` | |
| `LIA_KEY_FILE` | `$LIA_HOME/keys/signing.hex` | |
| `LIA_KEY_ID` | `lia-install` | |
| `LIA_ADAPTER` | `claude-code` | |
| `LIA_REQUIRED` | unset / `0` | When set to `1`, fail-**closed**: deny tools if LIA is missing or version &lt; 0.3.0 |

### Fail-closed mode

```bash
export LIA_REQUIRED=1
```

With `LIA_REQUIRED=1`, `lia-pretool.sh` returns `decision: deny` if:

- `lia` is not installed / not executable, or
- version cannot be parsed as ≥ 0.3.0

Default remains fail-open so install stays optional.

## Related

- [DEPENDENCIES.md](DEPENDENCIES.md) — Bucket C optional recommended
- [SETUP.md](SETUP.md) — full coworker setup
- `./scripts/doctor.sh` — `[ok|warn] lia`
- `./scripts/install-deps.sh --with-lia`
