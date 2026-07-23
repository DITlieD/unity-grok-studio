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
# Official standalone Unity CLI (optional companion — never fails overall doctor)
# Distinct from Editor binary: probe `unity --version` for CLI-like success.
import re, subprocess  # early import; LIA block also uses these
UNITY_CLI_INSTALL = (
    'curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash  '
    '# or: ./scripts/install-deps.sh --with-unity-cli  (see docs/UNITY-CLI.md)'
)
unity_cli_bin = shutil.which('unity')
if not unity_cli_bin:
    add('unity_cli', 'missing', 'unity not on PATH', UNITY_CLI_INSTALL)
else:
    ver_detail = unity_cli_bin
    cli_ok = False
    try:
        r = subprocess.run(
            [unity_cli_bin, '--version'],
            capture_output=True, text=True, timeout=8,
        )
        out = ((r.stdout or '') + (r.stderr or '')).strip()
        first = out.splitlines()[0] if out else ''
        # Standalone CLI prints a version; accept success exit or version-like text.
        # Avoid treating a bare Editor binary mis-named "unity" as ok if --version fails hard.
        if r.returncode == 0 and (first or out):
            cli_ok = True
            ver_detail = first or out[:200]
        elif re.search(r'\d+\.\d+', out) and r.returncode in (0, 1):
            # Some builds print version on stderr with nonzero; still CLI-like.
            cli_ok = True
            ver_detail = first or out[:200]
        else:
            ver_detail = f'{unity_cli_bin} present but --version failed ({first or r.returncode})'
    except Exception as e:
        ver_detail = f'{unity_cli_bin} error: {e}'
    if cli_ok:
        add('unity_cli', 'ok', ver_detail, '')
    else:
        add(
            'unity_cli',
            'warn',
            ver_detail,
            UNITY_CLI_INSTALL + '  # ensure standalone CLI, not Editor binary',
        )
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
# LIA Trust (optional PreToolUse GATE) — recommend ≥ 0.3.0; v0.2.x broken for multi-harness/Grok
LIA_INSTALL = 'curl -fsSL https://raw.githubusercontent.com/DITlieD/lia-trust/main/install.sh | bash'
LIA_MIN = (0, 3, 0)
lia_bin = shutil.which('lia')
if not lia_bin:
    add('lia', 'warn', 'lia not on PATH', LIA_INSTALL + '  # see docs/LIA-TRUST.md')
else:
    ver_str = ''
    try:
        r = subprocess.run([lia_bin, '--version'], capture_output=True, text=True, timeout=5)
        ver_str = (r.stdout or r.stderr or '').strip().splitlines()[0] if (r.stdout or r.stderr) else ''
    except Exception as e:
        ver_str = f'error: {e}'
    m = re.search(r'v?(\d+)\.(\d+)\.(\d+)', ver_str or '')
    if not m:
        # try `lia version` or bare digits elsewhere
        try:
            r2 = subprocess.run([lia_bin, 'version'], capture_output=True, text=True, timeout=5)
            alt = (r2.stdout or r2.stderr or '').strip()
            m = re.search(r'v?(\d+)\.(\d+)\.(\d+)', alt)
            if m:
                ver_str = alt.splitlines()[0] if alt else ver_str
        except Exception:
            pass
    if m:
        tup = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        detail = ver_str or f'{tup[0]}.{tup[1]}.{tup[2]}'
        if tup >= LIA_MIN:
            add('lia', 'ok', detail, '')
        else:
            add(
                'lia',
                'warn',
                f'{detail} (< 0.3.0; v0.2.x broken for multi-harness/Grok)',
                LIA_INSTALL + '  # reinstall from DITlieD/lia-trust main',
            )
    else:
        add(
            'lia',
            'warn',
            f'{lia_bin} present but version unparsed ({ver_str!r}); expect 0.3.0+',
            LIA_INSTALL + '  # reinstall from DITlieD/lia-trust main',
        )
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
