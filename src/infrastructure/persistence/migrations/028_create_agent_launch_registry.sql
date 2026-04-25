-- Canonical agent launch registry — single source of truth for launch ownership.
-- Every launch surface MUST go through this registry before spawning any process.

CREATE TABLE IF NOT EXISTS agent_launch_registry (
    launch_id TEXT PRIMARY KEY,
    canonical_key TEXT NOT NULL,
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

-- Enforce at most one active/in-flight launch per canonical key.
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_launch_per_key
    ON agent_launch_registry (canonical_key)
    WHERE status IN ('RESERVED', 'SPAWNING', 'ACTIVE', 'TERMINATING');

-- Fast lookup by canonical key for dedup checks.
CREATE INDEX IF NOT EXISTS idx_launch_canonical_key ON agent_launch_registry (canonical_key);

-- Fast lookup by status for reconciliation queries.
CREATE INDEX IF NOT EXISTS idx_launch_status ON agent_launch_registry (status);

-- Fast lookup by surface for operator visibility.
CREATE INDEX IF NOT EXISTS idx_launch_surface ON agent_launch_registry (surface);
