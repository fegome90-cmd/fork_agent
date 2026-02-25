-- Migration 005: Create telemetry_sessions table
-- Session-level aggregations for quick session summaries

CREATE TABLE telemetry_sessions (
    session_id TEXT PRIMARY KEY,
    
    -- Session metadata
    workspace_id TEXT,
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    duration_ms INTEGER,
    
    -- Hook metrics
    hooks_fired INTEGER DEFAULT 0,
    hooks_succeeded INTEGER DEFAULT 0,
    hooks_failed INTEGER DEFAULT 0,
    
    -- Agent metrics
    agents_spawned INTEGER DEFAULT 0,
    agents_completed INTEGER DEFAULT 0,
    agents_failed INTEGER DEFAULT 0,
    
    -- Tmux metrics
    tmux_sessions_created INTEGER DEFAULT 0,
    
    -- Memory metrics
    memory_saves INTEGER DEFAULT 0,
    memory_searches INTEGER DEFAULT 0,
    memory_deletes INTEGER DEFAULT 0,
    
    -- Workflow metrics
    workflow_started INTEGER DEFAULT 0,
    workflow_completed INTEGER DEFAULT 0,
    workflow_aborted INTEGER DEFAULT 0,
    
    -- CLI metrics
    cli_commands INTEGER DEFAULT 0,
    cli_errors INTEGER DEFAULT 0,
    
    -- Status
    status TEXT DEFAULT 'active',       -- active/ended/error
    
    -- Environment metadata
    platform TEXT,
    python_version TEXT,
    fork_agent_version TEXT
);

-- Indexes
CREATE INDEX idx_telemetry_sessions_started ON telemetry_sessions(started_at);
CREATE INDEX idx_telemetry_sessions_status ON telemetry_sessions(status);
CREATE INDEX idx_telemetry_sessions_workspace ON telemetry_sessions(workspace_id);
CREATE INDEX idx_telemetry_sessions_ended ON telemetry_sessions(ended_at) WHERE ended_at IS NOT NULL;
