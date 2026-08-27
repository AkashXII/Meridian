import json
from pathlib import Path
from app.chunker import ingest_policy_documents
from app.retrieval.vector_store import build_vector_store
from app.retrieval.keyword_store import build_keyword_store
from app.retrieval.hybrid_retriever import hybrid_search

DATA_DIR = Path(__file__).parent.parent / "data"
BLIND_SET = Path(__file__).parent / "blind_eval_set_chunked.json"
def main():
    chunks = ingest_policy_documents(str(DATA_DIR))
    vector_store = build_vector_store(chunks)
    keyword_store = build_keyword_store(chunks)
    blind = json.loads(BLIND_SET.read_text())
    print(f"Chunked corpus: {len(chunks)} chunks | blind queries: {len(blind)}\n")
    per_query = []
    for case in blind:
        hits = hybrid_search(vector_store, keyword_store, case["query"], top_k=5)
        retrieved = [h["doc_id"] for h in hits]
        relevant = set(case["relevant_doc_ids"])
        per_query.append((case, retrieved, relevant))

    for K in (3, 5):
        hit_count = 0
        for case, retrieved, relevant in per_query:
            found = any(d in retrieved[:K] for d in relevant)
            if found:
                hit_count += 1
            if K == 3:  
                rank = next((i + 1 for i, d in enumerate(retrieved) if d in relevant), None)
                status = f"OK (rank {rank})" if (rank and rank <= 3) else "MISS"
                print(f"  [{status:11s}] {case['query'][:50]}")
                if status == "MISS":
                    print(f"                want {sorted(relevant)} got {retrieved[:3]}")
        print(f"\nrecall@{K}: {hit_count}/{len(blind)} = {hit_count / len(blind):.3f}")
        if K == 3:
            print()


if __name__ == "__main__":
    main()