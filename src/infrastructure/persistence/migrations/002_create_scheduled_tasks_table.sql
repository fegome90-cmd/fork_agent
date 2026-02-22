-- Migration 002: Create scheduled_tasks table
-- This creates the scheduled task execution system

CREATE TABLE scheduled_tasks (
    id TEXT PRIMARY KEY,
    scheduled_at INTEGER NOT NULL,
    action TEXT NOT NULL,
    context TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at INTEGER NOT NULL
);

CREATE INDEX idx_scheduled_tasks_scheduled_at ON scheduled_tasks (scheduled_at);
CREATE INDEX idx_scheduled_tasks_status ON scheduled_tasks (status);
