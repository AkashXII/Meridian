from typing import List, Optional

from rank_bm25 import BM25Okapi


def build_keyword_store(docs: list[dict]):
    tokenized = [d["text"].lower().split() for d in docs]
    return {"bm25": BM25Okapi(tokenized), "docs": docs}


def query_keyword_store(
    store, query: str, k: int = 3, claim_types: Optional[List[str]] = None
) -> list[dict]:
    """claim_types, if given, keeps only chunks of those types. BM25 is still
    scored over the whole corpus (so IDF weights are unchanged) and the
    filter is applied before taking the top k."""
    bm25, docs = store["bm25"], store["docs"]
    scores = bm25.get_scores(query.lower().split())
    pairs = zip(docs, scores)
    if claim_types:
        allowed = set(claim_types)
        pairs = [(d, s) for d, s in pairs if d["claim_type"] in allowed]
    ranked = sorted(pairs, key=lambda pair: pair[1], reverse=True)
    return [
        {"doc_id": d["doc_id"], "text": d["text"], "claim_type": d["claim_type"],
         "title": d["title"], "score": float(s)}
        for d, s in ranked[:k]
    ]
