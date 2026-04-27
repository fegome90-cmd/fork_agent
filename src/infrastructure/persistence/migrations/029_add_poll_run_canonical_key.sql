ALTER TABLE poll_runs ADD COLUMN canonical_key TEXT;
CREATE INDEX idx_poll_runs_canonical_key ON poll_runs(canonical_key) WHERE canonical_key IS NOT NULL;
