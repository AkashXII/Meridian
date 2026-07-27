CREATE DATABASE IF NOT EXISTS claims_platform;
USE claims_platform;

CREATE TABLE IF NOT EXISTS claim_decisions (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


    raw_claim_text        TEXT NOT NULL,
    redacted_claim_text   TEXT NOT NULL,
    pii_found             JSON,         

    -- extracted fields
    policy_number   VARCHAR(64),
    claim_type      VARCHAR(32),
    incident_date   VARCHAR(32),        
    amount_requested DECIMAL(12,2),

   
    retrieved_docs  JSON,              

    -- decisions
    coverage_decision   VARCHAR(32),     
    coverage_reasoning  TEXT,
    fraud_flagged       BOOLEAN,
    fraud_reason        TEXT,
    final_decision      VARCHAR(32),   

    -- observability
    latency_ms      INT,                 

    INDEX idx_policy_number (policy_number),
    INDEX idx_created_at (created_at),
    INDEX idx_final_decision (final_decision)
);