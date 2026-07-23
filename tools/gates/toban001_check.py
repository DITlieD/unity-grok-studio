#!/usr/bin/env python3
"""toban001_check.py - the TOBAN001 banned-Unity-API static analyzer (AOR U-10 / AOR-D10).

A Layer-2 static, regex-unsound, necessary-not-sufficient gate leg for the Unity pack: it
scans the changeset C# (.cs) files for a frozen denylist of Unity APIs banned in production
game code because they are slow, leak, freeze the editor, or are a determinism / allocation
hazard (the Unity analog of the Rust .unwrap() / Python except:pass bans). The load-bearing
runtime proof for the Unity pack stays the auditor-driven EditMode/PlayMode run_tests
(AOR-D10); this analyzer is the cheap static floor the orchestrator runs off-agent.

FAIL-CLOSED (wiring-enforcement R1): any banned-API hit on a real source line is a BLOCK
(exit 1); a --files list naming a path that does not exist is a config error (exit 2) so a
dead-evidence path screams rather than silently passing (R2).

The denylist is a frozen named-constant table (the gate is frozen in gate-manifest.txt, R8)
so an executing run cannot quietly weaken it. An in-code TOBAN-ALLOW[<code>] marker on the
hit line or the line above downgrades that one hit to INFO (the Unity analog of WIRE-DARK).

CLI:
  toban001_check.py --files a.cs,b.cs [--json]
  toban001_check.py --root <dir> [--json]
Exit: 0 clean (or no .cs to judge), 1 a banned-API BLOCK, 2 scan-config error (fail-closed).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_RULES: tuple[tuple[str, "re.Pattern[str]", str, str], ...] = (
    ("TOBAN001", re.compile(r"\bGameObject\.Find\s*\("),
     "GameObject.Find is an O(n) scene scan; cache the reference or inject it", "BLOCK"),
    ("TOBAN002", re.compile(r"\bFindObjectsOfType\s*[(<]|\bFindObjectOfType\s*[(<]"),
     "FindObjectsOfType scans every object every call; cache or use a registry", "BLOCK"),
    ("TOBAN003", re.compile(r"\bCamera\.main\b"),
     "Camera.main does a tagged Find each access; cache the Camera reference", "WARN"),
    ("TOBAN004", re.compile(r"\bResources\.Load\s*\("),
     "Resources.Load is a sync disk hit + a deprecated content path; use Addressables/refs", "WARN"),
    ("TOBAN005", re.compile(r"\bDateTime\.Now\b"),
     "DateTime.Now is non-deterministic + locale-bound; use Time.time / a seeded clock", "BLOCK"),
    ("TOBAN006", re.compile(r"\bThread\.Sleep\s*\("),
     "Thread.Sleep freezes the main thread / editor; use a coroutine or async/await", "BLOCK"),
    ("TOBAN007", re.compile(r"\bDestroy\s*\(\s*this\s*\)\s*;\s*\w"),
     "code after Destroy(this) runs on a torn-down object; return after Destroy", "WARN"),
    ("TOBAN008", re.compile(r"\bDebug\.Log\s*\([^)]*\+[^)]*\)"),
     "Debug.Log with string concat allocates every call even when stripped; guard it", "WARN"),
)

_ALLOW_RE = re.compile(r"//\s*TOBAN-ALLOW\[(?P<code>TOBAN\d+)\]")

# The Unity production .cs file-size cap (AOR 9.5; tighter than the generic 1000-line
# maintainability boundary, and enforced here because the frozen maintainability_check.py
# does not scan .cs). A .cs over this is a BLOCK (split the MonoBehaviour / extract a helper).
_CS_MAX_LINES = 600


def _scan_text(text: str, path: str) -> list[dict]:
    """Return the finding dicts for one file source text."""
    lines = text.splitlines()
    findings: list[dict] = []
    if len(lines) > _CS_MAX_LINES and not _ALLOW_RE.search(text):
        findings.append({
            "code": "TOBAN-FILESIZE",
            "file": path,
            "line": len(lines),
            "reason": f".cs file is {len(lines)} lines (> the {_CS_MAX_LINES}-line Unity prod "
                      "cap, AOR 9.5); split the MonoBehaviour or extract a helper",
            "severity": "BLOCK",
            "snippet": "",
        })
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        for code, pattern, reason, severity in _RULES:
            if pattern.search(line):
                prev = lines[idx - 1] if idx > 0 else ""
                allowed = any(
                    m.group("code") == code for m in _ALLOW_RE.finditer(line + "\n" + prev)
                )
                findings.append({
                    "code": code,
                    "file": path,
                    "line": idx + 1,
                    "reason": reason,
                    "severity": "INFO" if allowed else severity,
                    "snippet": line.strip()[:160],
                })
    return findings


def scan_files(files: list[Path]) -> tuple[list[dict], list[str]]:
    """Scan an explicit file list. Returns (findings, missing_paths)."""
    findings: list[dict] = []
    missing: list[str] = []
    for f in files:
        if not f.exists():
            missing.append(str(f))
            continue
        if f.suffix != ".cs":
            continue
        try:
            findings.extend(_scan_text(f.read_text(encoding="utf-8", errors="replace"), str(f)))
        except OSError as exc:
            missing.append(f"{f}: {exc}")
    return findings, missing


def scan_root(root: Path) -> tuple[list[dict], list[str]]:
    """Scan every .cs under a directory root."""
    if not root.is_dir():
        return [], [str(root)]
    return scan_files(sorted(root.rglob("*.cs")))


def _split_csv(value: str | None) -> list[str]:
    return [x.strip() for x in (value or "").split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TOBAN001 banned-Unity-API analyzer (AOR U-10)")
    ap.add_argument("--files", default=None, help="comma-separated .cs files to scan")
    ap.add_argument("--root", default=None, help="scan every .cs under this dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if not args.files and not args.root:
        print("TOBAN_CONFIG_ERROR: one of --files / --root is required", file=sys.stderr)
        return 2

    if args.files:
        findings, missing = scan_files([Path(p) for p in _split_csv(args.files)])
    else:
        findings, missing = scan_root(Path(args.root))

    if missing:
        print("TOBAN_CONFIG_ERROR: missing/unreadable paths: " + ", ".join(missing), file=sys.stderr)
        if args.json:
            print(json.dumps({"verdict": "ERROR", "missing": missing}, indent=2))
        return 2

    blocking = [f for f in findings if f["severity"] == "BLOCK"]
    verdict = "BLOCK" if blocking else "PASS"
    if args.json:
        print(json.dumps({"verdict": verdict, "findings": findings,
                          "block_count": len(blocking)}, indent=2, sort_keys=True))
    else:
        for f in findings:
            print(f"{f['severity']} {f['code']} {f['file']}:{f['line']} - {f['reason']}")
        print(f"TOBAN001: {verdict} ({len(blocking)} blocking, {len(findings)} total)")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
