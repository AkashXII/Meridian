"""Is the retrieved evidence strong enough to let the LLM decide on its own?

The cross-encoder's score for the best (query, clause) pair is a usable
signal for "retrieval found nothing that really matches this claim". When it
is below MIN_RERANK_SCORE, the LLM is reasoning over clauses that probably
don't govern the claim, so its approve/deny is not trustworthy and the
claim is escalated to a human instead (see app.decision).

MIN_RERANK_SCORE must be calibrated, not guessed: run
    python -m eval.run_scope_and_confidence_eval
which prints the top-1 score of every eval query split by hit/miss and a
threshold sweep, then set MIN_RERANK_SCORE in .env. The default below is a
placeholder until that has been done.
"""
import os
from typing import Optional, Tuple

MIN_RERANK_SCORE = float(os.getenv("MIN_RERANK_SCORE", "0.10"))


def assess_retrieval(
    retrieved: list[dict], threshold: Optional[float] = None
) -> Tuple[Optional[float], bool]:
    """Returns (top_rerank_score, is_low_confidence).

    Nothing retrieved, or a top hit with no rerank score, counts as low
    confidence: there is no evidence to decide from.
    """
    threshold = MIN_RERANK_SCORE if threshold is None else threshold
    if not retrieved:
        return None, True
    top = retrieved[0].get("rerank_score")
    if top is None:
        return None, True
    return float(top), float(top) < threshold
