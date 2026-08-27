import json
import os
import time
from pathlib import Path
import pymysql
from dotenv import load_dotenv
from app.llm import get_judge_llm
from app.models import FaithfulnessCheck
load_dotenv()
SAMPLE_SIZE = 20
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
    from app.chunker import ingest_policy_documents
    docs = ingest_policy_documents(str(Path(__file__).parent.parent / "data"))
    return {d["doc_id"]: d for d in docs}


def fetch_real_cases(limit=SAMPLE_SIZE):
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

TRAP_CASE_2 = {
    "id": "TRAP2",
    "policy_number": "A-22222",
    "claim_type": "auto",
    "doc_ids": ["auto_2"],
    "reasoning": (
        "The claim is denied because the vehicle was being driven more than "
        "50 miles from the policyholder's registered address at the time of "
        "the incident, which voids comprehensive coverage under the "
        "geographic use restriction."
    ),
    "expect_grounded": False,
}
def build_context(doc_ids, doc_lookup):
    lines = []
    resolved = 0
    for doc_id in doc_ids:
        doc = doc_lookup.get(doc_id)
        if doc:
            lines.append(f"- {doc['title']}: {doc['text']}")
            resolved += 1
    return "\n".join(lines), resolved


def judge(context: str, reasoning: str) -> FaithfulnessCheck:
    llm = get_judge_llm()
    structured_llm = llm.with_structured_output(FaithfulnessCheck, method="json_mode")
    return structured_llm.invoke(
        "You are evaluating whether a generated insurance-claim decision explanation "
        "is grounded in the source policy clauses provided. Respond with ONLY a JSON "
        "object matching this exact shape: "
        "{\"grounded\": true or false, \"unsupported_claims\": [list of strings]}. "
        "No other text before or after the JSON.\n\n"
        f"SOURCE POLICY CLAUSES:\n{context}\n\n"
        f"GENERATED REASONING:\n{reasoning}\n\n"
        "A claim is UNSUPPORTED only if it introduces a rule, limit, condition, "
        "exception, or entitlement that is NOT present anywhere in the source clauses "
        "above - something invented.\n\n"
        "The following are NOT unsupported, and must NOT be flagged:\n"
        "- Restating the claim's own facts (dates, amounts, policy numbers).\n"
        "- Arithmetic or logical comparisons between a source clause's limit and the "
        "claim's own amount (e.g. '$2,800 is within the $10,000 limit' is valid if "
        "$10,000 actually appears in the source).\n"
        "- Reasonable negative inferences from a condition that IS in the source "
        "(e.g. noting an exclusion doesn't apply because its trigger condition is "
        "absent from the claim details).\n"
        "- Phrasing not lifted word-for-word from the source, as long as the underlying "
        "rule it describes is actually present.\n\n"
        "Only flag a claim if the RULE ITSELF is fabricated - not because the wording "
        "differs, and not because it involves a comparison or inference over "
        "information that IS present.\n\n"
        "Set grounded=true only if no claim is fabricated in this sense. List any "
        "genuinely unsupported claims specifically."
    )


def judge_with_retry(context: str, reasoning: str, max_retries: int = 3) -> FaithfulnessCheck:
    for attempt in range(max_retries):
        try:
            return judge(context, reasoning)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 * (attempt + 1)
            print(f"     (judge call failed: {type(e).__name__}, retrying in {wait}s...)")
            time.sleep(wait)


def main():
    doc_lookup = load_doc_texts()
    real_cases = fetch_real_cases()

    if not real_cases:
        print("No claims found in the audit table. Run some claims first.")
        return

    print(f"Judging {len(real_cases)} real claims + 1 trap case\n")

    results = []

    for row in real_cases:
        if "Overridden to needs_review" in row["coverage_reasoning"]:
            print(f"[SKIP] claim {row['id']}: pre-fix legacy format, reasoning mixes override text")
            continue

        retrieved = json.loads(row["retrieved_docs"])
        doc_ids = [d["doc_id"] for d in retrieved]
        context, resolved = build_context(doc_ids, doc_lookup)

        if resolved < len(doc_ids):
            print(f"[SKIP] claim {row['id']}: {len(doc_ids) - resolved}/{len(doc_ids)} "
                  f"doc_id(s) not in current corpus (stale row, pre-corpus-switch)")
            continue
        if not context:
            print(f"[SKIP] claim {row['id']}: no matching docs in current corpus")
            continue

        try:
            verdict = judge_with_retry(context, row["coverage_reasoning"])
        except Exception as e:
            print(f"[SKIP] claim {row['id']}: judge call failed after retries ({type(e).__name__})")
            continue

        results.append(verdict.grounded)

        status = "GROUNDED" if verdict.grounded else "UNSUPPORTED"
        print(f"[{status}] claim {row['id']} ({row['policy_number']}, {row['claim_type']}) docs={doc_ids}")
        if not verdict.grounded:
            for c in verdict.unsupported_claims:
                print(f"     ! {c}")

    trap_context, trap_resolved = build_context(TRAP_CASE["doc_ids"], doc_lookup)
    try:
        trap_verdict = judge_with_retry(trap_context, TRAP_CASE["reasoning"])
        trap_caught = trap_verdict.grounded == TRAP_CASE["expect_grounded"]
        print(f"\n[TRAP] judge {'CORRECTLY caught' if trap_caught else 'FAILED to catch'} the planted hallucination")
        if trap_verdict.unsupported_claims:
            for c in trap_verdict.unsupported_claims:
                print(f"     ! {c}")
    except Exception as e:
        trap_caught = False
        print(f"\n[TRAP] judge call failed after retries ({type(e).__name__}) - could not verify trap detection")

    if results:
        rate = sum(results) / len(results)
        print(f"\nFaithfulness rate on real claims: {rate:.1%} ({sum(results)}/{len(results)})")
    else:
        print("\nNo claims were successfully judged - all were skipped or failed.")
    print(f"Trap case detection: {'PASS' if trap_caught else 'FAIL'}")


if __name__ == "__main__":
    main()