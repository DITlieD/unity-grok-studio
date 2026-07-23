---
name: sfx-forge
description: >
  Game-lane SFX pipeline: retrieval-first library search, optional generation,
  deterministic assemble, objective QA, audition report. Trigger on any sfx /
  audio / sound-effect creation or replacement, "synthesize a sound", "make a
  wav", firework/buff/impact audio work.
---

# sfx-forge — sound supervisor doctrine

The agent is a **sound supervisor**, not a freestyle DSP author. Real recordings
first; generate only impossible textures; assemble deterministically; QA
objectively; hand a structured audition report to the human ear.

**Hard line: the agent NEVER declares audio done.** The human audition verdict
(approve / reject / notes) is the done-gate.

## Tools (exact invocations)

All under `$UNITY_GROK_ROOT/tools/sfx/`. Prefer package venv python:

```bash
SFX=$UNITY_GROK_ROOT/tools/sfx
PY=${UNITY_GROK_ROOT}/.venv/bin/python
[[ -x $PY ]] || PY=python3
export SFX_LIB=${SFX_LIB:-$UNITY_GROK_ROOT/sfx_library}
```

| Step | Command |
|------|---------|
| QA | `$PY $SFX/analyze_audio.py --file <wav> --profile impact --json` |
| Seed/lib | `$PY $SFX/seed_library.py` (or freesound_fetch; Sonniss drop-in is **optional**) |
| Index | `$PY $SFX/sfx_index_build.py` |
| Search | `$PY $SFX/sfx_search.py --query "..." --license allowed --max-dur 2 --json` |
| Generate | `$PY $SFX/sfx_generate.py --mode t2a --prompt "..." --dur 1.2 --seed 7 --count 4` |
| Assemble | `$PY $SFX/assemble_sfx.py --plan <yaml> --out <dir>` |
| Report | `$PY $SFX/render_audition_report.py --family-dir <dir> --compare <old.wav>` |
| Voice timing (OFF by default) | `$PY $SFX/voice_timing.py --file <guide.wav> --json` |

Exit codes for analyze: **0 pass / 1 threshold fail / 2 scan error**. Never treat 2 as pass.

Fixture for offline smoke: `$UNITY_GROK_ROOT/fixtures/beep.wav`.

## Optional: Sonniss / large libraries
`sonniss_ingest.py` may remain for owners who already have packs. It is **not required**
for coworker setup or offline tests. Do not fail doctor/bootstrap if Sonniss is absent.

## Brief format (before any tool call)

```
source_event:   what physically happens
performance:    force, speed, material
perspective:    close / medium / far; dry / room
treatment:      game need (UI snap, combat impact, loop…)
forbidden:      music, voices, whoosh wash, …
```

## Layer decomposition
- transient (real or procedural — **mandatory real-or-procedural for physical hits**)
- body
- texture / debris
- sub
- tail / sweetener

## Doctrine
1. **RETRIEVAL BEFORE GENERATION.** Physical hits pull library layers via `sfx_search.py`.
2. **One prompt per layer** when generating; explicit negatives (music, voices).
3. **4–8 candidates**, then rank with analyze — never dump 100.
4. **Family-not-file:** variants + optional tiers, not a single one-shot wav.
5. **QA gate mandatory** (`analyze_audio.py`) before report or game.
6. **Provenance mandatory** (ledger + manifest + generation provenance json).
7. **Report mandatory** (`render_audition_report.py`) with verdict slot.
8. **License fail-closed:** `providers.toml` `license_class` — noncommercial/unknown refused
   unless `--research-quarantine`.

## Voice-timing leg (OFF by default)
Only when the user **explicitly hands a guide recording** in the current task.

## Unity
After **approve** verdict only: wire family via your project's SFX player (or builders /
Unity MCP). Do not hand-edit scene/prefab YAML.

## Paths
- Tools: `$UNITY_GROK_ROOT/tools/sfx/`
- Library: `$SFX_LIB` (default `$UNITY_GROK_ROOT/sfx_library`)
- Game clips: under the active Unity project `Assets/SFX/<Family>/`
