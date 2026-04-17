-- Migration: Create sessions table for session lifecycle management
-- Created: 2026-04-16

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    directory TEXT NOT NULL,
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    goal TEXT,
    instructions TEXT,
    summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at);
