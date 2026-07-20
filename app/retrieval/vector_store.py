"""
Vector search over the policy documents using embedding similarity.
Chroma's default embedding function runs a local MiniLM model — no API key,
no extra cost, works fully offline once the model is cached.
"""
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


def query_vector_store(collection, query: str, k: int = 3) -> list[dict]:
    results = collection.query(query_texts=[query], n_results=k)
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