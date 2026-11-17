USE claims_platform;

-- Retrieval-confidence escalation (app/retrieval/confidence.py, app/decision.py).
-- Run once, after review_schema.sql. audit_store.py writes these columns,
-- so claims will fail to be recorded until this migration has been applied.
ALTER TABLE claim_decisions
    ADD COLUMN retrieval_top_score      DECIMAL(6,4) NULL,
    ADD COLUMN low_retrieval_confidence BOOLEAN      NULL,
    ADD COLUMN escalation_reason        TEXT         NULL;

CREATE INDEX idx_low_retrieval_confidence ON claim_decisions (low_retrieval_confidence);
