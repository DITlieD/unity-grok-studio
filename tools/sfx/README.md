# sfx-forge tools

Studio SFX pipeline (see `workflow/plans/sfx-forge-pipeline-2026-07.md` and
`.claude/skills/sfx-forge/SKILL.md`).

## Setup

```bash
cd .claude/tools/sfx
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export SFX_LIB=${SFX_LIB:-$UNITY_GROK_ROOT/sfx_library}
.venv/bin/python seed_library.py   # minimal ledgered seed set
.venv/bin/python sfx_index_build.py
```

## CLIs

| Tool | Role |
|------|------|
| `analyze_audio.py` | QA metrics + waveform/mel PNG; exit 0/1/2 |
| `seed_library.py` | Ledgered procedural seed library |
| `freesound_fetch.py` | CC0 Freesound fetch (needs `FREESOUND_TOKEN`) |
| `sfx_index_build.py` | BM25 index over ledger |
| `sfx_search.py` | Hard license filter + rank |
| `sfx_generate.py` | Fail-closed gen wrapper (Stable Audio parked) |
| `assemble_sfx.py` | Deterministic layer assemble + variants + QA |
| `render_audition_report.py` | HTML/MD audition artifact |
| `voice_timing.py` | Guide wav → event map (skill: off by default) |

## Tests

```bash
.venv/bin/python -m pytest tests/test_sfx_pipeline.py -v
```

Tests drive the real CLIs and assert non-empty wavs + metrics (no mocks of the units under test).
