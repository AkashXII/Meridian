"""Deterministic merge of the parallel branches into the final decision.

Kept free of LLM, tracing and retrieval imports so it can be unit-tested
directly. The LLM's own assessment (coverage) is never modified here; the
final decision is a separate object, so both are stored side by side.

Escalation rules, applied to the LLM's approve/deny:
  1. Fraud flag on an approval -> needs_review (a fraud flag on a denial
     doesn't need a human: the outcome is already the cautious one).
  2. Low retrieval confidence on an approval OR a denial -> needs_review.
     Unlike fraud, a denial is escalated too: denying a claim because the
     retrieved clauses didn't match it is just as unsupported as approving it.
Processing requirements (documentation/assessment thresholds) are appended
to anything that isn't a denial.
"""
from typing import Optional, Tuple

from app.general_rules import check_processing_requirements
from app.models import CoverageDecision, FraudCheck

ESCALATION_PREFIX = "Escalated for human review — "


def resolve_final_decision(
    coverage: CoverageDecision,
    fraud: FraudCheck,
    amount_requested: Optional[float],
    low_retrieval_confidence: bool = False,
    retrieval_top_score: Optional[float] = None,
    confidence_threshold: Optional[float] = None,
) -> Tuple[CoverageDecision, Optional[str]]:
    """Returns (final_decision, escalation_reason or None)."""
    reasons = []

    if fraud.flagged and coverage.decision == "approved":
        reasons.append(f"fraud flag: {fraud.reason}")

    if low_retrieval_confidence:
        if retrieval_top_score is None:
            detail = "no policy clauses were retrieved for this claim"
        else:
            detail = f"best clause match score {retrieval_top_score:.2f}"
            if confidence_threshold is not None:
                detail += f" is below the {confidence_threshold:.2f} threshold"
        # Applies to every LLM outcome: approve/deny get escalated, and a
        # needs_review still tells the reviewer the evidence was weak.
        reasons.append(
            f"low retrieval confidence ({detail}); the retrieved policy clauses "
            "may not govern this claim"
        )

    if reasons:
        escalation_reason = "; ".join(reasons)
        final = CoverageDecision(
            decision="needs_review",
            reasoning=f"{ESCALATION_PREFIX}{escalation_reason}.",
        )
    else:
        escalation_reason = None
        final = CoverageDecision(decision=coverage.decision, reasoning=coverage.reasoning)

    requirements = check_processing_requirements(amount_requested)
    if requirements and final.decision != "denied":
        final = CoverageDecision(
            decision=final.decision,
            reasoning=final.reasoning + " Processing requirements: " + " ".join(requirements),
        )

    return final, escalation_reason
