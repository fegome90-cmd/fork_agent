-- Migration 013: Add session_id column to observations table
-- Links observations to specific agent sessions for grouping and retrieval.
-- session_id: Optional identifier for the session that created this observation.

-- Add session_id column to observations table (nullable)
ALTER TABLE observations ADD COLUMN session_id TEXT;

-- Create index on session_id for efficient querying by session
CREATE INDEX IF NOT EXISTS idx_observations_session_id ON observations(session_id) WHERE session_id IS NOT NULL;
