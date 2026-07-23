#!/usr/bin/env python3
"""mono_wire_census.py - the MonoBehaviour-attachment wire census (AOR U-10 / AOR-D10).

The Unity analog of python_wire_check / production_caller_check: a NEW MonoBehaviour (a C#
class deriving from MonoBehaviour or ScriptableObject) that is attached to NO GameObject /
prefab / scene AND referenced by no other script is WIRE-DARK -- the Unity producer-without-
consumer failure (wiring-enforcement R6/R7). A script you can never reach at runtime is the
exact "compiles + unit-test-green but never wired" defect the gate exists to catch, expressed
for a stack with no instrumentable binary.

How "wired" is proven (Layer-2 static, regex-unsound, necessary-not-sufficient; the
load-bearing backstop stays the auditor-driven PlayMode run_tests, AOR-D10):
  WIRED if the class's GUID (from its .cs.meta) appears as an m_Script fileID/guid reference
    in ANY .unity / .prefab / .asset YAML under the project (it is attached to something), OR
  WIRED if the class name is referenced by another .cs file outside its own (AddComponent<T>,
    a typed field, GetComponent<T>, a [SerializeField] of that type, etc.), OR
  REGISTERED-DARK if a // WIRE-DARK[<id>] marker sits on the line above the class def.
  Else DARK -> BLOCK (exit 1).

Inputs:
  --new-files a.cs,b.cs   the NEW .cs files this changeset added (the producers to judge)
  --project <dir>         the Unity project root to scan for attachments + references
  --meta-dir <dir>        optional: where .cs.meta files live (default: alongside the .cs)
  [--json]
FAIL-CLOSED (R1/R2): a --new-files path that does not exist, or a --project that is not a dir,
is a config error (exit 2); a real DARK MonoBehaviour is a BLOCK (exit 1). A changeset whose
new .cs files contain no MonoBehaviour/ScriptableObject is exit 0 (nothing to judge).

Exit: 0 all wired / nothing to judge, 1 a DARK MonoBehaviour (BLOCK), 2 scan-config error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# A class deriving (directly) from a Unity component base that MUST be attached/referenced.
_CLASS_RE = re.compile(
    r"^\s*(?:public\s+|internal\s+|sealed\s+|abstract\s+|partial\s+)*class\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*:\s*(?P<bases>[^{]+)"
)
_UNITY_BASES = ("MonoBehaviour", "ScriptableObject", "StateMachineBehaviour")
# A .cs.meta guid line: "guid: 0123456789abcdef0123456789abcdef"
_GUID_RE = re.compile(r"^guid:\s*([0-9a-fA-F]{32})\s*$", re.MULTILINE)
# A WIRE-DARK escape on the line above the class def.
_WIREDARK_RE = re.compile(r"//\s*WIRE-DARK\[(?P<id>[^\]]+)\]")


def _find_mono_classes(cs_path: Path) -> list[dict]:
    """Find MonoBehaviour/ScriptableObject classes defined in one .cs file."""
    try:
        text = cs_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    out: list[dict] = []
    for idx, line in enumerate(lines):
        m = _CLASS_RE.match(line)
        if not m:
            continue
        bases = m.group("bases")
        if not any(b in bases for b in _UNITY_BASES):
            continue
        prev = lines[idx - 1] if idx > 0 else ""
        dark = _WIREDARK_RE.search(prev)
        out.append({
            "name": m.group("name"),
            "file": str(cs_path),
            "line": idx + 1,
            "wire_dark_marker": dark.group("id") if dark else None,
        })
    return out


def _class_guid(cs_path: Path, meta_dir: Path | None) -> str | None:
    """Read the GUID Unity assigned this script from its .cs.meta sidecar."""
    meta = (meta_dir / (cs_path.name + ".meta")) if meta_dir else cs_path.with_suffix(".cs.meta")
    if not meta.exists():
        return None
    m = _GUID_RE.search(meta.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def _guid_attached(project: Path, guid: str) -> bool:
    """True if the GUID appears as a script reference in any scene/prefab/asset YAML."""
    if not guid:
        return False
    needle = guid
    for ext in ("*.unity", "*.prefab", "*.asset"):
        for yaml in project.rglob(ext):
            try:
                if needle in yaml.read_text(encoding="utf-8", errors="replace"):
                    return True
            except OSError:
                continue
    return False


def _name_referenced(project: Path, name: str, own_file: Path) -> bool:
    """True if the class name is referenced by another .cs file (AddComponent<T>, a typed
    field, GetComponent<T>, etc.) -- a word-boundary match outside its own defining file."""
    word = re.compile(r"\b" + re.escape(name) + r"\b")
    own = own_file.resolve()
    for cs in project.rglob("*.cs"):
        if cs.resolve() == own:
            continue
        try:
            text = cs.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Strip the (rare) case where the name only appears in its own re-declaration.
        if word.search(text):
            return True
    return False


def census(new_files: list[Path], project: Path, meta_dir: Path | None) -> dict:
    """Run the wire census over the new .cs files. Returns a verdict dict."""
    results: list[dict] = []
    for cs in new_files:
        for cls in _find_mono_classes(cs):
            if cls["wire_dark_marker"]:
                verdict = "REGISTERED-DARK"
            else:
                guid = _class_guid(cs, meta_dir)
                attached = _guid_attached(project, guid) if guid else False
                referenced = _name_referenced(project, cls["name"], cs)
                if attached:
                    verdict = "WIRED-ATTACHED"
                elif referenced:
                    verdict = "WIRED-REFERENCED"
                else:
                    verdict = "DARK"
                cls["guid"] = guid
            cls["verdict"] = verdict
            results.append(cls)
    dark = [r for r in results if r["verdict"] == "DARK"]
    return {"verdict": "BLOCK" if dark else "PASS", "results": results, "dark_count": len(dark)}


def _split_csv(value: str | None) -> list[str]:
    return [x.strip() for x in (value or "").split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MonoBehaviour-attachment wire census (AOR U-10)")
    ap.add_argument("--new-files", required=True, help="comma-separated NEW .cs files to judge")
    ap.add_argument("--project", required=True, help="Unity project root to scan")
    ap.add_argument("--meta-dir", default=None, help="where .cs.meta files live (default: beside the .cs)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    project = Path(args.project)
    if not project.is_dir():
        print(f"MONOWIRE_CONFIG_ERROR: project not a dir: {project}", file=sys.stderr)
        return 2
    files: list[Path] = []
    for p in _split_csv(args.new_files):
        path = Path(p)
        if not path.exists():
            print(f"MONOWIRE_CONFIG_ERROR: missing new-file: {path}", file=sys.stderr)
            return 2
        if path.suffix == ".cs":
            files.append(path)
    meta_dir = Path(args.meta_dir) if args.meta_dir else None

    result = census(files, project, meta_dir)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for r in result["results"]:
            print(f"{r['verdict']} {r['name']} {r['file']}:{r['line']}")
        print(f"mono_wire_census: {result['verdict']} ({result['dark_count']} dark)")
    return 1 if result["verdict"] == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
