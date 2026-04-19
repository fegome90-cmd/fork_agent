-- Dedicated FTS5 table for agent prompts (separate from observations_fts)

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_text TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    provider TEXT NOT NULL DEFAULT '',
    session_id TEXT,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s','now') * 1000),
    metadata TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS prompts_fts USING fts5(
    prompt_text,
    role,
    model,
    provider,
    session_id,
    content='prompts',
    content_rowid=rowid
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS prompts_ai AFTER INSERT ON prompts BEGIN
    INSERT INTO prompts_fts(rowid, prompt_text, role, model, provider, session_id)
    VALUES (new.rowid, new.prompt_text, new.role, new.model, new.provider, new.session_id);
END;

CREATE TRIGGER IF NOT EXISTS prompts_ad AFTER DELETE ON prompts BEGIN
    INSERT INTO prompts_fts(prompts_fts, rowid, prompt_text, role, model, provider, session_id)
    VALUES ('delete', old.rowid, old.prompt_text, old.role, old.model, old.provider, old.session_id);
END;

CREATE TRIGGER IF NOT EXISTS prompts_au AFTER UPDATE ON prompts BEGIN
    INSERT INTO prompts_fts(prompts_fts, rowid, prompt_text, role, model, provider, session_id)
    VALUES ('delete', old.rowid, old.prompt_text, old.role, old.model, old.provider, old.session_id);
    INSERT INTO prompts_fts(rowid, prompt_text, role, model, provider, session_id)
    VALUES (new.rowid, new.prompt_text, new.role, new.model, new.provider, new.session_id);
END;
