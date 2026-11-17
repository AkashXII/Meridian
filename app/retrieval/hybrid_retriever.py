from typing import List, Optional

from sentence_transformers import CrossEncoder

from app.retrieval.keyword_store import query_keyword_store
from app.retrieval.vector_store import query_vector_store

_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder("BAAI/bge-reranker-base")
    return _reranker


def hybrid_search(
    vector_store,
    keyword_store,
    query: str,
    top_k: int = 3,
    claim_types: Optional[List[str]] = None,
) -> list[dict]:
    """Vector top-5 + BM25 top-5, deduplicated, reranked by the cross-encoder.

    claim_types (see app.retrieval.scope) restricts both retrievers to those
    corpus slices; None searches the whole corpus.
    """
    candidates = {}
    hits = query_vector_store(vector_store, query, k=5, claim_types=claim_types) + \
        query_keyword_store(keyword_store, query, k=5, claim_types=claim_types)
    for hit in hits:
        candidates[hit["doc_id"]] = hit

    if not candidates:
        return []

    reranker = get_reranker()
    pairs = [(query, c["text"]) for c in candidates.values()]
    scores = reranker.predict(pairs)

    reranked = sorted(zip(candidates.values(), scores), key=lambda p: p[1], reverse=True)
    return [{**c, "rerank_score": float(s)} for c, s in reranked[:top_k]]
