-- Agent templates for reusable agent definitions (WS5: Team Templates)
CREATE TABLE IF NOT EXISTS agent_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'USER',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    model TEXT NOT NULL DEFAULT '',
    system_prompt TEXT NOT NULL DEFAULT '',
    tools TEXT NOT NULL DEFAULT '[]',     -- JSON array
    skills TEXT NOT NULL DEFAULT '[]',    -- JSON array
    output TEXT NOT NULL DEFAULT '',
    default_reads TEXT NOT NULL DEFAULT '[]',  -- JSON array
    interactive INTEGER NOT NULL DEFAULT 1,
    max_depth INTEGER NOT NULL DEFAULT 1,
    file_path TEXT NOT NULL DEFAULT '',
    team_id TEXT,  -- nullable, references team_definitions.id
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now') * 1000),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now') * 1000)
);

CREATE INDEX IF NOT EXISTS idx_agent_templates_name ON agent_templates(name);
CREATE INDEX IF NOT EXISTS idx_agent_templates_scope ON agent_templates(scope);
CREATE INDEX IF NOT EXISTS idx_agent_templates_team ON agent_templates(team_id);
CREATE INDEX IF NOT EXISTS idx_agent_templates_status ON agent_templates(status);

-- Team definitions
CREATE TABLE IF NOT EXISTS team_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    agent_names TEXT NOT NULL DEFAULT '[]',  -- JSON array
    team_dir TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now') * 1000),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now') * 1000)
);
