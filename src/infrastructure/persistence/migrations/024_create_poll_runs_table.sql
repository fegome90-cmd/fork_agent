-- Poll runs table for autonomous agent polling.

CREATE TABLE IF NOT EXISTS poll_runs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at INTEGER,
    ended_at INTEGER,
    poll_run_dir TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_poll_status ON poll_runs(status);
CREATE INDEX IF NOT EXISTS idx_poll_task ON poll_runs(task_id);
