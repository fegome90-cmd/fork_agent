-- Ensure only one active (QUEUED/RUNNING) poll run per task_id
-- Uses partial unique index — only applies to non-terminal statuses
CREATE UNIQUE INDEX IF NOT EXISTS idx_poll_runs_unique_active_task
    ON poll_runs (task_id)
    WHERE status IN ('QUEUED', 'RUNNING');
