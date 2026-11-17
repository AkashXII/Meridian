from typing import List, Optional

import chromadb


def build_vector_store(docs: list[dict]):
    client = chromadb.Client()
    collection = client.create_collection(name="policy_docs")
    collection.add(
        ids=[d["doc_id"] for d in docs],
        documents=[d["text"] for d in docs],
        metadatas=[{"claim_type": d["claim_type"], "title": d["title"]} for d in docs],
    )
    return collection


def query_vector_store(
    collection, query: str, k: int = 3, claim_types: Optional[List[str]] = None
) -> list[dict]:
    """claim_types, if given, restricts the search to chunks whose metadata
    claim_type is in that list (filtered inside Chroma, before ranking)."""
    kwargs = {"query_texts": [query], "n_results": k}
    if claim_types:
        kwargs["where"] = {"claim_type": {"$in": list(claim_types)}}
    results = collection.query(**kwargs)
    hits = []
    for doc_id, text, meta, distance in zip(
        results["ids"][0], results["documents"][0],
        results["metadatas"][0], results["distances"][0],
    ):
        hits.append({
            "doc_id": doc_id, "text": text,
            "claim_type": meta["claim_type"], "title": meta["title"],
            "score": 1 - distance,
        })
    return hits
