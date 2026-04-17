-- Migration 010: Add project and type columns for scoping support
-- Enables project-level and type-level filtering in memory queries.
-- project: Optional namespace/project scope identifier.
-- type: Optional observation type/category classifier.

-- Add project column to observations table (nullable)
ALTER TABLE observations ADD COLUMN project TEXT;

-- Add type column to observations table (nullable)
ALTER TABLE observations ADD COLUMN type TEXT;

-- Create index on project for efficient filtering by project scope
CREATE INDEX idx_observations_project ON observations(project) WHERE project IS NOT NULL;

-- Create index on type for efficient filtering by observation type
CREATE INDEX idx_observations_type ON observations(type) WHERE type IS NOT NULL;
