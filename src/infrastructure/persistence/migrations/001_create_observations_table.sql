-- Migration 001: Create observations table with FTS5 support
-- This creates the core memory storage system

CREATE TABLE observations (
    id TEXT PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT
);

CREATE INDEX idx_observations_timestamp ON observations (timestamp);

CREATE VIRTUAL TABLE observations_fts USING fts5(
    content,
    content='observations',
    content_rowid='rowid'
);

CREATE TRIGGER observations_after_insert AFTER INSERT ON observations BEGIN
    INSERT INTO observations_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER observations_after_delete AFTER DELETE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
END;

CREATE TRIGGER observations_after_update AFTER UPDATE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
    INSERT INTO observations_fts(rowid, content) VALUES (new.rowid, new.content);
END;
