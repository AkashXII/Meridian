
from typing import Literal, Optional
from pydantic import BaseModel, Field


class ExtractedClaim(BaseModel):
    policy_number: Optional[str] = Field(
        None, description="The policy number referenced in the claim, if mentioned"
    )
    claim_type: Optional[Literal["auto", "home", "health", "other"]] = Field(
        None, description="Type of insurance claim"
    )
    incident_date: Optional[str] = Field(
        None, description="Date of the incident in YYYY-MM-DD format, if mentioned"
    )
    description: str = Field(
        description="A concise one-sentence summary of what happened"
    )
    amount_requested: Optional[float] = Field(
        None, description="Dollar amount being claimed, if mentioned"
    )
    


class CoverageDecision(BaseModel):
    decision: Literal["approved", "denied", "needs_review"]
    reasoning: str = Field(
        description="Brief explanation for the decision, referencing the policy rules used"
    )
class FraudCheck(BaseModel):
    flagged: bool = Field(description="True if anything in the claim looks inconsistent or suspicious")
    reason: str = Field(description="Brief explanation of what was flagged, or why nothing was flagged")