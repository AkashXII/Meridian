"""
Compares three retrieval strategies against the labeled eval set:
vector-only, BM25-only, and the production hybrid (vector + BM25 + rerank).

Run: python -m eval.run_eval
"""
import json
from pathlib import Path

from app.retrieval.hybrid_retriever import hybrid_search
from app.retrieval.keyword_store import build_keyword_store, query_keyword_store
from app.retrieval.vector_store import build_vector_store, query_vector_store

EVAL_SET_PATH = Path(__file__).parent / "retrieval_eval_set.json"
DOCS_PATH = Path(__file__).parent.parent / "data" / "policy_docs.json"
K = 3


def precision_at_k(retrieved_ids, relevant_ids, k):
    top_k = retrieved_ids[:k]
    return sum(1 for d in top_k if d in relevant_ids) / len(top_k) if top_k else 0.0


def recall_at_k(retrieved_ids, relevant_ids, k):
    top_k = retrieved_ids[:k]
    return sum(1 for d in top_k if d in relevant_ids) / len(relevant_ids)


def reciprocal_rank(retrieved_ids, relevant_ids):
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1 / rank
    return 0.0


def evaluate_strategy(name, retrieve_fn, eval_set, k=K):
    precisions, recalls, rrs = [], [], []
    for case in eval_set:
        retrieved_ids = retrieve_fn(case["query"], k)
        relevant = set(case["relevant_doc_ids"])
        precisions.append(precision_at_k(retrieved_ids, relevant, k))
        recalls.append(recall_at_k(retrieved_ids, relevant, k))
        rrs.append(reciprocal_rank(retrieved_ids, relevant))

    result = {
        "name": name,
        "precision": sum(precisions) / len(precisions),
        "recall": sum(recalls) / len(recalls),
        "mrr": sum(rrs) / len(rrs),
    }
    print(f"{name:15s} P@{k}={result['precision']:.3f}  R@{k}={result['recall']:.3f}  MRR={result['mrr']:.3f}")
    return result


def main():
    docs = json.loads(DOCS_PATH.read_text())
    eval_set = json.loads(EVAL_SET_PATH.read_text())
    vector_store = build_vector_store(docs)
    keyword_store = build_keyword_store(docs)

    print(f"Corpus: {len(docs)} docs | Eval set: {len(eval_set)} queries | k={K}\n")

    vector_only = lambda q, k: [h["doc_id"] for h in query_vector_store(vector_store, q, k=k)]
    bm25_only = lambda q, k: [h["doc_id"] for h in query_keyword_store(keyword_store, q, k=k)]
    hybrid = lambda q, k: [h["doc_id"] for h in hybrid_search(vector_store, keyword_store, q, top_k=k)]

    evaluate_strategy("vector_only", vector_only, eval_set)
    evaluate_strategy("bm25_only", bm25_only, eval_set)
    evaluate_strategy("hybrid", hybrid, eval_set)


if __name__ == "__main__":
    main()