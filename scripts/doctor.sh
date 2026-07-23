#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export UNITY_GROK_ROOT="$ROOT"
JSON=0
[[ "${1:-}" == "--json" ]] && JSON=1
python3 - "$ROOT" "$JSON" <<'PY'
import json, os, shutil, sys, pathlib, glob
root = pathlib.Path(sys.argv[1]); as_json = sys.argv[2] == '1'
comps = {}
def add(name, status, detail='', fix=''):
    comps[name] = {'status': status, 'detail': detail, 'fix': fix}
p = shutil.which('python3') or shutil.which('python')
add('python', 'ok' if p else 'missing', p or '', 'install Python 3.10+')
uv = shutil.which('uvx') or shutil.which('uv')
add('uvx', 'ok' if uv else 'missing', uv or '', 'curl -LsSf https://astral.sh/uv/install.sh | sh')
g = shutil.which('grok')
add('grok_plugin', 'ok' if g else 'warn', g or 'grok CLI not found', 'install Grok Build')
b = shutil.which('blender')
add('blender', 'ok' if b else 'missing', b or '', 'snap install blender --classic  # or see docs/SETUP.md')
unity_ok = shutil.which('Unity') is not None or bool(glob.glob(str(pathlib.Path.home()/'Unity'/'Hub'/'Editor'/'*'/'Editor'/'Unity')))
add('unity_editor', 'ok' if unity_ok else 'missing', '', 'Install Unity Hub; see docs/UNITY-INSTALL.md')
freellm='warn'
try:
    import urllib.request
    urllib.request.urlopen('http://127.0.0.1:3001/v1/models', timeout=1)
    freellm='ok'
except Exception:
    pass
add('freellmapi', freellm, 'listening :3001' if freellm=='ok' else 'not on :3001', 'start FreeLLMAPI')
# Devin bridge health + credential discovery
port = os.environ.get('DEVIN_PROXY_PORT', '8810')
bridge_status = 'warn'
bridge_detail = f'not on :{port}'
bridge_fix = './tools/devin-bridge/run.sh  # after Devin Desktop login'
try:
    import urllib.request
    urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=1)
    bridge_status = 'ok'
    bridge_detail = f'listening :{port}'
    bridge_fix = ''
except Exception:
    pass
add('devin_bridge', bridge_status, bridge_detail, bridge_fix)
# optional credentials detail
home = pathlib.Path.home()
cred_candidates = [
    home/'.local/share/devin/credentials.toml',
    home/'.config/devin/credentials.toml',
    home/'.config/Devin/credentials.toml',
    home/'Library/Application Support/devin/credentials.toml',
]
if os.environ.get('DEVIN_CREDS'):
    cred_candidates.insert(0, pathlib.Path(os.environ['DEVIN_CREDS']))
cred_found = next((str(c) for c in cred_candidates if c.is_file()), None)
if cred_found:
    add('devin_credentials', 'ok', cred_found, '')
else:
    add('devin_credentials', 'warn', 'credentials.toml not found', 'Install Devin Desktop, log in once; or set DEVIN_CREDS')
add('mcp_blender_gen', 'ok' if (root/'mcp'/'wrappers'/'blender-gen.sh').exists() else 'missing')
add('mcp_vision_check', 'ok' if (root/'mcp'/'wrappers'/'vision-check.sh').exists() else 'missing')
add('unity_uitools_package', 'ok' if (root/'unity-packages'/'com.unitygrok.uitools').is_dir() else 'missing')
add('unity_project_uitools', 'warn', 'run wire-unity-project.sh for a project', './scripts/wire-unity-project.sh /path/to/Project')
ok = comps.get('python',{}).get('status')=='ok'
payload={'ok': ok, 'components': comps}
if as_json:
    print(json.dumps(payload))
else:
    for k,v in comps.items():
        print(f"[{v['status']}] {k} - {v.get('detail','')}")
        if v.get('fix') and v['status'] != 'ok':
            print(f"         fix: {v['fix']}")
    print('doctor: done')
PY
