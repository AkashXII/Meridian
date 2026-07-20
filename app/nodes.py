import json
from pathlib import Path

from app.llm import get_llm
from app.models import CoverageDecision, ExtractedClaim
from app.retrieval.hybrid_retriever import hybrid_search
from app.retrieval.keyword_store import build_keyword_store
from app.retrieval.vector_store import build_vector_store
from app.state import ClaimState

REQUIRED_FIELDS = ["policy_number", "claim_type", "incident_date"]

_vector_store = None
_keyword_store = None


def _get_retrieval_stores():
    global _vector_store, _keyword_store
    if _vector_store is None or _keyword_store is None:
        docs_path = Path(__file__).parent.parent / "data" / "policy_docs.json"
        docs = json.loads(docs_path.read_text())
        _vector_store = build_vector_store(docs)
        _keyword_store = build_keyword_store(docs)
    return _vector_store, _keyword_store

def intake_node(state: ClaimState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(ExtractedClaim)
    extracted: ExtractedClaim = structured_llm.invoke(
        "Extract structured claim details from this claim description:\n\n"
        f"{state['raw_claim_text']}"
    )
    missing = [f for f in REQUIRED_FIELDS if not getattr(extracted, f)]
    return {"extracted": extracted, "missing_fields": missing}


def clarification_node(state: ClaimState) -> dict:
    # Phase 1 just surfaces what's missing. Later this is where you'd loop
    # back to a user or an external system for the missing info.
    print(f"\n[Clarification needed] Missing fields: {state['missing_fields']}")
    return {}


def coverage_check_node(state: ClaimState) -> dict:
    extracted = state["extracted"]
    vector_store, keyword_store = _get_retrieval_stores()

    query = f"{extracted.claim_type} claim: {extracted.description}"
    retrieved = hybrid_search(vector_store, keyword_store, query, top_k=3)
    policy_context = "\n".join(f"- {r['title']}: {r['text']}" for r in retrieved)

    llm = get_llm()
    structured_llm = llm.with_structured_output(CoverageDecision)
    decision: CoverageDecision = structured_llm.invoke(
        f"Relevant policy clauses:\n{policy_context}\n\n"
        f"Claim details:\n{extracted.model_dump_json(indent=2)}\n\n"
        "Decide whether this claim should be approved, denied, or needs_review, "
        "based only on the policy clauses above, and explain why in one or two sentences."
    )
    return {"coverage_decision": decision}

def route_after_intake(state: ClaimState) -> str:
    return "clarification_needed" if state["missing_fields"] else "coverage_check"
