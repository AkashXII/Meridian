USE claims_platform;

CREATE TABLE IF NOT EXISTS users (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE claim_decisions
    ADD COLUMN user_id BIGINT NULL,
    ADD CONSTRAINT fk_claim_user FOREIGN KEY (user_id) REFERENCES users(id);

CREATE INDEX idx_claim_user ON claim_decisions (user_id);