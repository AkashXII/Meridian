from typing import List
VARIANT_PROMPT = (
    "Rewrite this insurance claim description into 3 different search queries "
    "that would help find the relevant policy clause. Vary the framing:\n"
    "1. Formal insurance terminology\n"
    "2. The specific peril or event\n"
    "3. The coverage or treatment being sought\n\n"
    "Output ONLY the 3 queries, one per line, no numbering, no extra text.\n\n"
    "Claim: {description}"
)


def generate_query_variants(description: str, llm=None) -> List[str]:
    """Returns the original description plus up to 3 LLM-generated variants.
    Always includes the original, so multi-query never does worse than single-
    query on a claim the raw phrasing already handles well."""
    variants = [description]
    if not description or not description.strip():
        return variants
    if llm is None:
        from app.llm import get_llm
        llm = get_llm()
    try:
        resp = llm.invoke(VARIANT_PROMPT.format(description=description))
        text = resp.content if hasattr(resp, "content") else str(resp)
        for line in text.strip().splitlines():
            line = line.strip().lstrip("0123456789.-) ").strip()
            if line and line not in variants:
                variants.append(line)
    except Exception:
        pass  
    return variants


def multi_query_search(vector_store, keyword_store, description, hybrid_search_fn, top_k=3, llm=None):
    variants = generate_query_variants(description, llm=llm)

    best_by_doc = {}
    for q in variants:
        for hit in hybrid_search_fn(vector_store, keyword_store, q, top_k=top_k):
            did = hit["doc_id"]
            if did not in best_by_doc or hit.get("rerank_score", hit.get("score", 0)) > \
               best_by_doc[did].get("rerank_score", best_by_doc[did].get("score", 0)):
                best_by_doc[did] = hit

    merged = sorted(
        best_by_doc.values(),
        key=lambda h: h.get("rerank_score", h.get("score", 0)),
        reverse=True,
    )
    return merged[:top_k]