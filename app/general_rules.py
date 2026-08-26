
from typing import List
DOCUMENTATION_THRESHOLD = 500      
ASSESSMENT_THRESHOLD = 10000      
def check_processing_requirements(amount_requested) -> List[str]:
    requirements: List[str] = []
    if amount_requested is None:
        return requirements
    try:
        amount = float(amount_requested)
    except (TypeError, ValueError):
        return requirements

    if amount > ASSESSMENT_THRESHOLD:
        requirements.append(
            f"Claim amount ${amount:,.0f} exceeds ${ASSESSMENT_THRESHOLD:,} - "
            "independent assessment required before approval."
        )
    elif amount > DOCUMENTATION_THRESHOLD:
        requirements.append(
            f"Claim amount ${amount:,.0f} exceeds ${DOCUMENTATION_THRESHOLD:,} - "
            "supporting documentation (photos or receipts) required."
        )

    return requirements