-- Migration 003: Create telemetry_events table
-- This creates the core telemetry event storage system
-- Stores all events: hooks, agents, tmux, memory, workflow, cli, traces

CREATE TABLE telemetry_events (
    -- Primary key
    id TEXT PRIMARY KEY,
    
    -- Event identification
    event_type TEXT NOT NULL,          -- e.g., "hook.fire", "agent.spawn", "memory.save"
    event_category TEXT NOT NULL,      -- session/hook/agent/tmux/memory/workflow/cli/trace
    
    -- Temporal data
    timestamp INTEGER NOT NULL,        -- Unix timestamp (ms) when event occurred
    received_at INTEGER NOT NULL,      -- Unix timestamp (ms) when we received it
    
    -- Context
    session_id TEXT,                   -- fork_agent session
    correlation_id TEXT,               -- For linking related events
    parent_event_id TEXT,              -- For event hierarchies
    
    -- Event data (JSON)
    attributes TEXT NOT NULL,          -- JSON object with event-specific data
    metrics TEXT,                      -- JSON object with metric values
    
    -- Processing metadata
    processed INTEGER DEFAULT 0,       -- 0=pending, 1=processed
    processed_at INTEGER,
    
    -- Retention
    expires_at INTEGER NOT NULL        -- Unix timestamp for TTL-based cleanup
);

-- Indexes for common queries
CREATE INDEX idx_telemetry_events_type ON telemetry_events(event_type);
CREATE INDEX idx_telemetry_events_category ON telemetry_events(event_category);
CREATE INDEX idx_telemetry_events_session ON telemetry_events(session_id);
CREATE INDEX idx_telemetry_events_timestamp ON telemetry_events(timestamp);
CREATE INDEX idx_telemetry_events_expires ON telemetry_events(expires_at);
CREATE INDEX idx_telemetry_events_correlation ON telemetry_events(correlation_id);

-- Composite indexes for analytics
CREATE INDEX idx_telemetry_events_type_timestamp ON telemetry_events(event_type, timestamp);
CREATE INDEX idx_telemetry_events_session_type ON telemetry_events(session_id, event_type);
CREATE INDEX idx_telemetry_events_category_timestamp ON telemetry_events(event_category, timestamp);
