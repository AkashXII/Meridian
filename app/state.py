"""
The state that flows through every node in the graph. Each node receives the
current state and returns a dict of the keys it wants to update — LangGraph
merges that into the running state for you.
"""
from typing import List, Optional, TypedDict

from app.models import CoverageDecision, ExtractedClaim


class ClaimState(TypedDict):
    raw_claim_text: str
    extracted: Optional[ExtractedClaim]
    missing_fields: List[str]
    coverage_decision: Optional[CoverageDecision]
