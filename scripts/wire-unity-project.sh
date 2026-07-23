#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJ="${1:-}"
if [[ -z "$PROJ" || ! -d "$PROJ" ]]; then
  echo "Usage: $0 /path/to/UnityProject" >&2; exit 2
fi
MANIFEST="$PROJ/Packages/manifest.json"
mkdir -p "$PROJ/Packages"
if [[ ! -f "$MANIFEST" ]]; then
  echo '{"dependencies":{}}' > "$MANIFEST"
fi
python3 - "$MANIFEST" "$ROOT" <<'PY'
import json,sys,pathlib
manifest=pathlib.Path(sys.argv[1]); root=pathlib.Path(sys.argv[2]).resolve()
data=json.loads(manifest.read_text())
deps=data.setdefault('dependencies',{})
uit=root/'unity-packages'/'com.unitygrok.uitools'
ad=root/'unity-packages'/'com.unitygrok.agentdebug'
# use absolute file: URI for reliability
deps['com.unitygrok.uitools']=f'file:{uit}'
if ad.is_dir():
    deps['com.unitygrok.agentdebug']=f'file:{ad}'
manifest.write_text(json.dumps(data, indent=2)+chr(10))
print('wired', manifest)
for k,v in deps.items():
    if k.startswith('com.unitygrok'): print(' ',k,'->',v)
PY
echo "Open Unity, wait for domain reload, then menus under Tools/UnityGrok (View Probe, Placement, Anim, Vfx)."
