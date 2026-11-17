from app.decision import ESCALATION_PREFIX, resolve_final_decision
from app.models import CoverageDecision, FraudCheck

CLEAN = FraudCheck(flagged=False, reason="No deterministic rule violations detected.")
FLAGGED = FraudCheck(flagged=True, reason="Claim filed 90 days after the incident.")


def cov(decision):
    return CoverageDecision(decision=decision, reasoning=f"LLM says {decision}.")


def test_confident_clean_approval_passes_through():
    final, reason = resolve_final_decision(cov("approved"), CLEAN, 300.0, retrieval_top_score=0.9)
    assert final.decision == "approved"
    assert final.reasoning == "LLM says approved."
    assert reason is None


def test_fraud_flag_escalates_an_approval():
    final, reason = resolve_final_decision(cov("approved"), FLAGGED, 300.0)
    assert final.decision == "needs_review"
    assert final.reasoning.startswith(ESCALATION_PREFIX)
    assert "fraud flag" in reason


def test_fraud_flag_leaves_a_denial_alone():
    final, reason = resolve_final_decision(cov("denied"), FLAGGED, 300.0)
    assert final.decision == "denied"
    assert reason is None


def test_low_confidence_escalates_an_approval():
    final, reason = resolve_final_decision(
        cov("approved"), CLEAN, 300.0,
        low_retrieval_confidence=True, retrieval_top_score=0.03, confidence_threshold=0.10,
    )
    assert final.decision == "needs_review"
    assert "low retrieval confidence" in reason
    assert "0.03" in reason and "0.10" in reason


def test_low_confidence_escalates_a_denial_too():
    final, reason = resolve_final_decision(
        cov("denied"), CLEAN, 300.0, low_retrieval_confidence=True, retrieval_top_score=0.03,
    )
    assert final.decision == "needs_review"
    assert reason is not None


def test_low_confidence_on_needs_review_still_explains_why():
    final, reason = resolve_final_decision(
        cov("needs_review"), CLEAN, 300.0, low_retrieval_confidence=True, retrieval_top_score=0.03,
    )
    assert final.decision == "needs_review"
    assert "low retrieval confidence" in reason


def test_nothing_retrieved_is_described_as_such():
    _, reason = resolve_final_decision(
        cov("approved"), CLEAN, 300.0, low_retrieval_confidence=True, retrieval_top_score=None,
    )
    assert "no policy clauses were retrieved" in reason


def test_fraud_and_low_confidence_reasons_are_both_reported():
    _, reason = resolve_final_decision(
        cov("approved"), FLAGGED, 300.0, low_retrieval_confidence=True, retrieval_top_score=0.03,
    )
    assert "fraud flag" in reason and "low retrieval confidence" in reason


def test_processing_requirements_appended_unless_denied():
    approved, _ = resolve_final_decision(cov("approved"), CLEAN, 3200.0)
    denied, _ = resolve_final_decision(cov("denied"), CLEAN, 3200.0)
    assert "Processing requirements" in approved.reasoning
    assert "Processing requirements" not in denied.reasoning


def test_llm_assessment_object_is_not_modified():
    coverage = cov("approved")
    resolve_final_decision(coverage, FLAGGED, 300.0, low_retrieval_confidence=True)
    assert coverage.decision == "approved"
    assert coverage.reasoning == "LLM says approved."
