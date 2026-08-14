"""
Measures whether coverage_check's generated reasoning is actually grounded in
the policy clauses that were retrieved for it - as opposed to the retrieval
eval, which only measures whether the RIGHT clauses were found.

These are different questions. Retrieval can be perfect while the LLM still
invents a rule that wasn't in the retrieved text (exactly the failure mode hit
in Phase 3, where the fraud check hallucinated an "auto claims need an A-
prefix" rule that appears nowhere in the corpus).

Uses an LLM as judge. That is a deliberate, appropriate use here: "is this
claim supported by this text" is a genuine judgment call, not a lookup - the
opposite of the fraud-prefix check, which was a closed-form comparison and
correctly moved to plain code.

Run: python -m eval.faithfulness_eval
"""
import json
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

from app.llm import get_llm
from app.models import FaithfulnessCheck

load_dotenv()

DOCS_PATH = Path(__file__).parent.parent / "data" / "policy_docs.json"
SAMPLE_SIZE = 10


def _connect():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "claims_platform"),
        cursorclass=pymysql.cursors.DictCursor,
    )


def load_doc_texts() -> dict:
    """
    retrieved_docs in the audit table stores doc_id/title/rerank_score but NOT
    the clause text, so we look the text back up from the corpus by doc_id.

    Known limitation: if the corpus changes, this reconstructs the CURRENT text
    rather than what the model actually saw at decision time. Storing the text
    itself at write time would be more audit-correct.
    """
    docs = json.loads(DOCS_PATH.read_text())
    return {d["doc_id"]: d for d in docs}


def fetch_real_cases(limit=SAMPLE_SIZE):
    """Pull real (retrieved_docs, reasoning) pairs from claims already processed."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, policy_number, claim_type, retrieved_docs, coverage_reasoning
                FROM claim_decisions
                WHERE coverage_reasoning IS NOT NULL
                  AND retrieved_docs IS NOT NULL
                  AND JSON_LENGTH(retrieved_docs) > 0
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()


# A deliberately unfaithful case, hand-written (not model-generated). Without
# this, an eval built only from real history could score 10/10 while never
# demonstrating it can actually CATCH a hallucination - which would make the
# result meaningless. This verifies the judge itself works.
TRAP_CASE = {
    "id": "TRAP",
    "policy_number": "A-11111",
    "claim_type": "auto",
    "doc_ids": ["auto_1"],
    "reasoning": (
        "The claim is approved because comprehensive auto coverage applies and "
        "the policyholder has maintained a no-claims bonus for three consecutive "
        "years, which entitles them to an additional 15% payout uplift under the "
        "loyalty provision."
    ),
    "expect_grounded": False,
}


def build_context(doc_ids, doc_lookup):
    lines = []
    for doc_id in doc_ids:
        doc = doc_lookup.get(doc_id)
        if doc:
            lines.append(f"- {doc['title']}: {doc['text']}")
    return "\n".join(lines)


def judge(context: str, reasoning: str) -> FaithfulnessCheck:
    llm = get_llm()
    structured_llm = llm.with_structured_output(FaithfulnessCheck)
    return structured_llm.invoke(
        "You are evaluating whether a generated explanation is grounded in the "
        "source text provided.\n\n"
        f"SOURCE POLICY CLAUSES:\n{context}\n\n"
        f"GENERATED REASONING:\n{reasoning}\n\n"
        "Determine whether every factual claim in the generated reasoning is "
        "directly supported by the source clauses above. A claim is unsupported "
        "if it states a rule, limit, condition, or entitlement that does not "
        "appear in the source text - even if it sounds plausible or is generally "
        "true of insurance. Restating the claim's own details (dates, amounts, "
        "policy numbers) is not an unsupported claim.\n\n"
        "Set grounded=true only if every claim is supported by the source. "
        "List any unsupported claims specifically."
    )


def main():
    doc_lookup = load_doc_texts()
    real_cases = fetch_real_cases()

    if not real_cases:
        print("No claims found in the audit table. Run some claims first.")
        return

    print(f"Judging {len(real_cases)} real claims + 1 trap case\n")

    results = []

    for row in real_cases:
        retrieved = json.loads(row["retrieved_docs"])
        doc_ids = [d["doc_id"] for d in retrieved]
        context = build_context(doc_ids, doc_lookup)
        if not context:
            print(f"[SKIP] claim {row['id']}: no matching docs in current corpus")
            continue

        verdict = judge(context, row["coverage_reasoning"])
        results.append(verdict.grounded)

        status = "GROUNDED" if verdict.grounded else "UNSUPPORTED"
        print(f"[{status}] claim {row['id']} ({row['policy_number']}, {row['claim_type']}) docs={doc_ids}")
        if not verdict.grounded:
            for c in verdict.unsupported_claims:
                print(f"     ! {c}")

    # Trap case - verifies the judge can actually detect an unfaithful answer.
    trap_context = build_context(TRAP_CASE["doc_ids"], doc_lookup)
    trap_verdict = judge(trap_context, TRAP_CASE["reasoning"])
    trap_caught = trap_verdict.grounded == TRAP_CASE["expect_grounded"]
    print(f"\n[TRAP] judge {'CORRECTLY caught' if trap_caught else 'FAILED to catch'} the planted hallucination")
    if trap_verdict.unsupported_claims:
        for c in trap_verdict.unsupported_claims:
            print(f"     ! {c}")

    if results:
        rate = sum(results) / len(results)
        print(f"\nFaithfulness rate on real claims: {rate:.1%} ({sum(results)}/{len(results)})")
    print(f"Trap case detection: {'PASS' if trap_caught else 'FAIL'}")


if __name__ == "__main__":
    main()