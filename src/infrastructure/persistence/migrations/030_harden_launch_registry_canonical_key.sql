-- Harden agent_launch_registry: add CHECK constraints for canonical_key.
-- Also clean any existing rows with empty canonical_key (data integrity fix).

-- Step 1: Delete any rows with empty canonical_key (orphaned from previous bugs).
DELETE FROM agent_launch_registry WHERE canonical_key = '' OR canonical_key IS NULL;

-- Step 2: Recreate table with CHECK constraint.
-- SQLite does not support ALTER TABLE ADD CHECK, so we recreate.
-- Note: IF NOT EXISTS prevents issues if this migration runs twice.
CREATE TABLE IF NOT EXISTS agent_launch_registry_new (
    launch_id TEXT PRIMARY KEY,
    canonical_key TEXT NOT NULL CHECK(canonical_key != ''),
    surface TEXT NOT NULL,
    owner_type TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    backend TEXT,
    status TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    reserved_at INTEGER,
    spawn_started_at INTEGER,
    spawn_confirmed_at INTEGER,
    ended_at INTEGER,
    lease_expires_at INTEGER,
    termination_handle_type TEXT,
    termination_handle_value TEXT,
    process_pid INTEGER,
    process_pgid INTEGER,
    tmux_session TEXT,
    tmux_pane_id TEXT,
    prompt_digest TEXT,
    request_fingerprint TEXT,
    last_error TEXT,
    quarantine_reason TEXT
);

-- Copy existing data.
INSERT OR IGNORE INTO agent_launch_registry_new SELECT * FROM agent_launch_registry;

-- Swap tables.
DROP TABLE agent_launch_registry;
ALTER TABLE agent_launch_registry_new RENAME TO agent_launch_registry;

-- Recreate indexes.
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_launch_per_key
    ON agent_launch_registry (canonical_key)
    WHERE status IN ('RESERVED', 'SPAWNING', 'ACTIVE', 'TERMINATING');

CREATE INDEX IF NOT EXISTS idx_launch_canonical_key ON agent_launch_registry (canonical_key);
CREATE INDEX IF NOT EXISTS idx_launch_status ON agent_launch_registry (status);
CREATE INDEX IF NOT EXISTS idx_launch_surface ON agent_launch_registry (surface);
