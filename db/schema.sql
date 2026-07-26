CREATE DATABASE IF NOT EXISTS claims_platform;
USE claims_platform;

CREATE TABLE IF NOT EXISTS claim_decisions (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- input: both raw and redacted, so we can prove PII scrubbing ran
    raw_claim_text        TEXT NOT NULL,
    redacted_claim_text   TEXT NOT NULL,
    pii_found             JSON,          -- [{entity_type, start, end, score}, ...]

    -- extracted fields
    policy_number   VARCHAR(64),
    claim_type      VARCHAR(32),
    incident_date   VARCHAR(32),         -- kept as-extracted (may be null/malformed); not a DATE on purpose
    amount_requested DECIMAL(12,2),

    -- retrieval trace: what the coverage decision was actually grounded in
    retrieved_docs  JSON,                -- [{doc_id, title, rerank_score}, ...]

    -- decisions
    coverage_decision   VARCHAR(32),     -- approved / denied / needs_review
    coverage_reasoning  TEXT,
    fraud_flagged       BOOLEAN,
    fraud_reason        TEXT,
    final_decision      VARCHAR(32),     -- after fraud override logic

    -- observability
    latency_ms      INT,                 -- total wall-clock for the graph run

    INDEX idx_policy_number (policy_number),
    INDEX idx_created_at (created_at),
    INDEX idx_final_decision (final_decision)
);