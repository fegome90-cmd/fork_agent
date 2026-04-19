-- Migration 012: Add revision_count column to observations table
-- Tracks how many times an observation has been revised/updated

ALTER TABLE observations ADD COLUMN revision_count INTEGER NOT NULL DEFAULT 1;

-- Create index for efficient querying by revision count
CREATE INDEX IF NOT EXISTS idx_observations_revision_count ON observations(revision_count);
