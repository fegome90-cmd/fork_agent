-- Migration 021: Fix topic_key unique index for NULL projects
-- Standard SQL and SQLite consider NULLs distinct in UNIQUE indexes.
-- This migration uses IFNULL to ensure uniqueness for project-agnostic topic keys.

DROP INDEX IF EXISTS idx_observations_topic_key_project;

CREATE UNIQUE INDEX idx_observations_topic_key_project
ON observations(topic_key, IFNULL(project, ''))
WHERE topic_key IS NOT NULL;
