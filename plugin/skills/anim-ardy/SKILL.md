---
name: anim-ardy
description: ARDY animation prototype CLI to BVH. Offline synthetic path for tests; live ARDY when service available.
---
# anim-ardy

Scripts under `$UNITY_GROK_ROOT/tools/anim/`:
- `ardy_client.py --synthetic --seed 42` → JSON motion
- `ardy_to_bvh.py` → BVH
- `ardy_skeleton.py` skeleton map

Default outputs: `./outputs/anims/` (create if missing).

## Smoke
```bash
export UNITY_GROK_ROOT=...
python $UNITY_GROK_ROOT/tools/anim/ardy_client.py --synthetic --seed 42 -o /tmp/ardy.json
python $UNITY_GROK_ROOT/tools/anim/ardy_to_bvh.py /tmp/ardy.json -o /tmp/ardy.bvh
```
Golden tests live in `tools/anim/tests/`.
