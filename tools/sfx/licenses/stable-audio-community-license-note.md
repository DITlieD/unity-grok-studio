# Stable Audio 3 Small SFX — recon note (U4 / R1)

**Fetch date:** 2026-07-19

## Status: PARKED (A3/A4 path)

- Shipping provider key: `stable_audio_3_small_sfx` in `providers.toml`
- `license_class`: `commercial_ok` (Stability Community License — commercial use
  permitted below the revenue threshold per research dossier [SFX-R] 20.2)
- `status`: `parked_pending_host`

## Why parked

Unattended recon did not stand up live weights + inference host in this session:

1. Full model download + GPU host (remote 3090) not confirmed free for batch.
2. Local CPU generation wall-time not benchmarked under 10 min/clip threshold
   without installing torch + model weights into the sfx venv (large dep).

Per plan ABORT A3/A4: **generation leg parked**; retrieval-only pipeline ships.
`sfx_generate.py` exits 3 with parked JSON when called without
`--allow-dsp-placeholder`. Noncommercial providers still fail-closed (exit 1)
naming `license_class`.

## Re-open checklist

1. WebFetch live license at https://stability.ai/license and archive text here.
2. Confirm Small SFX checkpoint path from Stability-AI repos.
3. FORK F2: ssh probe 3090 + nvidia-smi ≥4GB free → remote; else CPU timed run.
4. Flip `status` to `live` only after one 2s t2a wav + provenance lands.

## Refusal path (always live)

```bash
.venv/bin/python sfx_generate.py --provider research_sony_woosh \
  --prompt "test" --dur 0.5 --count 1
# expect nonzero exit, license_class=noncommercial named
```
