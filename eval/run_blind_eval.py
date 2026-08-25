
import json
from pathlib import Path

from app.retrieval.hybrid_retriever import hybrid_search
from app.retrieval.keyword_store import build_keyword_store
from app.retrieval.vector_store import build_vector_store
from eval.run_eval import precision_at_k, recall_at_k, reciprocal_rank

DOCS_PATH = Path(__file__).parent.parent / "data" / "policy_docs.json"
ORIGINAL_SET = Path(__file__).parent / "retrieval_eval_set.json"
BLIND_SET = Path(__file__).parent / "blind_eval_set.json"
K = 3


def evaluate(name, eval_set, vector_store, keyword_store, verbose=False):
    precisions, recalls, rrs = [], [], []

    for case in eval_set:
        if not case.get("query") or not case.get("relevant_doc_ids"):
            continue

        hits = hybrid_search(vector_store, keyword_store, case["query"], top_k=K)
        retrieved_ids = [h["doc_id"] for h in hits]
        relevant = set(case["relevant_doc_ids"])

        precisions.append(precision_at_k(retrieved_ids, relevant, K))
        recalls.append(recall_at_k(retrieved_ids, relevant, K))
        rrs.append(reciprocal_rank(retrieved_ids, relevant))

        if verbose:
            hit = any(d in relevant for d in retrieved_ids)
            rank = next((i + 1 for i, d in enumerate(retrieved_ids) if d in relevant), None)
            status = f"OK  (rank {rank})" if hit else "MISS"
            print(f"  [{status:12s}] {case['query'][:60]}")
            if not hit:
                print(f"                 expected={sorted(relevant)} got={retrieved_ids}")

    if not precisions:
        print(f"{name}: no complete cases found - fill in the query and relevant_doc_ids fields")
        return None

    n = len(precisions)
    result = {
        "n": n,
        "precision": sum(precisions) / n,
        "recall": sum(recalls) / n,
        "mrr": sum(rrs) / n,
    }
    print(f"\n{name} (n={n}):  P@{K}={result['precision']:.3f}  R@{K}={result['recall']:.3f}  MRR={result['mrr']:.3f}")
    return result


def main():
    docs = json.loads(DOCS_PATH.read_text())
    vector_store = build_vector_store(docs)
    keyword_store = build_keyword_store(docs)

    print(f"Corpus: {len(docs)} docs | k={K}\n")

    original = json.loads(ORIGINAL_SET.read_text())
    evaluate("Original eval set", original, vector_store, keyword_store)

    print("\n" + "=" * 60)
    print("Blind eval set (queries written without reference to the corpus)")
    print("=" * 60)
    blind = json.loads(BLIND_SET.read_text())
    blind_result = evaluate("Blind eval set", blind, vector_store, keyword_store, verbose=True)

    if blind_result and blind_result["n"] < 8:
        print(f"\nNote: only {blind_result['n']} blind cases filled in - aim for at least 8-10 for a meaningful comparison.")


if __name__ == "__main__":
    main()