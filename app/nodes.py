"""
Each node is a plain function: (state) -> partial state update.
No LangGraph-specific magic here, which makes them easy to unit test later.
"""
from app.llm import get_llm
from app.models import CoverageDecision, ExtractedClaim
from app.state import ClaimState

REQUIRED_FIELDS = ["policy_number", "claim_type", "incident_date"]

# Stand-in for the real knowledge base. Phase 2 replaces this with hybrid RAG
# over actual policy documents — the node interface below won't need to change.
POLICY_RULES = """
- Auto claims are covered up to $10,000 if the incident date is within the policy's active period.
- Home claims related to flood damage are NOT covered under standard policies.
- Health claims require a policy_number starting with 'H-' to be considered valid.
- Any claim missing a clear incident_date should be marked as needs_review.
"""


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
    llm = get_llm()
    structured_llm = llm.with_structured_output(CoverageDecision)
    extracted = state["extracted"]
    decision: CoverageDecision = structured_llm.invoke(
        f"Policy rules:\n{POLICY_RULES}\n\n"
        f"Claim details:\n{extracted.model_dump_json(indent=2)}\n\n"
        "Decide whether this claim should be approved, denied, or needs_review, "
        "and explain why in one or two sentences."
    )
    return {"coverage_decision": decision}


def route_after_intake(state: ClaimState) -> str:
    return "clarification_needed" if state["missing_fields"] else "coverage_check"
