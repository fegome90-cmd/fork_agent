-- Add launch metadata required for authoritative polling cleanup and conservative dedupe.

ALTER TABLE poll_runs ADD COLUMN launch_method TEXT;
ALTER TABLE poll_runs ADD COLUMN launch_pane_id TEXT;
ALTER TABLE poll_runs ADD COLUMN launch_pid INTEGER;
ALTER TABLE poll_runs ADD COLUMN launch_pgid INTEGER;
ALTER TABLE poll_runs ADD COLUMN launch_recorded_at INTEGER;
