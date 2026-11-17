"""Which slice of the policy corpus a claim is allowed to retrieve from.

Once intake has classified the claim, clauses from other policy lines can
only ever be wrong answers: an auto claim is never decided by a home-policy
clause. Restricting the search to the claim's own policy line plus the
general terms (which apply to every claim) removes those cross-domain
competitors before ranking, instead of hoping the reranker demotes them.
"""
from typing import List, Optional

DOMAIN_TYPES = ("auto", "home", "health")
SHARED_TYPE = "general"


def retrieval_scope(claim_type: Optional[str]) -> Optional[List[str]]:
    """Corpus claim_types to search for a claim of this type.

    Returns None (= search everything) when the type isn't one of the three
    policy lines, e.g. "other" or a missing type: with no reliable signal,
    filtering would only risk excluding the right clause.
    """
    if claim_type in DOMAIN_TYPES:
        return [claim_type, SHARED_TYPE]
    return None
