import json
from pathlib import Path
from app.pii import redact
from app.llm import get_llm
from app.models import CoverageDecision, ExtractedClaim, FraudCheck
from app.retrieval.hybrid_retriever import hybrid_search
from app.retrieval.keyword_store import build_keyword_store
from app.retrieval.vector_store import build_vector_store
from app.state import ClaimState
from app.fraud_rules import run_fraud_checks

REQUIRED_FIELDS = ["policy_number", "claim_type", "incident_date"]

_docs = json.loads((Path(__file__).parent.parent / "data" / "policy_docs.json").read_text())
_vector_store = build_vector_store(_docs)
_keyword_store = build_keyword_store(_docs)

def intake_node(state: ClaimState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(ExtractedClaim)
    extracted: ExtractedClaim = structured_llm.invoke(
        "Extract structured claim details from this claim description:\n\n"
        f"{state['redacted_claim_text']}"
    )
    missing = [f for f in REQUIRED_FIELDS if not getattr(extracted, f)]
    return {"extracted": extracted, "missing_fields": missing}

def pii_redact_node(state: ClaimState) -> dict:
    redacted_text, found = redact(state["raw_claim_text"])
    if found:
        print(f"\n[PII redacted] Found: {[e['entity_type'] for e in found]}")
    return {"redacted_claim_text": redacted_text, "pii_found": found}

def clarification_node(state: ClaimState) -> dict:
    # Phase 1 just surfaces what's missing. Later this is where you'd loop
    # back to a user or an external system for the missing info.
    print(f"\n[Clarification needed] Missing fields: {state['missing_fields']}")
    return {}


def coverage_check_node(state: ClaimState) -> dict:
    extracted = state["extracted"]
    query = f"{extracted.claim_type} claim: {extracted.description}"
    retrieved = hybrid_search(_vector_store, _keyword_store, query, top_k=3)
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

def fraud_check_node(state: ClaimState) -> dict:
    violations = run_fraud_checks(state["extracted"])
    if violations:
        return {"fraud_check": FraudCheck(flagged=True, reason=" ".join(violations))}
    return {
        "fraud_check": FraudCheck(
            flagged=False, reason="No deterministic rule violations detected."
        )
    }
def final_decision_node(state: ClaimState) -> dict:
    coverage = state["coverage_decision"]
    fraud = state["fraud_check"]

    if fraud.flagged and coverage.decision == "approved":
        overridden = CoverageDecision(
            decision="needs_review",
            reasoning=(
                f"Original coverage assessment: {coverage.reasoning} "
                f"Overridden to needs_review — fraud flag: {fraud.reason}"
            ),
        )
        return {"coverage_decision": overridden}

    return {}

def route_after_intake(state: ClaimState):
    if state["missing_fields"]:
        return "clarification_needed"
    return ["coverage_check", "fraud_check"]