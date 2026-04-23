-- Orchestration tasks table for the task board.

CREATE TABLE IF NOT EXISTS orchestration_tasks (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    owner TEXT,
    blocked_by TEXT DEFAULT '[]',
    plan_text TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    approved_by TEXT,
    approved_at INTEGER,
    requested_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_otask_status ON orchestration_tasks(status);
CREATE INDEX IF NOT EXISTS idx_otask_owner ON orchestration_tasks(owner);
CREATE INDEX IF NOT EXISTS idx_otask_created ON orchestration_tasks(created_at);
