---
name: sfx-forge
description: >
  Game-lane SFX pipeline: retrieval-first library search, optional generation,
  deterministic assemble, objective QA, audition report. Trigger on any sfx /
  audio / sound-effect creation or replacement, "synthesize a sound", "make a
  wav", "sfx for X", firework/buff/impact audio work in work_games.
---

# sfx-forge — sound supervisor doctrine

The agent is a **sound supervisor**, not a freestyle DSP author. Real recordings
first; generate only impossible textures; assemble deterministically; QA
objectively; hand a structured audition report to the human ear.

**Hard line: the agent NEVER declares audio done.** Raian's audition verdict
(approve / reject / notes) is the done-gate.

## Tools (exact invocations)

All under `$UNITY_GROK_ROOT/tools/sfx/`. Use the local venv:

```bash
SFX=$UNITY_GROK_ROOT/tools/sfx
PY=$SFX/.venv/bin/python
export SFX_LIB=${SFX_LIB:-$UNITY_GROK_ROOT/sfx_library}
```

| Step | Command |
|------|---------|
| QA | `$PY $SFX/analyze_audio.py --file <wav> --profile impact --json` |
| Seed/lib | `$PY $SFX/seed_library.py` (or freesound_fetch / Sonniss drop-in) |
| Index | `$PY $SFX/sfx_index_build.py` |
| Search | `$PY $SFX/sfx_search.py --query "..." --license allowed --max-dur 2 --json` |
| Generate | `$PY $SFX/sfx_generate.py --mode t2a --prompt "..." --dur 1.2 --seed 7 --count 4` |
| Assemble | `$PY $SFX/assemble_sfx.py --plan <yaml> --out <dir>` |
| Report | `$PY $SFX/render_audition_report.py --family-dir <dir> --compare <old.wav>` |
| Voice timing (OFF by default) | `$PY $SFX/voice_timing.py --file <guide.wav> --json` |

Exit codes for analyze: **0 pass / 1 threshold fail / 2 scan error**. Never treat 2 as pass.

## Game direction: stylized / fantasy

The current game wants **cartoonish, exaggerated, readable** sound, not dry
realism. Favor designed/stylized library sources (Sonniss designed packs,
Freesound `cartoon` / `magic` / `sparkle` hits) over field-recorded realism, and
exaggeration over fidelity: a boing with character beats a physically-correct
thud. When searching, lead with style terms (`cartoon`, `stylized`, `magic`,
`whoosh`, `sparkle`) and the fantasy/cartoon tags the ledger carries. When
generating a missing layer, prompt for the stylized read, not the literal one.
Physical-hit realism still routes through retrieval first (doctrine 1); this
only shifts which retrieved candidates win.

## Brief format (before any tool call)

```
source_event:   what physically happens
performance:    force, speed, material
perspective:    close / medium / far; dry / room
treatment:      game need (UI snap, combat impact, loop…)
forbidden:      music, voices, whoosh wash, …
```

## Layer decomposition

Break the event into layers **before** search/generate:

- transient (real or procedural — **mandatory real-or-procedural for physical hits**)
- body
- texture / debris
- sub
- tail / sweetener

## Doctrine

1. **RETRIEVAL BEFORE GENERATION.** Physical hits pull library layers via
   `sfx_search.py`. Search refuses non-ledgered paths; assemble refuses
   quarantine.
2. **One prompt per layer** when generating; explicit negatives (music, voices).
3. **4–8 candidates**, then rank with analyze — never dump 100.
4. **Family-not-file:** variants + optional tiers, not a single one-shot wav.
5. **QA gate mandatory** (`analyze_audio.py`) before report or game.
6. **Provenance mandatory** (ledger + manifest + generation provenance json).
7. **Report mandatory** (`render_audition_report.py`) with verdict slot.
8. **License fail-closed:** `providers.toml` `license_class` —
   noncommercial/unknown refused unless `--research-quarantine` (quarantine dir
   unread by search/assemble). No model laundering.
9. Legacy freestyle `gen_*_sfx.py` scripts are deprecated for new work; existing
   wavs stay until owner orders replacement.

## Voice-timing leg (OFF by default)

Only when Raian **explicitly hands a guide recording** in the current task:

```bash
$PY $SFX/voice_timing.py --file <guide.wav> --out event_map.yaml --json
$PY $SFX/assemble_sfx.py --plan <yaml> --event-map event_map.yaml --out <dir>
```

Never auto-fire. Never a dependency of other units.

## Unity

After **approve** verdict only: wire family via `SfxFamilyPlayer` (no-repeat +
bounded jitter). Do not hand-edit scene/prefab YAML; use builders / unityMCP.

## Paths

- Tools: `$UNITY_GROK_ROOT/tools/sfx/`
- Skill: this file
- Library: `$SFX_LIB` (default `$UNITY_GROK_ROOT/sfx_library`)
- Game clips: `{CURRENT_GAME}/Assets/SFX/<Family>/`
