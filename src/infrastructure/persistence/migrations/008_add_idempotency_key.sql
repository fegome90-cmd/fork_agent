-- Migration 008: Add idempotency_key for deduplication
-- This enables reliable event deduplication at the database level

-- Add idempotency_key column to observations table
ALTER TABLE observations ADD COLUMN idempotency_key TEXT;

-- Create unique index on idempotency_key
-- This enforces deduplication at the database level
-- NULL idempotency_key values are allowed for legacy observations
CREATE UNIQUE INDEX idx_observations_idempotency_key 
ON observations(idempotency_key) 
WHERE idempotency_key IS NOT NULL;

-- Note: For legacy observations without idempotency_key, the index
-- will not include them (WHERE clause filters NULLs). This allows
-- smooth migration without breaking existing data.
