#!/usr/bin/env bash
# UserPromptSubmit: if text-only model + image attachments, prepend vision description.
set -euo pipefail
ROOT="${UNITY_GROK_ROOT:-${GROK_PLUGIN_ROOT:-}/..}"
ROOT="$(cd "$ROOT" 2>/dev/null && pwd || echo "$ROOT")"
INPUT="$(cat || true)"
# Default allow / pass-through when no images or vision not needed
export UGS_HOOK_INPUT="$INPUT"
export UGS_ROOT="$ROOT"
python3 - <<'PY'
import json, os, re, sys, subprocess, pathlib
raw = os.environ.get('UGS_HOOK_INPUT','')
root = pathlib.Path(os.environ.get('UGS_ROOT','.'))
try: data = json.loads(raw) if raw.strip() else {}
except Exception: data = {}
# Pass-through strategies: if hook should only inject, print injection JSON per Grok hook contract
# We support both: (1) print additionalContext field (2) plain text prefix
prompt = data.get('prompt') or data.get('userPrompt') or data.get('message') or ''
model = (data.get('model') or data.get('modelId') or os.environ.get('GROK_MODEL','')).lower()
attachments = data.get('attachments') or data.get('images') or data.get('files') or []
paths = []
if isinstance(attachments, list):
    for a in attachments:
        if isinstance(a, str) and re.search(r'\.(png|jpe?g|gif|webp)$', a, re.I):
            paths.append(a)
        elif isinstance(a, dict):
            p = a.get('path') or a.get('file_path') or a.get('url') or ''
            if p and not str(p).startswith('data:'): paths.append(p)
# also scan prompt for image paths
for m in re.finditer(r'(/[^\s]+\.(?:png|jpe?g|gif|webp))', prompt, re.I):
    paths.append(m.group(1))
paths = [p for p in paths if pathlib.Path(p).expanduser().is_file()]
TEXT_ONLY = os.environ.get('UGS_TEXT_ONLY_MODELS', 'free-coder,devin-free,devin-glm,devin-swe,kimi,glm-5,swe-1').split(',')
force = os.environ.get('UGS_FORCE_PREDESCRIBE','0') == '1'
is_text = force or any(t.strip() and t.strip() in model for t in TEXT_ONLY)
if not paths or not is_text:
    # no-op: empty stdout is fine for allow
    sys.exit(0)
server = root/'mcp'/'vision-check'/'server.py'
descs = []
for p in paths[:3]:
    try:
        out = subprocess.check_output([sys.executable, str(server), '--image', p], text=True, timeout=90, stderr=subprocess.DEVNULL)
        descs.append(f'### {p}\n{out.strip()}')
    except Exception as e:
        descs.append(f'### {p}\n(vision-describe failed: {e})')
block = '[vision-predescribe]\n' + '\n\n'.join(descs) + '\n[/vision-predescribe]\n'
# Grok UserPromptSubmit often accepts JSON additionalContext
print(json.dumps({'additionalContext': block, 'decision': 'allow'}))
PY
