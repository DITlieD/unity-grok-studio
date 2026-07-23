#!/usr/bin/env python3
"""Family manifest linking every output to layer sources/licenses/seeds."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class OutputRow:
    name: str
    path: str
    role: str  # master | variant | stem
    sha256: str = ""
    qa_pass: bool | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class LayerProvenance:
    role: str
    source: str
    license: str = ""
    gain_db: float = 0.0
    pitch_cents: float = 0.0
    offset_ms: float = 0.0


@dataclass
class FamilyManifest:
    name: str
    seed: int
    plan_path: str
    created: str
    layers: list[LayerProvenance] = field(default_factory=list)
    outputs: list[OutputRow] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "seed": self.seed,
            "plan_path": self.plan_path,
            "created": self.created,
            "layers": [asdict(x) for x in self.layers],
            "outputs": [asdict(x) for x in self.outputs],
            "notes": self.notes,
            "output_count": len(self.outputs),
        }

    def write(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path


def new_manifest(name: str, seed: int, plan_path: str) -> FamilyManifest:
    return FamilyManifest(
        name=name,
        seed=seed,
        plan_path=str(plan_path),
        created=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def load_manifest(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
