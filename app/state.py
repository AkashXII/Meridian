
from typing import List, Optional, TypedDict
from app.models import CoverageDecision, ExtractedClaim, FraudCheck
class ClaimState(TypedDict):
    raw_claim_text: str
    redacted_claim_text: str
    pii_found: List[dict]
    extracted: Optional[ExtractedClaim]
    missing_fields: List[str]
    coverage_decision: Optional[CoverageDecision]
    fraud_check: Optional[FraudCheck]
    final_decision: Optional[CoverageDecision]
    retrieved_docs: List[dict]
    # Set by coverage_check: best cross-encoder score among retrieved clauses,
    # and whether it fell below MIN_RERANK_SCORE (app.retrieval.confidence).
    retrieval_top_score: Optional[float]
    low_retrieval_confidence: bool
    # Set by final_decision when deterministic code overrode the LLM.
    escalation_reason: Optional[str]
    trace_carrier: dict
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
