-- Migration 011: Fix topic_key scoping
-- Changes global topic_key index to project-scoped composite index.
-- This allows different projects to use the same topic_key values.

-- Drop the old global index
DROP INDEX IF EXISTS idx_observations_topic_key;

-- Create the new project-scoped unique index
-- If project is NULL, it still enforces uniqueness for that NULL project scope
CREATE UNIQUE INDEX idx_observations_topic_key_project
ON observations(topic_key, project)
WHERE topic_key IS NOT NULL;
