#!/usr/bin/env bash
# Wire unity-grok UPM packages into a Unity project manifest.
# Default: com.unitygrok.uitools + com.unitygrok.agentdebug only.
# Opt-in: --with-pipeline adds com.unity.pipeline (official CLI companion; never default).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJ=""
WITH_PIPELINE=0
USAGE="Usage: $0 /path/to/UnityProject [--with-pipeline]

  Default: wire com.unitygrok.uitools + com.unitygrok.agentdebug (ViewProbe, placement, …).
  --with-pipeline: also ensure com.unity.pipeline in manifest (opt-in; for unity command eval).
                   Prefer when official Unity CLI is present. Does not remove Coplay MCP.
                   See docs/UNITY-CLI.md. MCP alone is enough for the live Editor loop.
"
for a in "$@"; do
  case "$a" in
    --with-pipeline) WITH_PIPELINE=1;;
    -h|--help) printf '%s' "$USAGE"; exit 0;;
    -*)
      echo "Unknown option: $a" >&2
      printf '%s' "$USAGE" >&2
      exit 2
      ;;
    *)
      if [[ -z "$PROJ" ]]; then PROJ="$a"
      else
        echo "Unexpected argument: $a" >&2
        printf '%s' "$USAGE" >&2
        exit 2
      fi
      ;;
  esac
done
if [[ -z "$PROJ" || ! -d "$PROJ" ]]; then
  printf '%s' "$USAGE" >&2
  exit 2
fi
MANIFEST="$PROJ/Packages/manifest.json"
mkdir -p "$PROJ/Packages"
if [[ ! -f "$MANIFEST" ]]; then
  echo '{"dependencies":{}}' > "$MANIFEST"
fi
python3 - "$MANIFEST" "$ROOT" "$WITH_PIPELINE" <<'PY'
import json, sys, pathlib
manifest = pathlib.Path(sys.argv[1])
root = pathlib.Path(sys.argv[2]).resolve()
with_pipeline = sys.argv[3] == '1'
data = json.loads(manifest.read_text())
deps = data.setdefault('dependencies', {})
uit = root / 'unity-packages' / 'com.unitygrok.uitools'
ad = root / 'unity-packages' / 'com.unitygrok.agentdebug'
# use absolute file: URI for reliability
deps['com.unitygrok.uitools'] = f'file:{uit}'
if ad.is_dir():
    deps['com.unitygrok.agentdebug'] = f'file:{ad}'
if with_pipeline:
    # Official experimental pipeline package — version float is intentional (Unity resolves).
    # Do not pin aggressively; coworker may adjust. Only added when --with-pipeline.
    if 'com.unity.pipeline' not in deps:
        deps['com.unity.pipeline'] = '0.1.0-exp.1'
        print('added com.unity.pipeline (opt-in; open project in Unity to resolve)')
    else:
        print('com.unity.pipeline already present:', deps['com.unity.pipeline'])
manifest.write_text(json.dumps(data, indent=2) + '\n')
print('wired', manifest)
for k, v in deps.items():
    if k.startswith('com.unitygrok') or k == 'com.unity.pipeline':
        print(' ', k, '->', v)
if with_pipeline:
    print('Pipeline is opt-in only. Prefer Coplay MCP for scene/GO; CLI eval when connected.')
    print('If CLI present: unity pipeline install  # alternate path; see docs/UNITY-CLI.md')
PY
echo "Open Unity, wait for domain reload, then menus under Tools/UnityGrok (View Probe, Placement, Anim, Vfx)."
