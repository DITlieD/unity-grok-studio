#!/usr/bin/env python3
"""Render audition report (HTML) for a family: metrics, spectrograms, lineage.

Does NOT claim audio quality — measurements + evidence + verdict slot only.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.metrics import load_audio
from lib.spectrogram import render_waveform_mel_png
from sfx_manifest import load_manifest


def render_report(
    family_dir: Path,
    out_path: Path | None = None,
    compare_path: Path | None = None,
) -> Path:
    family_dir = Path(family_dir)
    man_path = family_dir / "manifest.json"
    if not man_path.exists():
        raise FileNotFoundError(f"no manifest.json in {family_dir}")
    man = load_manifest(man_path)
    report_dir = out_path.parent if out_path else family_dir / "report"
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_path or (report_dir / "audition_report.html")

    rows_html = []
    for o in man.get("outputs", []):
        if o.get("role") == "stem":
            continue
        m = o.get("metrics") or {}
        png = None
        p = Path(o["path"])
        if p.exists():
            png = report_dir / f"{p.stem}.qa.png"
            try:
                data, sr, _ = load_audio(p)
                render_waveform_mel_png(data, sr, png, title=p.name)
            except Exception:
                png = None
        qa = o.get("qa_pass")
        qa_s = "PASS" if qa else ("FAIL" if qa is False else "n/a")
        img = (
            f'<img src="{html.escape(png.name)}" alt="spec" style="max-width:480px"/>'
            if png and png.exists()
            else ""
        )
        rows_html.append(
            f"""
            <tr>
              <td>{html.escape(o.get('name',''))}</td>
              <td>{html.escape(o.get('role',''))}</td>
              <td>{qa_s}</td>
              <td>{m.get('duration_s', '')}</td>
              <td>{m.get('peak_dbfs', '')}</td>
              <td>{m.get('integrated_lufs', '')}</td>
              <td>{m.get('onset_count', '')}</td>
              <td><a href="file://{html.escape(o.get('path',''))}">{html.escape(o.get('path',''))}</a></td>
            </tr>
            <tr><td colspan="8">{img}</td></tr>
            """
        )

    layers_html = []
    for L in man.get("layers", []):
        layers_html.append(
            f"<li><b>{html.escape(str(L.get('role')))}</b> "
            f"license={html.escape(str(L.get('license')))} "
            f"src={html.escape(str(L.get('source')))} "
            f"gain={L.get('gain_db')}dB pitch={L.get('pitch_cents')}c</li>"
        )

    compare_html = ""
    if compare_path and Path(compare_path).exists():
        cp = Path(compare_path)
        cpng = report_dir / f"compare_old_{cp.stem}.qa.png"
        try:
            data, sr, _ = load_audio(cp)
            render_waveform_mel_png(data, sr, cpng, title=f"OLD {cp.name}")
            compare_html = f"""
            <h2>Old vs new (reference clip)</h2>
            <p>Reference only — no quality claim.</p>
            <img src="{html.escape(cpng.name)}" style="max-width:640px"/>
            <p>file://{html.escape(str(cp.resolve()))}</p>
            """
        except Exception as e:
            compare_html = f"<p>compare render failed: {html.escape(str(e))}</p>"

    doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<title>Audition: {html.escape(man.get('name',''))}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 1.5rem; background: #111; color: #eee; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 1rem; }}
th, td {{ border: 1px solid #444; padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }}
th {{ background: #222; }}
.verdict {{ border: 2px dashed #888; padding: 1rem; margin-top: 2rem; }}
a {{ color: #8cf; }}
.note {{ color: #aaa; font-size: 0.9rem; }}
</style></head><body>
<h1>Audition report: {html.escape(man.get('name',''))}</h1>
<p class="note">Measurements and lineage only. The agent NEVER declares audio done —
human verdict in the slot below is the done-gate.</p>
<ul>
<li>seed: {html.escape(str(man.get('seed')))}</li>
<li>created: {html.escape(str(man.get('created')))}</li>
<li>plan: {html.escape(str(man.get('plan_path')))}</li>
<li>outputs: {man.get('output_count')}</li>
</ul>
<h2>Layer lineage</h2>
<ul>
{''.join(layers_html)}
</ul>
<h2>Variants / master (summary)</h2>
<table>
<tr><th>name</th><th>role</th><th>QA</th><th>dur</th><th>peak dBFS</th><th>LUFS</th><th>onsets</th><th>path</th></tr>
{''.join(rows_html)}
</table>
{compare_html}
<div class="verdict">
<h2>Verdict slot (human)</h2>
<p>approve / reject / notes — fill by owner:</p>
<pre>
VERDICT:
NOTES:
</pre>
</div>
</body></html>
"""
    out_path.write_text(doc, encoding="utf-8")
    # also md summary
    md_path = out_path.with_suffix(".md")
    md_lines = [
        f"# Audition: {man.get('name')}",
        "",
        "Measurements + lineage only. No quality claims.",
        "",
        f"- seed: {man.get('seed')}",
        f"- outputs: {man.get('output_count')}",
        "",
        "## Layers",
    ]
    for L in man.get("layers", []):
        md_lines.append(
            f"- **{L.get('role')}** license=`{L.get('license')}` src=`{L.get('source')}`"
        )
    md_lines += ["", "## Outputs", ""]
    for o in man.get("outputs", []):
        if o.get("role") == "stem":
            continue
        m = o.get("metrics") or {}
        md_lines.append(
            f"- {o.get('name')} ({o.get('role')}) QA={o.get('qa_pass')} "
            f"dur={m.get('duration_s')} peak={m.get('peak_dbfs')}"
        )
    md_lines += ["", "## Verdict slot", "", "VERDICT:", "NOTES:", ""]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family-dir", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--compare", default=None, help="old wav for side-by-side strip")
    args = ap.parse_args(argv)
    try:
        path = render_report(
            Path(args.family_dir),
            Path(args.out) if args.out else None,
            Path(args.compare) if args.compare else None,
        )
    except Exception as e:
        print(json.dumps({"pass": False, "error": str(e)}), file=sys.stderr)
        return 1
    print(json.dumps({"pass": True, "report": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
