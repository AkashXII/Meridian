import json
import os

from overrides import final
import pymysql
from dotenv import load_dotenv
from typer.cli import state

load_dotenv()


def _connect():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "claims_platform"),
        cursorclass=pymysql.cursors.DictCursor,
    )


def record_decision(state: dict, latency_ms: int, user_id: int | None = None) -> None:
    extracted = state.get("extracted")
    coverage = state.get("coverage_decision")
    fraud = state.get("fraud_check")
    final = state.get("final_decision")          
    final_decision_value = final.decision if final else None
    review_status = "pending" if final_decision_value == "needs_review" else None

    row = {
        "raw_claim_text": state.get("raw_claim_text"),
        "redacted_claim_text": state.get("redacted_claim_text"),
        "pii_found": json.dumps(state.get("pii_found") or []),
        "policy_number": extracted.policy_number if extracted else None,
        "claim_type": extracted.claim_type if extracted else None,
        "incident_date": extracted.incident_date if extracted else None,
        "amount_requested": extracted.amount_requested if extracted else None,
        "retrieved_docs": json.dumps(state.get("retrieved_docs") or []),
        "coverage_decision": coverage.decision if coverage else None,
        "coverage_reasoning": coverage.reasoning if coverage else None,
        "fraud_flagged": fraud.flagged if fraud else None,
        "fraud_reason": fraud.reason if fraud else None,
        "final_decision": final_decision_value,
        "review_status": review_status,
        "latency_ms": latency_ms,
        "user_id": user_id,
        "input_tokens": state.get("input_tokens"),
        "output_tokens": state.get("output_tokens"),
        "estimated_cost_usd": state.get("estimated_cost_usd"),
    }

    sql = """
        INSERT INTO claim_decisions (
            raw_claim_text, redacted_claim_text, pii_found,
            policy_number, claim_type, incident_date, amount_requested,
            retrieved_docs, coverage_decision, coverage_reasoning,
            fraud_flagged, fraud_reason, final_decision, latency_ms,
            input_tokens, output_tokens, estimated_cost_usd, user_id,
            review_status
        ) VALUES (
            %(raw_claim_text)s, %(redacted_claim_text)s, %(pii_found)s,
            %(policy_number)s, %(claim_type)s, %(incident_date)s, %(amount_requested)s,
            %(retrieved_docs)s, %(coverage_decision)s, %(coverage_reasoning)s,
            %(fraud_flagged)s, %(fraud_reason)s, %(final_decision)s, %(latency_ms)s,
            %(input_tokens)s, %(output_tokens)s, %(estimated_cost_usd)s, %(user_id)s,
            %(review_status)s
        )
    """

    try:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(sql, row)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[audit_store] failed to record decision: {e}")