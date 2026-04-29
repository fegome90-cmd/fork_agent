-- 033_create_fpel_tables.sql
-- FPEL (Frozen Proposal Evidence Loop) tables for authorization gating.
-- Stores frozen proposals, sealed verdicts, checker reports, and FPEL status per target.

-- Frozen proposals: immutable snapshots of task/workflow proposals at freeze time.
CREATE TABLE IF NOT EXISTS frozen_proposals (
    frozen_proposal_id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    content TEXT NOT NULL,
    lifecycle TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (lifecycle IN ('ACTIVE', 'SUPERSEDED')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_frozen_proposals_target
    ON frozen_proposals(target_id);

CREATE INDEX IF NOT EXISTS idx_frozen_proposals_lifecycle
    ON frozen_proposals(lifecycle);

-- Sealed verdicts: successful seal outputs, one per frozen_proposal_id (UNIQUE).
CREATE TABLE IF NOT EXISTS sealed_verdicts (
    frozen_proposal_id TEXT PRIMARY KEY
        REFERENCES frozen_proposals(frozen_proposal_id)
        ON DELETE CASCADE,
    verdict TEXT NOT NULL DEFAULT 'SEALED_PASS',
    sealed_at TEXT NOT NULL,
    content_hash TEXT NOT NULL
);

-- FPEL status per target: tracks the current authorization state.
CREATE TABLE IF NOT EXISTS fpel_status (
    target_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'NOT_FROZEN',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Checker reports: evidence from individual checkers on frozen proposals.
CREATE TABLE IF NOT EXISTS fpel_checker_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    frozen_proposal_id TEXT NOT NULL
        REFERENCES frozen_proposals(frozen_proposal_id)
        ON DELETE CASCADE,
    checker_id TEXT NOT NULL,
    verdict TEXT NOT NULL,
    report_content TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (frozen_proposal_id, checker_id)
);

CREATE INDEX IF NOT EXISTS idx_checker_reports_frozen
    ON fpel_checker_reports(frozen_proposal_id);
