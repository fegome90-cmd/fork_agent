-- Migration 019: Rebuild FTS5 with unicode61 tokenizer and include topic_key
-- Fixes: case-insensitive search, unicode/emoji tokenization, topic_key not indexed

-- Drop legacy FTS triggers if they exist
DROP TRIGGER IF EXISTS observations_after_insert;
DROP TRIGGER IF EXISTS observations_after_delete;
DROP TRIGGER IF EXISTS observations_after_update;

-- Drop existing FTS table and triggers
DROP TRIGGER IF EXISTS observations_ai;
DROP TRIGGER IF EXISTS observations_ad;
DROP TRIGGER IF EXISTS observations_au;
DROP TABLE IF EXISTS observations_fts;

-- Recreate with unicode61 tokenizer + topic_key column
CREATE VIRTUAL TABLE observations_fts USING fts5(
    content,
    metadata,
    title,
    topic_key,
    content='observations',
    content_rowid=rowid,
    tokenize='unicode61'
);

-- Rebuild triggers
CREATE TRIGGER observations_ai AFTER INSERT ON observations BEGIN
    INSERT INTO observations_fts(rowid, content, metadata, title, topic_key)
    VALUES (new.rowid, new.content, new.metadata, new.title, new.topic_key);
END;

CREATE TRIGGER observations_ad AFTER DELETE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, content, metadata, title, topic_key)
    VALUES ('delete', old.rowid, old.content, old.metadata, old.title, old.topic_key);
END;

CREATE TRIGGER observations_au AFTER UPDATE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, content, metadata, title, topic_key)
    VALUES ('delete', old.rowid, old.content, old.metadata, old.title, old.topic_key);
    INSERT INTO observations_fts(rowid, content, metadata, title, topic_key)
    VALUES (new.rowid, new.content, new.metadata, new.title, new.topic_key);
END;

-- Rebuild FTS index from existing data
INSERT INTO observations_fts(rowid, content, metadata, title, topic_key)
SELECT rowid, content, metadata, title, topic_key FROM observations;
