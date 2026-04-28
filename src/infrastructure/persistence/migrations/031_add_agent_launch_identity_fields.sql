-- 031_add_agent_launch_identity_fields.sql
-- ADR-001: Canonical Agent Identity — add role, parent_launch_id, model, output_artifact.

-- Parent launch reference for delegation causality (NOT compression lineage).
-- Nullable: legacy rows and top-level launches have no parent.
-- ON DELETE SET NULL: preserves child linkage even if parent is pruned.
ALTER TABLE agent_launch_registry ADD COLUMN parent_launch_id TEXT
    REFERENCES agent_launch_registry(launch_id)
    ON DELETE SET NULL;

-- Agent role (e.g., "poll-agent", "explorer", "implementer").
-- Nullable: legacy rows created before migration 031.
-- Post-migration launches MUST provide role (enforced at service layer).
ALTER TABLE agent_launch_registry ADD COLUMN role TEXT;

-- Model identifier used for the launch (e.g., "glm-5-turbo", "deepseek-v4-flash").
-- Nullable: for legacy compatibility.
ALTER TABLE agent_launch_registry ADD COLUMN model TEXT;

-- Path to the output artifact written by the agent.
-- Nullable: set after spawn completes, not at claim time.
ALTER TABLE agent_launch_registry ADD COLUMN output_artifact TEXT;

-- Index for ancestry queries (cycle detection walks parent chain).
CREATE INDEX IF NOT EXISTS idx_launch_parent
    ON agent_launch_registry (parent_launch_id);

-- Index for role-based filtering and legacy migration queries.
CREATE INDEX IF NOT EXISTS idx_launch_role
    ON agent_launch_registry (role);

-- Index for model-based analytics.
CREATE INDEX IF NOT EXISTS idx_launch_model
    ON agent_launch_registry (model);
