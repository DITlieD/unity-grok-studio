"""Deterministic RNG helpers (stdlib only)."""
from __future__ import annotations

import hashlib
import random
from typing import Sequence


def make_rng(seed: int, *salts: str | int) -> random.Random:
    h = hashlib.sha256()
    h.update(str(int(seed)).encode())
    for s in salts:
        h.update(b"|")
        h.update(str(s).encode())
    # 32-bit seed from digest for Random
    return random.Random(int.from_bytes(h.digest()[:8], "little"))


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
