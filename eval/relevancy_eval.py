"""
Answer relevancy eval: does the coverage_check reasoning actually address
THIS claim's specific details (amount, situation, claim type), or is it
generic/evasive/off-target - independent of whether it's grounded in the
retrieved clauses (that's what faithfulness_eval.py already checks).

A response can be fully faithful (every claim traces to a real retrieved
clause) and still fail relevancy - e.g. accurately quoting a real exclusion
while never actually engaging with the claim's specific amount or situation.

Same patterns as faithfulness_eval.py throughout: json_mode with an explicit
JSON shape (this model's documented structured-output incompatibility),
retry-then-skip on transient failures, and a hand-planted trap case to
verify the judge actually discriminates before trusting it on real claims.

Uses redacted_claim_text (confirmed via DESCRIBE claim_decisions) as the
claim's specific details - the actual text coverage_check reasoned from,
post-PII-redaction, not a separately-parsed summary field.
"""
import os
import time
from pathlib import Path

import pymysql
from dotenv import load_dotenv

from app.llm import get_judge_llm
from pydantic import BaseModel, Field

load_dotenv()

SAMPLE_SIZE = 20


class RelevancyCheck(BaseModel):
    relevant: bool = Field(description="True if the reasoning addresses this specific claim's details")
    explanation: str = Field(description="Brief explanation of the verdict")


def _connect():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "claims_platform"),
        cursorclass=pymysql.cursors.DictCursor,
    )


def fetch_real_cases(limit=SAMPLE_SIZE):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, policy_number, claim_type, redacted_claim_text,
                       amount_requested, coverage_reasoning
                FROM claim_decisions
                WHERE coverage_reasoning IS NOT NULL
                  AND redacted_claim_text IS NOT NULL
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()


# Hand-written, not model-generated - reasoning that's entirely accurate and
# grounded but never actually engages with what THIS claim is asking. Tests
# relevancy specifically: faithfulness would likely pass this (nothing here
# is fabricated), but it should fail relevancy, since it doesn't address the
# claim at all.
TRAP_CASE = {
    "id": "TRAP",
    "claim_type": "home",
    "redacted_claim_text": "A tree fell on my roof during a storm and caused $6,000 in damage. Is this covered?",
    "amount_requested": 6000.0,
    "coverage_reasoning": (
        "Claims processing requires supporting documentation for amounts "
        "over $500, and independent assessment is required for amounts "
        "over $10,000. Please ensure all documentation is submitted within "
        "the standard filing window."
    ),
    "expect_relevant": False,
}


def judge(claim_type, description, amount_requested, reasoning) -> RelevancyCheck:
    llm = get_judge_llm()
    structured_llm = llm.with_structured_output(RelevancyCheck, method="json_mode", include_raw=True)
    result = structured_llm.invoke(
        "You are evaluating whether a generated insurance-claim decision explanation "
        "actually ADDRESSES the specific claim it was given - not whether it's "
        "factually correct or grounded in policy text (that's checked separately). "
        "Respond with ONLY a JSON object matching this exact shape: "
        '{"relevant": true or false, "explanation": string}. '
        "No other text before or after the JSON.\n\n"
        f"CLAIM TYPE: {claim_type}\n"
        f"CLAIM DESCRIPTION: {description}\n"
        f"AMOUNT REQUESTED: {amount_requested}\n\n"
        f"GENERATED REASONING:\n{reasoning}\n\n"
        "Mark relevant=false if the reasoning is generic, templated, or evasive - "
        "for example, only discussing procedural requirements (documentation, "
        "deadlines) without ever addressing whether THIS claim's specific "
        "situation is covered. Mark relevant=false if the reasoning appears to "
        "answer a different question than the one the claim actually asks. "
        "Mark relevant=true if the reasoning directly engages with the claim's "
        "specific situation, even if you are not separately verifying whether "
        "the coverage conclusion itself is correct - that is a different check.\n\n"
        "Set relevant=true only if the reasoning genuinely engages with this "
        "specific claim's details."
    )
    parsed = result["parsed"]
    if parsed is None:
        raise ValueError(f"Judge returned unparseable output: {result.get('parsing_error')}")
    return parsed


def judge_with_retry(claim_type, description, amount_requested, reasoning, max_retries=3) -> RelevancyCheck:
    for attempt in range(max_retries):
        try:
            return judge(claim_type, description, amount_requested, reasoning)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 * (attempt + 1)
            print(f"     (judge call failed: {type(e).__name__}, retrying in {wait}s...)")
            time.sleep(wait)


def main():
    real_cases = fetch_real_cases()

    if not real_cases:
        print("No claims found with redacted_claim_text populated.")
        return

    print(f"Judging {len(real_cases)} real claims + 1 trap case\n")

    results = []
    for row in real_cases:
        try:
            verdict = judge_with_retry(
                row["claim_type"], row["redacted_claim_text"], row["amount_requested"], row["coverage_reasoning"]
            )
        except Exception as e:
            print(f"  claim {row['id']:>6}  SKIPPED - judge failed after retries ({type(e).__name__})")
            continue

        results.append(verdict.relevant)
        status = "RELEVANT" if verdict.relevant else "OFF-TARGET"
        print(f"[{status}] claim {row['id']} ({row['claim_type']}): {row['redacted_claim_text'][:60]}")
        if not verdict.relevant:
            print(f"     ! {verdict.explanation}")

    trap_verdict = judge_with_retry(
        TRAP_CASE["claim_type"], TRAP_CASE["redacted_claim_text"], TRAP_CASE["amount_requested"], TRAP_CASE["coverage_reasoning"]
    )
    trap_caught = trap_verdict.relevant == TRAP_CASE["expect_relevant"]
    print(f"\n[TRAP] judge {'CORRECTLY caught' if trap_caught else 'FAILED to catch'} the off-target reasoning")
    print(f"     {trap_verdict.explanation}")

    if results:
        rate = sum(results) / len(results)
        print(f"\nRelevancy rate on real claims: {rate:.1%} ({sum(results)}/{len(results)})")
    print(f"Trap case detection: {'PASS' if trap_caught else 'FAIL'}")


if __name__ == "__main__":
    main()