#!/usr/bin/env python3
"""unity_symbol_census.py - the verify-before-write symbol census (AOR U-10 / AOR-D9).

Unity's API surface drifts across versions (renamed enums, signature changes, deprecated
overloads), so the Unity executor follows verify-before-write: before using a version-
sensitive symbol it must clear a verify-tier check via unity_reflect / unity_docs and record
a RECEIPT. This gate is the off-agent enforcement: it scans the changeset C# files for any
symbol on the frozen policy denylist (unity-symbol-policy.json) and FAILS when a deny-tier
symbol is used with NO matching receipt in the session ledger.

This is the static, fail-closed companion to AOR-D9 (the executor profile bakes the
verify-before-write discipline; this gate proves the receipt exists). It is regex-unsound
(name-grep, not a type resolver) and necessary-not-sufficient -- the runtime backstop stays
the auditor-driven run_tests (AOR-D10).

Policy file (unity-symbol-policy.json) shape:
  {
    "version": 1,
    "symbols": [
      {"symbol": "FindObjectsByType", "tier": "deny",
       "reason": "added in 2022.2; absent on older LTS -- verify the target Unity version"},
      {"symbol": "InputSystem", "tier": "verify",
       "reason": "the new Input System package may not be installed -- verify before use"}
    ]
  }
tier "deny"   -> a use WITHOUT a receipt is a BLOCK.
tier "verify" -> a use WITHOUT a receipt is a WARN (surfaced, non-blocking).

A receipt clears a symbol: a // UNITY-VERIFY[<symbol>] marker in the changed source, OR a
line "<symbol>" in the session receipt ledger file (--receipts PATH, one symbol per line).

CLI:
  unity_symbol_census.py --files a.cs,b.cs --policy unity-symbol-policy.json
                         [--receipts ledger.txt] [--json]
FAIL-CLOSED (R1/R2): a missing policy file, or a --files path that does not exist, is a config
error (exit 2); a deny-tier symbol used with no receipt is a BLOCK (exit 1).
Exit: 0 clean, 1 a deny-tier symbol with no receipt (BLOCK), 2 scan-config error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_RECEIPT_MARKER = re.compile(r"//\s*UNITY-VERIFY\[(?P<symbol>[^\]]+)\]")


def _load_policy(policy_path: Path) -> list[dict]:
    """Load + validate the symbol policy (fail-closed on a malformed file)."""
    data = json.loads(policy_path.read_text(encoding="utf-8"))
    symbols = data.get("symbols")
    if not isinstance(symbols, list):
        raise ValueError("policy file has no 'symbols' list")
    out: list[dict] = []
    for row in symbols:
        sym = str(row.get("symbol", "")).strip()
        tier = str(row.get("tier", "")).strip()
        if not sym or tier not in ("deny", "verify"):
            raise ValueError(f"bad policy row: {row!r}")
        out.append({"symbol": sym, "tier": tier, "reason": str(row.get("reason", ""))})
    return out


def _collect_receipts(files_text: dict[str, str], receipts_path: Path | None) -> set[str]:
    """The set of symbols that have a verification receipt (in-code marker or ledger)."""
    receipts: set[str] = set()
    for text in files_text.values():
        for m in _RECEIPT_MARKER.finditer(text):
            receipts.add(m.group("symbol").strip())
    if receipts_path and receipts_path.exists():
        for line in receipts_path.read_text(encoding="utf-8", errors="replace").splitlines():
            tok = line.strip()
            if tok and not tok.startswith("#"):
                receipts.add(tok)
    return receipts


def census(files_text: dict[str, str], policy: list[dict], receipts: set[str]) -> dict:
    """Scan each file for policy symbols used without a receipt."""
    findings: list[dict] = []
    for path, text in files_text.items():
        # Strip comment-only lines so a symbol named in a comment is not a use.
        body = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("//"))
        for row in policy:
            sym = row["symbol"]
            if re.search(r"\b" + re.escape(sym) + r"\b", body) and sym not in receipts:
                findings.append({
                    "symbol": sym, "tier": row["tier"], "file": path,
                    "reason": row["reason"],
                    "severity": "BLOCK" if row["tier"] == "deny" else "WARN",
                })
    blocking = [f for f in findings if f["severity"] == "BLOCK"]
    return {"verdict": "BLOCK" if blocking else "PASS", "findings": findings,
            "block_count": len(blocking)}


def _split_csv(value: str | None) -> list[str]:
    return [x.strip() for x in (value or "").split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Unity verify-before-write symbol census (AOR U-10)")
    ap.add_argument("--files", required=True, help="comma-separated .cs files to scan")
    ap.add_argument("--policy", required=True, help="unity-symbol-policy.json path")
    ap.add_argument("--receipts", default=None, help="session receipt ledger (one symbol/line)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    policy_path = Path(args.policy)
    if not policy_path.is_file():
        print(f"SYMCENSUS_CONFIG_ERROR: missing policy file: {policy_path}", file=sys.stderr)
        return 2
    try:
        policy = _load_policy(policy_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"SYMCENSUS_CONFIG_ERROR: bad policy: {exc}", file=sys.stderr)
        return 2

    files_text: dict[str, str] = {}
    for p in _split_csv(args.files):
        path = Path(p)
        if not path.exists():
            print(f"SYMCENSUS_CONFIG_ERROR: missing file: {path}", file=sys.stderr)
            return 2
        if path.suffix == ".cs":
            files_text[str(path)] = path.read_text(encoding="utf-8", errors="replace")

    receipts = _collect_receipts(files_text, Path(args.receipts) if args.receipts else None)
    result = census(files_text, policy, receipts)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for f in result["findings"]:
            print(f"{f['severity']} {f['symbol']} {f['file']} - {f['reason']}")
        print(f"unity_symbol_census: {result['verdict']} ({result['block_count']} blocking)")
    return 1 if result["verdict"] == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
