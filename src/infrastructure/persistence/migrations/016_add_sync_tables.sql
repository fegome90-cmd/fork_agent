-- Migration: Add sync tables for incremental sync and mutation tracking
-- Created: 2026-04-17

-- Sync chunks: tracks imported chunks to avoid re-import
CREATE TABLE IF NOT EXISTS sync_chunks (
    chunk_id TEXT PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'local',
    imported_at INTEGER NOT NULL DEFAULT (strftime('%s','now') * 1000),
    observation_count INTEGER NOT NULL DEFAULT 0,
    checksum TEXT NOT NULL
);

-- Sync mutations: change journal for incremental sync
CREATE TABLE IF NOT EXISTS sync_mutations (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    entity TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    op TEXT NOT NULL CHECK(op IN ('insert','update','delete')),
    payload TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'local',
    project TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now') * 1000)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_sync_mutations_seq ON sync_mutations(seq);
CREATE INDEX IF NOT EXISTS idx_sync_mutations_entity ON sync_mutations(entity, entity_key);
CREATE INDEX IF NOT EXISTS idx_sync_mutations_source ON sync_mutations(source);
CREATE INDEX IF NOT EXISTS idx_sync_mutations_project ON sync_mutations(project);

-- Sync status: single row for global sync state
CREATE TABLE IF NOT EXISTS sync_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_export_at INTEGER,
    last_import_at INTEGER,
    last_export_seq INTEGER DEFAULT 0,
    mutation_count INTEGER DEFAULT 0
);

-- Initialize sync status row
INSERT OR IGNORE INTO sync_status (id) VALUES (1);
