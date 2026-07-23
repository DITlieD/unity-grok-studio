#!/usr/bin/env python3
"""Build BM25 metadata index over ledgered wavs (CLAP fallback path).

Stores sqlite at SFX_LIB/index.db. Only ledgered files are indexed.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.bm25 import BM25Index, build_doc_text
from lib.ledger import read_ledger, resolve_ledger_abs
from lib.paths import resolve_sfx_lib, is_quarantine_path


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS docs (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            abs_path TEXT NOT NULL,
            license TEXT,
            category TEXT,
            tags TEXT,
            duration_s REAL,
            sample_rate INTEGER,
            channels INTEGER,
            ucs_name TEXT,
            original_name TEXT,
            source TEXT,
            mtime REAL,
            doc_text TEXT
        )
        """
    )
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn


def build_index(sfx_lib: Path, db_path: Path | None = None) -> int:
    sfx_lib = Path(sfx_lib).resolve()
    db_path = db_path or (sfx_lib / "index.db")
    rows = read_ledger(sfx_lib)
    conn = open_db(db_path)
    conn.execute("DELETE FROM docs")
    n = 0
    for row in rows:
        abs_p = resolve_ledger_abs(sfx_lib, row)
        if not abs_p.exists():
            continue
        if is_quarantine_path(abs_p, sfx_lib):
            continue
        meta = {
            "path": row.path,
            "abs_path": str(abs_p),
            "license": row.license,
            "category": row.category,
            "tags": row.tags,
            "duration_s": row.duration_s,
            "sample_rate": row.sample_rate,
            "channels": row.channels,
            "ucs_name": row.ucs_name,
            "original_name": row.original_name,
            "source": row.source,
        }
        text = build_doc_text(meta)
        mtime = abs_p.stat().st_mtime
        conn.execute(
            """
            INSERT OR REPLACE INTO docs
            (path, abs_path, license, category, tags, duration_s, sample_rate,
             channels, ucs_name, original_name, source, mtime, doc_text)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                row.path,
                str(abs_p),
                row.license,
                row.category,
                row.tags,
                row.duration_s,
                row.sample_rate,
                row.channels,
                row.ucs_name,
                row.original_name,
                row.source,
                mtime,
                text,
            ),
        )
        n += 1
    conn.execute(
        "INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
        ("backend", "bm25"),
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
        ("row_count", str(n)),
    )
    conn.commit()
    conn.close()
    return n


def load_bm25_from_db(db_path: Path) -> BM25Index:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    idx = BM25Index()
    for r in conn.execute("SELECT * FROM docs"):
        meta = dict(r)
        idx.add(meta.get("doc_text") or "", meta)
    idx.finalize()
    conn.close()
    return idx


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sfx-lib", default=None)
    ap.add_argument("--db", default=None)
    args = ap.parse_args(argv)
    lib = resolve_sfx_lib(args.sfx_lib)
    db = Path(args.db) if args.db else lib / "index.db"
    n = build_index(lib, db)
    ledger_n = len(read_ledger(lib))
    print(json.dumps({"indexed": n, "ledger_rows": ledger_n, "db": str(db)}, indent=2))
    if n == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
