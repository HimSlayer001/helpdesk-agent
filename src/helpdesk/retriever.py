"""Keyword (BM25), embedding and hybrid (Reciprocal Rank Fusion) retrieval over KB chunks."""
from __future__ import annotations

import re
from typing import Callable, Sequence

import numpy as np
from rank_bm25 import BM25Okapi

from .kb import Chunk

STOP = set("a an and are as at be by can do does for from how i in is it my of on or the to what when where which with you your".split())


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


class BM25Retriever:
    name = "bm25"

    def __init__(self, chunks: Sequence[Chunk]):
        self.chunks = list(chunks)
        self.bm25 = BM25Okapi([tokenize(c.text) for c in self.chunks])

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        scores = self.bm25.get_scores(tokenize(query))
        order = np.argsort(-scores)[:k]
        return [(self.chunks[i], float(scores[i])) for i in order]


class DenseRetriever:
    """Cosine similarity over embeddings from any `embed(list[str]) -> list[list[float]]` function."""
    name = "dense"

    def __init__(self, chunks: Sequence[Chunk], embed: Callable[[list[str]], list[list[float]]]):
        self.chunks = list(chunks)
        self.embed = embed
        m = np.asarray(embed([c.text for c in self.chunks]), dtype=np.float32)
        self.matrix = m / np.linalg.norm(m, axis=1, keepdims=True)

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        q = np.asarray(self.embed([query])[0], dtype=np.float32)
        q /= np.linalg.norm(q)
        sims = self.matrix @ q
        order = np.argsort(-sims)[:k]
        return [(self.chunks[i], float(sims[i])) for i in order]


def rrf(rankings: Sequence[Sequence[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


class HybridRetriever:
    """Fuses BM25 and dense rankings: exact terms (error messages, tool names) plus paraphrase."""
    name = "hybrid"

    def __init__(self, bm25: BM25Retriever, dense: DenseRetriever, depth: int = 10):
        self.bm25, self.dense, self.depth = bm25, dense, depth
        self.by_id = {c.id: c for c in bm25.chunks}

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        lists = [[c.id for c, _ in r.search(query, self.depth)] for r in (self.bm25, self.dense)]
        return [(self.by_id[cid], s) for cid, s in rrf(lists)[:k]]
