-- 032_add_poll_run_launch_id.sql
-- Link PollRun to the authoritative AgentLaunch lifecycle record.

ALTER TABLE poll_runs ADD COLUMN launch_id TEXT
    REFERENCES agent_launch_registry(launch_id)
    ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_poll_launch_id
    ON poll_runs(launch_id);
