
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
    trace_carrier: dict
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float