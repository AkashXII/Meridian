
import time

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from opentelemetry import propagate
from pydantic import BaseModel, EmailStr
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.audit_store import _connect, record_decision
from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_reviewer,
    verify_password,
)
from app.graph import build_graph
from app.tracing import tracer

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Meridian - Insurance Claims Platform")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = build_graph()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class ClaimRequest(BaseModel):
    claim_text: str


class ReviewRequest(BaseModel):
    decision: str  
    notes: str = ""


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Email already registered")

            cur.execute(
                "INSERT INTO users (email, hashed_password) VALUES (%s, %s)",
                (body.email, hash_password(body.password)),
            )
        conn.commit()
        return {"email": body.email, "message": "registered"}
    finally:
        conn.close()
#ratelimit
@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, hashed_password, role FROM users WHERE email = %s",
                (form.username,),
            )
            user = cur.fetchone()
    finally:
        conn.close()
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user["id"], user["email"], user["role"])
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@app.post("/claims")
@limiter.limit("20/minute")
def submit_claim(request: Request, body: ClaimRequest, user: dict = Depends(get_current_user)):
    with tracer.start_as_current_span("claim_pipeline"):
        carrier = {}
        propagate.inject(carrier)

        start = time.time()
        result = graph.invoke(
            {
                "raw_claim_text": body.claim_text,
                "redacted_claim_text": "",
                "pii_found": [],
                "extracted": None,
                "missing_fields": [],
                "coverage_decision": None,
                "fraud_check": None,
                "retrieved_docs": [],
                "trace_carrier": carrier,
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost_usd": 0.0,
            }
        )
        latency_ms = int((time.time() - start) * 1000)

    record_decision(result, latency_ms, user_id=user["user_id"])

    coverage = result.get("coverage_decision")
    final = result.get("final_decision")
    fraud = result.get("fraud_check")
    extracted = result.get("extracted")
    return {
        "extracted": extracted.model_dump() if extracted else None,
        "missing_fields": result["missing_fields"],
        "policy_number": extracted.policy_number if extracted else None,
        "incident_date": extracted.incident_date if extracted else None,
        "claim_type": extracted.claim_type if extracted else None,
        "amount_requested": extracted.amount_requested if extracted else None,
        "decision": final.decision if final else None,
        "reasoning": final.reasoning if final else None,
        "coverage_decision": coverage.decision if coverage else None,
        "coverage_reasoning": coverage.reasoning if coverage else None,
        "fraud_flagged": fraud.flagged if fraud else None,
        "fraud_reason": fraud.reason if fraud else None,
        "latency_ms": latency_ms,
        "estimated_cost_usd": float(result["estimated_cost_usd"]),
    }

@app.get("/claims")
def my_claims(user: dict = Depends(get_current_user)):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_at, policy_number, claim_type, amount_requested,
                       final_decision, fraud_flagged, latency_ms, review_status
                FROM claim_decisions
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user["user_id"],),
            )
            return {"claims": cur.fetchall()}
    finally:
        conn.close()


@app.get("/claims/{claim_id}")
def claim_detail(claim_id: int, user: dict = Depends(get_current_user)):

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_at, policy_number, claim_type, incident_date,
                       amount_requested, retrieved_docs, coverage_decision,
                       coverage_reasoning, fraud_flagged, fraud_reason,
                       final_decision, latency_ms, estimated_cost_usd,
                       review_status, reviewed_at, review_notes
                FROM claim_decisions
                WHERE id = %s AND user_id = %s
                """,
                (claim_id, user["user_id"]),
            )
            claim = cur.fetchone()
    finally:
        conn.close()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

#reviews
@app.get("/review/queue")
def review_queue(user: dict = Depends(require_reviewer)):
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_at, policy_number, claim_type, amount_requested,
                       coverage_decision, coverage_reasoning, fraud_flagged,
                       fraud_reason, final_decision, review_status
                FROM claim_decisions
                WHERE review_status = 'pending'
                ORDER BY created_at ASC
                """
            )
            return {"queue": cur.fetchall()}
    finally:
        conn.close()


@app.post("/review/{claim_id}")
def resolve_review(claim_id: int, body: ReviewRequest, user: dict = Depends(require_reviewer)):
    if body.decision not in ("approved", "denied"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'denied'")

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, review_status FROM claim_decisions WHERE id = %s",
                (claim_id,),
            )
            claim = cur.fetchone()
            if not claim:
                raise HTTPException(status_code=404, detail="Claim not found")
            if claim["review_status"] != "pending":
                raise HTTPException(
                    status_code=409,
                    detail=f"Claim is not pending review (status: {claim['review_status']})",
                )

            cur.execute(
                """
                UPDATE claim_decisions
                SET review_status = %s,
                    final_decision = %s,
                    reviewed_by = %s,
                    reviewed_at = NOW(),
                    review_notes = %s
                WHERE id = %s
                """,
                (body.decision, body.decision, user["user_id"], body.notes, claim_id),
            )
        conn.commit()
    finally:
        conn.close()

    return {"claim_id": claim_id, "review_status": body.decision, "reviewed_by": user["email"]}