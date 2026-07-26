
import json
from pathlib import Path
import os
from app.token_usage import extract_usage, estimate_cost
from opentelemetry import propagate

from app.fraud_rules import run_fraud_checks
from app.llm import get_llm
from app.models import CoverageDecision, ExtractedClaim, FraudCheck
from app.pii import redact
from app.retrieval.hybrid_retriever import hybrid_search
from app.retrieval.keyword_store import build_keyword_store
from app.retrieval.vector_store import build_vector_store
from app.state import ClaimState
from app.tracing import tracer

REQUIRED_FIELDS = ["policy_number", "claim_type", "incident_date"]

_docs = json.loads((Path(__file__).parent.parent / "data" / "policy_docs.json").read_text())
_vector_store = build_vector_store(_docs)
_keyword_store = build_keyword_store(_docs)


def pii_redact_node(state: ClaimState) -> dict:
    parent_ctx = propagate.extract(state["trace_carrier"])
    with tracer.start_as_current_span("pii_redact", context=parent_ctx) as span:
        redacted_text, found = redact(state["raw_claim_text"])
        span.set_attribute("pii.entities_found", len(found))
        if found:
            print(f"\n[PII redacted] Found: {[e['entity_type'] for e in found]}")
    return {"redacted_claim_text": redacted_text, "pii_found": found}


def intake_node(state: ClaimState) -> dict:
    parent_ctx = propagate.extract(state["trace_carrier"])
    with tracer.start_as_current_span("intake", context=parent_ctx) as span:
        llm = get_llm()
        structured_llm = llm.with_structured_output(ExtractedClaim, include_raw=True)
        result = structured_llm.invoke(
            "Extract structured claim details from this claim description:\n\n"
            f"{state['redacted_claim_text']}"
        )
        extracted: ExtractedClaim = result["parsed"]
        usage = extract_usage(result["raw"])

        missing = [f for f in REQUIRED_FIELDS if not getattr(extracted, f)]
        span.set_attribute("claim.policy_number", extracted.policy_number or "")
        span.set_attribute("claim.type", extracted.claim_type or "")
        span.set_attribute("intake.missing_fields", missing)
        span.set_attribute("llm.input_tokens", usage["input_tokens"])
        span.set_attribute("llm.output_tokens", usage["output_tokens"])

    return {
        "extracted": extracted,
        "missing_fields": missing,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
    }

def clarification_node(state: ClaimState) -> dict:
    parent_ctx = propagate.extract(state["trace_carrier"])
    with tracer.start_as_current_span("clarification_needed", context=parent_ctx):
        print(f"\n[Clarification needed] Missing fields: {state['missing_fields']}")
    return {}


def coverage_check_node(state: ClaimState) -> dict:
    parent_ctx = propagate.extract(state["trace_carrier"])
    with tracer.start_as_current_span("coverage_check", context=parent_ctx) as span:
        extracted = state["extracted"]
        query = f"{extracted.claim_type} claim: {extracted.description}"

        with tracer.start_as_current_span("retrieval"):
            retrieved = hybrid_search(_vector_store, _keyword_store, query, top_k=3)

        policy_context = "\n".join(f"- {r['title']}: {r['text']}" for r in retrieved)

        with tracer.start_as_current_span("llm_call"):
            llm = get_llm()
            structured_llm = llm.with_structured_output(CoverageDecision, include_raw=True)
            result = structured_llm.invoke(
                f"Relevant policy clauses:\n{policy_context}\n\n"
                f"Claim details:\n{extracted.model_dump_json(indent=2)}\n\n"
                "Decide whether this claim should be approved, denied, or needs_review, "
                "based only on the policy clauses above, and explain why in one or two sentences."
            )
            decision: CoverageDecision = result["parsed"]
            usage = extract_usage(result["raw"])

        retrieved_docs = [
            {"doc_id": r["doc_id"], "title": r["title"], "rerank_score": r.get("rerank_score")}
            for r in retrieved
        ]
        total_input = state["input_tokens"] + usage["input_tokens"]
        total_output = state["output_tokens"] + usage["output_tokens"]
        cost = estimate_cost(os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), total_input, total_output)

        span.set_attribute("coverage.decision", decision.decision)
        span.set_attribute("retrieval.doc_count", len(retrieved_docs))
        span.set_attribute("llm.input_tokens", usage["input_tokens"])
        span.set_attribute("llm.output_tokens", usage["output_tokens"])

    return {
        "coverage_decision": decision,
        "retrieved_docs": retrieved_docs,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "estimated_cost_usd": cost,
    }

def fraud_check_node(state: ClaimState) -> dict:
    parent_ctx = propagate.extract(state["trace_carrier"])
    with tracer.start_as_current_span("fraud_check", context=parent_ctx) as span:
        violations = run_fraud_checks(state["extracted"])
        flagged = bool(violations)
        span.set_attribute("fraud.flagged", flagged)
        if flagged:
            result = FraudCheck(flagged=True, reason=" ".join(violations))
        else:
            result = FraudCheck(flagged=False, reason="No deterministic rule violations detected.")
    return {"fraud_check": result}


def final_decision_node(state: ClaimState) -> dict:
    parent_ctx = propagate.extract(state["trace_carrier"])
    with tracer.start_as_current_span("final_decision", context=parent_ctx) as span:
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
            span.set_attribute("final_decision.overridden", True)
            return {"coverage_decision": overridden}

        span.set_attribute("final_decision.overridden", False)
    return {}


def route_after_intake(state: ClaimState):
    if state["missing_fields"]:
        return "clarification_needed"
    return ["coverage_check", "fraud_check"]