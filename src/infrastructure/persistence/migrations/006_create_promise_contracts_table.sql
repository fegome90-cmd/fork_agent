-- Migration: Create promise_contracts table
-- PromiseContract entity for work orchestration SSOT

CREATE TABLE IF NOT EXISTS promise_contracts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    task TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN (
        'created', 'running', 'verify_passed', 'verify_failed', 'shipped', 'failed'
    )),
    verify_evidence TEXT,
    created_at TEXT,
    updated_at TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_promise_contracts_plan_id ON promise_contracts(plan_id);
CREATE INDEX IF NOT EXISTS idx_promise_contracts_session_id ON promise_contracts(session_id);
CREATE INDEX IF NOT EXISTS idx_promise_contracts_state ON promise_contracts(state);
