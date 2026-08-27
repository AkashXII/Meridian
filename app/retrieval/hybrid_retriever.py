
from sentence_transformers import CrossEncoder

from app.retrieval.keyword_store import query_keyword_store
from app.retrieval.vector_store import query_vector_store

_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:

        _reranker = CrossEncoder("BAAI/bge-reranker-base")
    return _reranker


def hybrid_search(vector_store, keyword_store, query: str, top_k: int = 3) -> list[dict]:
    candidates = {}
    for hit in query_vector_store(vector_store, query, k=5) + query_keyword_store(keyword_store, query, k=5):
        candidates[hit["doc_id"]] = hit  

    reranker = get_reranker()
    pairs = [(query, c["text"]) for c in candidates.values()]
    scores = reranker.predict(pairs)

    reranked = sorted(zip(candidates.values(), scores), key=lambda p: p[1], reverse=True)
    return [{**c, "rerank_score": float(s)} for c, s in reranked[:top_k]]