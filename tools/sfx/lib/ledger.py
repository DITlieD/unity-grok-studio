"""Provenance ledger for SFX_LIB. License gate lives here structurally."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# Default allowlist for search/assemble
DEFAULT_ALLOWED_LICENSES = frozenset(
    {
        "cc0",
        "cc0-1.0",
        "CC0",
        "CC0-1.0",
        "publicdomain",
        "public-domain",
        "sonniss-gdc",
        "bundle-licensed",
        "studio-seed",  # studio-generated seed layers for pipeline smoke
        "procedural-seed",
    }
)

LEDGER_FIELDS = [
    "path",
    "original_name",
    "ucs_name",
    "license",
    "source",
    "source_id",
    "uploader",
    "url",
    "download_date",
    "duration_s",
    "sample_rate",
    "channels",
    "sha256",
    "tags",
    "category",
]


@dataclass
class LedgerRow:
    path: str  # relative to SFX_LIB or absolute
    original_name: str
    ucs_name: str
    license: str
    source: str
    source_id: str = ""
    uploader: str = ""
    url: str = ""
    download_date: str = ""
    duration_s: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    sha256: str = ""
    tags: str = ""
    category: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def ledger_path(sfx_lib: Path) -> Path:
    return Path(sfx_lib) / "ledger.tsv"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_license(lic: str) -> str:
    return (lic or "").strip().lower().replace(" ", "")


def license_allowed(lic: str, allowed: Iterable[str] | None = None) -> bool:
    allow = {normalize_license(x) for x in (allowed or DEFAULT_ALLOWED_LICENSES)}
    return normalize_license(lic) in allow


def read_ledger(sfx_lib: Path) -> list[LedgerRow]:
    p = ledger_path(sfx_lib)
    if not p.exists():
        return []
    rows: list[LedgerRow] = []
    with open(p, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            if not r.get("path"):
                continue
            rows.append(
                LedgerRow(
                    path=r.get("path", ""),
                    original_name=r.get("original_name", ""),
                    ucs_name=r.get("ucs_name", ""),
                    license=r.get("license", ""),
                    source=r.get("source", ""),
                    source_id=r.get("source_id", ""),
                    uploader=r.get("uploader", ""),
                    url=r.get("url", ""),
                    download_date=r.get("download_date", ""),
                    duration_s=float(r["duration_s"] or 0),
                    sample_rate=int(float(r["sample_rate"] or 0)),
                    channels=int(float(r["channels"] or 0)),
                    sha256=r.get("sha256", ""),
                    tags=r.get("tags", ""),
                    category=r.get("category", ""),
                )
            )
    return rows


def write_ledger(sfx_lib: Path, rows: list[LedgerRow]) -> Path:
    sfx_lib = Path(sfx_lib)
    sfx_lib.mkdir(parents=True, exist_ok=True)
    p = ledger_path(sfx_lib)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS, delimiter="\t")
        w.writeheader()
        for row in rows:
            w.writerow(row.to_dict())
    return p


def append_ledger_row(sfx_lib: Path, row: LedgerRow) -> Path:
    rows = read_ledger(sfx_lib)
    # replace by path if present
    rows = [r for r in rows if r.path != row.path]
    rows.append(row)
    return write_ledger(sfx_lib, rows)


def resolve_ledger_abs(sfx_lib: Path, row: LedgerRow) -> Path:
    p = Path(row.path)
    if p.is_absolute():
        return p
    return (Path(sfx_lib) / p).resolve()


def row_for_path(sfx_lib: Path, wav_path: Path | str) -> LedgerRow | None:
    wav_path = Path(wav_path).resolve()
    sfx_lib = Path(sfx_lib).resolve()
    for row in read_ledger(sfx_lib):
        abs_p = resolve_ledger_abs(sfx_lib, row)
        if abs_p.resolve() == wav_path:
            return row
        # also match relative
        try:
            rel = str(wav_path.relative_to(sfx_lib)).replace("\\", "/")
            if row.path.replace("\\", "/") == rel:
                return row
        except ValueError:
            pass
    return None


def is_ledgered(sfx_lib: Path, wav_path: Path | str) -> bool:
    return row_for_path(sfx_lib, wav_path) is not None


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
