USE claims_platform;

ALTER TABLE users
    ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user';

ALTER TABLE claim_decisions
    ADD COLUMN review_status VARCHAR(20) NULL,
    ADD COLUMN reviewed_by BIGINT NULL,
    ADD COLUMN reviewed_at TIMESTAMP NULL,
    ADD COLUMN review_notes TEXT NULL,
    ADD CONSTRAINT fk_claim_reviewer
        FOREIGN KEY (reviewed_by) REFERENCES users(id);

CREATE INDEX idx_review_status ON claim_decisions (review_status);

UPDATE claim_decisions
SET review_status = 'pending'
WHERE final_decision = 'needs_review'
  AND review_status IS NULL;