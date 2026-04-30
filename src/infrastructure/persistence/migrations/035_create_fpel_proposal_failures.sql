-- 035_create_fpel_proposal_failures.sql
-- FPEL FAIL terminal state: per-proposal failure tracking.
-- Each frozen_proposal_id can have at most one failure row (PK).
-- INSERT OR IGNORE ensures idempotency — first-write-wins for reason.

CREATE TABLE IF NOT EXISTS fpel_proposal_failures (
    frozen_proposal_id TEXT PRIMARY KEY
        REFERENCES frozen_proposals(frozen_proposal_id) ON DELETE CASCADE,
    failed_at TEXT NOT NULL DEFAULT (datetime('now')),
    reason TEXT
);
