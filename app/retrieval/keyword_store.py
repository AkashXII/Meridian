"""
Keyword search over the same documents using BM25 — catches exact terms
(e.g. "flood", "H-") that embedding similarity can blur past.
"""
from rank_bm25 import BM25Okapi


def build_keyword_store(docs: list[dict]):
    tokenized = [d["text"].lower().split() for d in docs]
    return {"bm25": BM25Okapi(tokenized), "docs": docs}


def query_keyword_store(store, query: str, k: int = 3) -> list[dict]:
    bm25, docs = store["bm25"], store["docs"]
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(zip(docs, scores), key=lambda pair: pair[1], reverse=True)
    return [
        {"doc_id": d["doc_id"], "text": d["text"], "claim_type": d["claim_type"],
         "title": d["title"], "score": float(s)}
        for d, s in ranked[:k]
    ]