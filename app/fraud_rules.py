
from datetime import date, datetime

from app.models import ExtractedClaim

FILING_DEADLINE_DAYS = 60


def _check_policy_prefix(claim: ExtractedClaim) -> str | None:
    """The H- prefix is reserved for health policies (policy_docs: health_1)."""
    if not claim.policy_number:
        return None
    is_h_prefix = claim.policy_number.upper().startswith("H-")
    if is_h_prefix and claim.claim_type != "health":
        return (
            f"Policy number {claim.policy_number} uses the H- prefix, which is "
            f"reserved for health policies, but the claim type is '{claim.claim_type}'."
        )
    if claim.claim_type == "health" and not is_h_prefix:
        return (
            f"Health claim submitted against policy {claim.policy_number}, "
            "which does not use the required H- prefix."
        )
    return None


def _check_filing_deadline(claim: ExtractedClaim) -> str | None:
    """Claims must be filed within 60 days of the incident (policy_docs: general_1)."""
    if not claim.incident_date:
        return None
    try:
        incident = datetime.strptime(claim.incident_date, "%Y-%m-%d").date()
    except ValueError:
        return f"Incident date '{claim.incident_date}' is not a valid YYYY-MM-DD date."

    days_elapsed = (date.today() - incident).days
    if days_elapsed > FILING_DEADLINE_DAYS:
        return (
            f"Claim filed {days_elapsed} days after the incident, exceeding the "
            f"{FILING_DEADLINE_DAYS}-day filing deadline."
        )
    if days_elapsed < 0:
        return f"Incident date {claim.incident_date} is in the future."
    return None


def _check_amount(claim: ExtractedClaim) -> str | None:
    """A claim asking for nothing is almost always an extraction failure."""
    if claim.amount_requested is not None and claim.amount_requested <= 0:
        return (
            f"Claimed amount is {claim.amount_requested}, which is not a valid "
            "claim amount — likely missing or misparsed."
        )
    return None


ALL_CHECKS = [_check_policy_prefix, _check_filing_deadline, _check_amount]


def run_fraud_checks(claim: ExtractedClaim) -> list[str]:
    """Returns a list of violation messages. Empty list means nothing flagged."""
    return [msg for check in ALL_CHECKS if (msg := check(claim)) is not None]