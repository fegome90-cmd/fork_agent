-- Migration: Add sync metadata columns for future sync support
-- Created: 2026-04-16

ALTER TABLE observations ADD COLUMN sync_id TEXT;
ALTER TABLE observations ADD COLUMN synced_at INTEGER;

CREATE INDEX IF NOT EXISTS idx_observations_sync_id ON observations(sync_id) WHERE sync_id IS NOT NULL;
