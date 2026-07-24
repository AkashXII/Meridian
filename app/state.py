
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