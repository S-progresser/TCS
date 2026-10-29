from __future__ import annotations

import json
from pathlib import Path

from rank_bm25 import BM25Okapi

from backend.app.schemas import KnowledgeChunk, PolicyRule, RetrievalResult

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _load_json(path: str):
    full_path = DATA_DIR / path
    with full_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_claims() -> list[dict]:
    return _load_json("claims.json")


def load_rulebooks() -> list[PolicyRule]:
    raw = _load_json("rulebooks.json")
    return [PolicyRule(**entry) for entry in raw]


def load_sources() -> list[dict]:
    return _load_json("sources.json")


def load_kb_chunks() -> list[KnowledgeChunk]:
    raw = _load_json("kb_chunks.json")
    return [KnowledgeChunk(**entry) for entry in raw]


def retrieve_guidance(query: str, *, limit: int = 3) -> list[RetrievalResult]:
    docs = load_kb_chunks()
    corpus = [doc.text.lower().split() for doc in docs]
    bm25 = BM25Okapi(corpus)
    tokens = query.lower().split()
    scores = bm25.get_scores(tokens)
    ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
    results: list[RetrievalResult] = []
    for index, score in ranked[:limit]:
        if score <= 0:
            continue
        doc = docs[index]
        results.append(
            RetrievalResult(
                title=doc.title,
                snippet=doc.text[:180],
                source=doc.source,
                score=round(float(score), 2),
            )
        )
    return results
