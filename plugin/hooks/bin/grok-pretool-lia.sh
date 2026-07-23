#!/usr/bin/env bash
# Grok PreToolUse → LIA Trust adapter.
# Maps Grok hook envelope (camelCase toolName/toolInput) to Claude-code adapter
# schema, then maps LIA's permissionDecision back to Grok decision JSON.
#
# Env (optional):
#   LIA_HOME          default: ~/.lia-trust
#   LIA_BIN           default: lia on PATH
#   LIA_CONFIG        default: $LIA_HOME/config.json
#   LIA_JOURNAL       default: $LIA_HOME/journal/default.db
#   LIA_KEY_FILE      default: $LIA_HOME/keys/signing.hex
#   LIA_KEY_ID        default: lia-install
#   LIA_ADAPTER       default: claude-code
set -euo pipefail

LIA_HOME="${LIA_HOME:-$HOME/.lia-trust}"
LIA_BIN="${LIA_BIN:-$(command -v lia || true)}"
LIA_CONFIG="${LIA_CONFIG:-$LIA_HOME/config.json}"
LIA_JOURNAL="${LIA_JOURNAL:-$LIA_HOME/journal/default.db}"
LIA_KEY_FILE="${LIA_KEY_FILE:-$LIA_HOME/keys/signing.hex}"
LIA_KEY_ID="${LIA_KEY_ID:-lia-install}"
LIA_ADAPTER="${LIA_ADAPTER:-claude-code}"

if [[ -z "${LIA_BIN}" || ! -x "${LIA_BIN}" ]]; then
  # Fail-open only when LIA is not installed: coworkers may not have it yet.
  # Documented: run bootstrap / lia install. Explicit deny still requires LIA.
  echo '{"decision":"allow","reason":"lia binary missing; install lia-trust for GATE mediation"}'
  exit 0
fi

if [[ ! -f "${LIA_CONFIG}" || ! -f "${LIA_KEY_FILE}" ]]; then
  echo '{"decision":"allow","reason":"lia home not configured; run lia install --apply-live"}'
  exit 0
fi

SECRET="$(tr -d '[:space:]' < "${LIA_KEY_FILE}")"
INPUT="$(cat)"

# Translate Grok/Claude envelopes → Claude adapter schema via python (stdlib).
export LIA_HOOK_INPUT="$INPUT"
CLAUDE_JSON="$(python3 - <<'PY'
import json, os, sys

raw = os.environ.get("LIA_HOOK_INPUT", "")
try:
    data = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    data = {}

# Grok uses camelCase; Claude uses snake_case. Accept both.
tool = (
    data.get("toolName")
    or data.get("tool_name")
    or data.get("tool")
    or ""
)
tin = data.get("toolInput") or data.get("tool_input") or {}
if not isinstance(tin, dict):
    tin = {"value": tin}

# Map Grok tool names → LIA Claude matcher names.
MAP = {
    "run_terminal_command": "Bash",
    "Bash": "Bash",
    "shell": "Bash",
    "read_file": "Read",
    "Read": "Read",
    "search_replace": "Edit",
    "Edit": "Edit",
    "Write": "Write",
    "write": "Write",
    "MultiEdit": "MultiEdit",
    "Delete": "Delete",
    "grep": "Read",  # content read path — scope gate only
    "list_dir": "Read",
}

claude_tool = MAP.get(tool, tool or "Bash")

# Normalize shell payload field names.
if claude_tool == "Bash":
    cmd = tin.get("command") or tin.get("cmd") or tin.get("shell") or ""
    tin = {"command": cmd}
elif claude_tool in ("Read", "Write", "Edit", "Delete", "MultiEdit"):
    path = tin.get("file_path") or tin.get("path") or tin.get("target_file") or tin.get("file_path")
    if path is not None:
        tin = dict(tin)
        tin["file_path"] = path

out = {
    "hook_event_name": "PreToolUse",
    "tool_name": claude_tool,
    "tool_input": tin,
    "cwd": data.get("cwd") or data.get("workspaceRoot") or os.getcwd(),
    "session_id": data.get("sessionId") or data.get("session_id") or "",
    "tool_use_id": data.get("toolUseId") or data.get("tool_use_id") or "",
    "permission_mode": data.get("permissionMode") or data.get("permission_mode") or "default",
}
print(json.dumps(out))
PY
)"

set +e
LIA_OUT="$(printf '%s' "$CLAUDE_JSON" | "$LIA_BIN" hook \
  --adapter "$LIA_ADAPTER" \
  --config "$LIA_CONFIG" \
  --journal "$LIA_JOURNAL" \
  --secret-key-hex "$SECRET" \
  --key-id "$LIA_KEY_ID" 2>/tmp/lia-hook-stderr.$$)"
LIA_RC=$?
set -e
STDERR="$(cat /tmp/lia-hook-stderr.$$ 2>/dev/null || true)"
rm -f /tmp/lia-hook-stderr.$$

# Map LIA Claude output → Grok decision JSON.
export LIA_OUT LIA_RC STDERR
python3 - <<'PY'
import json, os, sys

out_raw = os.environ.get("LIA_OUT", "")
rc = int(os.environ.get("LIA_RC", "0") or "0")
stderr = os.environ.get("STDERR", "")

decision = "allow"
reason = "lia gates allow"

try:
    data = json.loads(out_raw) if out_raw.strip() else {}
except json.JSONDecodeError:
    data = {}

hso = data.get("hookSpecificOutput") or {}
pd = (hso.get("permissionDecision") or data.get("permissionDecision") or data.get("decision") or "").lower()
reason = (
    hso.get("permissionDecisionReason")
    or data.get("permissionDecisionReason")
    or data.get("reason")
    or stderr.strip()
    or reason
)

if pd in ("deny", "block") or rc == 2:
    decision = "deny"
elif pd in ("ask", "defer"):
    # Grok has no ask; deny to stay fail-closed on irreversible ambiguity.
    if "SHELL" in reason.upper() or "DESTRUCT" in reason.upper() or "irreversib" in reason.lower():
        decision = "deny"
    else:
        decision = "allow"
        reason = f"lia={pd}: {reason}"

print(json.dumps({"decision": decision, "reason": reason}))
# Exit 0 always with explicit decision JSON — Grok honors deny in stdout.
sys.exit(0)
PY
