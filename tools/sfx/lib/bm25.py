"""Minimal BM25 ranker over ledger metadata (CLAP fallback)."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable


_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


@dataclass
class Doc:
    doc_id: int
    tokens: list[str]
    meta: dict


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: list[Doc] = []
        self.df: Counter[str] = Counter()
        self.avgdl = 0.0
        self.N = 0

    def add(self, text: str, meta: dict) -> None:
        toks = tokenize(text)
        doc = Doc(doc_id=len(self.docs), tokens=toks, meta=meta)
        self.docs.append(doc)
        for t in set(toks):
            self.df[t] += 1

    def finalize(self) -> None:
        self.N = len(self.docs)
        if self.N == 0:
            self.avgdl = 0.0
            return
        self.avgdl = sum(len(d.tokens) for d in self.docs) / self.N

    def score(self, query: str, doc: Doc) -> float:
        q = tokenize(query)
        if not q or not doc.tokens:
            return 0.0
        tf = Counter(doc.tokens)
        dl = len(doc.tokens)
        s = 0.0
        for term in q:
            if term not in tf:
                continue
            n_q = self.df.get(term, 0)
            idf = math.log(1.0 + (self.N - n_q + 0.5) / (n_q + 0.5))
            freq = tf[term]
            denom = freq + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1.0))
            s += idf * (freq * (self.k1 + 1)) / (denom or 1.0)
        return s

    def search(self, query: str, top_k: int = 10) -> list[tuple[float, dict]]:
        scored = [(self.score(query, d), d.meta) for d in self.docs]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [(s, m) for s, m in scored[:top_k] if s > 0]


def build_doc_text(meta: dict) -> str:
    parts = [
        meta.get("ucs_name", ""),
        meta.get("original_name", ""),
        meta.get("category", ""),
        meta.get("tags", ""),
        meta.get("path", ""),
        meta.get("source", ""),
    ]
    # split path components
    path = meta.get("path", "")
    parts.extend(path.replace("\\", "/").split("/"))
    parts.extend(path.replace("_", " ").replace("-", " ").split())
    return " ".join(str(p) for p in parts if p)
