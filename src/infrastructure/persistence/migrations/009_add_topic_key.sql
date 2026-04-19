-- Migration 009: Add topic_key for upsert support
-- Enables topic_key-based upserts: same topic_key overwrites, not duplicates.
-- Distinct from idempotency_key (deduplication) — topic_key is for content evolution.

-- Add topic_key column to observations table
ALTER TABLE observations ADD COLUMN topic_key TEXT;

-- Create unique index on topic_key
-- NULL topic_key values are allowed for observations that don't use upserts
CREATE UNIQUE INDEX idx_observations_topic_key
ON observations(topic_key)
WHERE topic_key IS NOT NULL;
