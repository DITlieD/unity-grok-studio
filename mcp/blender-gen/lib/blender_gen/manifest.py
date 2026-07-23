"""Artifact manifest writer (seed, params, versions)."""
from __future__ import annotations

import json
import platform
import time
from pathlib import Path
from typing import Any

from . import __version__


def write_manifest(
    out_dir: Path,
    *,
    seed: int,
    kind: str,
    params: dict[str, Any],
    files: list[str],
    extra: dict[str, Any] | None = None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "kind": kind,
        "seed": int(seed),
        "params": params,
        "files": files,
        "versions": {
            "blender_gen": __version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "created_unix": time.time(),
    }
    if extra:
        doc.update(extra)
    path = out_dir / "manifest.json"
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
