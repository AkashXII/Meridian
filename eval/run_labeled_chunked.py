"""
Labeled retrieval eval on the live chunked corpus (48 chunks).

Reproduces the headline labeled number (0.96 recall@3). Compares vector-only,
BM25-only and the production hybrid retriever (vector + BM25 + cross-encoder
rerank) on the same 25 labeled queries.

Recall@3 here is hit-rate: 1 if any relevant chunk appears in the top 3,
else 0, averaged over queries. MRR is the mean of 1/rank of the first
relevant chunk.

Run: python -m eval.run_labeled_chunked
"""
import json
from pathlib import Path

from app.chunker import ingest_policy_documents
from app.retrieval.hybrid_retriever import hybrid_search
from app.retrieval.keyword_store import build_keyword_store, query_keyword_store
from app.retrieval.vector_store import build_vector_store, query_vector_store

DATA_DIR = Path(__file__).parent.parent / "data"
EVAL_SET = Path(__file__).parent / "labeled_eval_chunked.json"
K = 3


def hit_at_k(retrieved, relevant, k):
    return 1.0 if any(d in relevant for d in retrieved[:k]) else 0.0


def reciprocal_rank(retrieved, relevant):
    for i, d in enumerate(retrieved, start=1):
        if d in relevant:
            return 1.0 / i
    return 0.0


def main():
    chunks = ingest_policy_documents(str(DATA_DIR))
    vs = build_vector_store(chunks)
    ks = build_keyword_store(chunks)
    cases = json.loads(EVAL_SET.read_text())

    print(f"Chunked corpus: {len(chunks)} chunks | labeled queries: {len(cases)} | k={K}\n")

    strategies = [
        ("vector_only", lambda q: [h["doc_id"] for h in query_vector_store(vs, q, k=K)]),
        ("bm25_only", lambda q: [h["doc_id"] for h in query_keyword_store(ks, q, k=K)]),
        ("hybrid", lambda q: [h["doc_id"] for h in hybrid_search(vs, ks, q, top_k=K)]),
    ]
    for name, retrieve in strategies:
        hits, rrs = [], []
        for c in cases:
            got = retrieve(c["query"])
            rel = set(c["relevant_doc_ids"])
            hits.append(hit_at_k(got, rel, K))
            rrs.append(reciprocal_rank(got, rel))
        print(f"{name:12s} R@{K}={sum(hits)/len(hits):.3f}  MRR={sum(rrs)/len(rrs):.3f}")


if __name__ == "__main__":
    main()
