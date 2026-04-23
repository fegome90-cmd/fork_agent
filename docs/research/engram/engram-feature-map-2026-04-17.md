# Engram Memory System — Complete Analysis Report

> **Repository**: [Gentleman-Programming/engram](https://github.com/Gentleman-Programming/engram)
> **Language**: Go (single binary, no CGO)
> **License**: MIT
> **Stars**: 2,592 | **Forks**: 278

---

## Architecture Overview

Engram is a **persistent memory system for AI coding agents** — agent-agnostic with a single Go binary, SQLite + FTS5 storage, exposed via CLI, HTTP API, MCP server, and TUI.

### High-Level Data Flow

```
Agent (Claude Code / OpenCode / Gemini CLI / Codex / VS Code / Cursor / Windsurf)
    │
    ├─► MCP stdio (engram mcp)
    │       │
    │       └─► Store Layer (Go)
    │               │
    │               └─► SQLite + FTS5 (~/.engram/engram.db)
    │
    ├─► HTTP API (engram serve :7437)
    │
    └─► CLI (engram search, engram save, engram tui, etc.)
```

### Project Structure

```
engram/
├── cmd/engram/main.go          # CLI entry point
├── internal/
│   ├── store/store.go          # Core SQLite + FTS5 engine
│   ├── mcp/mcp.go              # MCP server (15 tools)
│   ├── server/server.go        # HTTP REST API
│   ├── tui/                    # Terminal UI (Bubbletea)
│   ├── sync/                   # Git sync (chunked)
│   ├── project/                # Project detection/normalization
│   ├── obsidian/               # Obsidian export (beta)
│   └── setup/                  # Agent installer
├── skills/                     # Agent behavior protocols
├── DOCS.md                     # Full technical reference
└── README.md
```

---

## Feature Matrix

| Category | Feature | Implementation |
|----------|---------|----------------|
| **Storage Backend** | SQLite + FTS5 | Pure Go (`modernc.org/sqlite`), no CGO |
| **Storage Location** | Default `~/.engram/engram.db` | Configurable via `ENGRAM_DATA_DIR` |
| **Full-Text Search** | FTS5 | Searches title, content, tool_name, type, project, topic_key |
| **Session Management** | Yes | Create, end, summary, recent sessions |
| **Compaction** | Agent-driven | No separate LLM service — agent compresses via mem_save/mem_session_summary |
| **Auto-Save Triggers** | Manual + Passive | Agents call tools proactively; passive capture via "Key Learnings" sections |
| **Privacy** | Two-layer redaction | `<private>...</private>` stripped at plugin + store layers |
| **Sync** | Git chunked | Compressed JSONL chunks + manifest, no merge conflicts |
| **Export/Import** | JSON | Full export/import with INSERT OR IGNORE |
| **MCP Server** | Yes (15 tools) | stdio transport, tool profiles (agent/admin) |
| **HTTP API** | Yes | REST on 127.0.0.1:7437 |
| **TUI** | Yes | Bubbletea-based, Catppuccin Mocha theme |
| **Project Isolation** | Yes | Per-project, per-scope (project/personal) |

---

## Data Model (Schema)

### Core Tables

```sql
-- Sessions: coding session metadata
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    directory TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at TEXT,
    summary TEXT
);

-- Observations: core memory entries
CREATE TABLE observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_id TEXT,
    session_id TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_name TEXT,
    project TEXT,
    scope TEXT NOT NULL DEFAULT 'project',
    topic_key TEXT,
    normalized_hash TEXT,
    revision_count INTEGER NOT NULL DEFAULT 1,
    duplicate_count INTEGER NOT NULL DEFAULT 1,
    last_seen_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- User Prompts: what the user asked
CREATE TABLE user_prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_id TEXT,
    session_id TEXT NOT NULL,
    content TEXT NOT NULL,
    project TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Sync Chunks: tracks imported chunks
CREATE TABLE sync_chunks (
    chunk_id TEXT PRIMARY KEY,
    imported_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Sync State: cloud sync journal
CREATE TABLE sync_state (
    target_key TEXT PRIMARY KEY,
    lifecycle TEXT NOT NULL DEFAULT 'idle',
    last_enqueued_seq INTEGER NOT NULL DEFAULT 0,
    last_ack_seq INTEGER NOT NULL DEFAULT 0,
    ...
);

-- Sync Mutations: change journal for sync
CREATE TABLE sync_mutations (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    target_key TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    op TEXT NOT NULL,
    payload TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'local',
    project TEXT NOT NULL DEFAULT '',
    occurred_at TEXT NOT NULL DEFAULT (datetime('now')),
    acked_at TEXT
);
```

### FTS5 Virtual Tables

```sql
-- Full-text search for observations
CREATE VIRTUAL TABLE observations_fts USING fts5(
    title, content, tool_name, type, project, topic_key,
    content='observations', content_rowid='id'
);

-- Full-text search for user prompts
CREATE VIRTUAL TABLE prompts_fts USING fts5(
    content, project,
    content='user_prompts', content_rowid='id'
);
```

### Indexes

```sql
CREATE INDEX idx_obs_session ON observations(session_id);
CREATE INDEX idx_obs_type ON observations(type);
CREATE INDEX idx_obs_project ON observations(project);
CREATE INDEX idx_obs_created ON observations(created_at DESC);
CREATE INDEX idx_obs_scope ON observations(scope);
CREATE INDEX idx_obs_topic ON observations(topic_key, project, scope, updated_at DESC);
CREATE INDEX idx_obs_dedupe ON observations(normalized_hash, project, scope, type, title, created_at DESC);
CREATE INDEX idx_prompts_session ON user_prompts(session_id);
CREATE INDEX idx_prompts_project ON user_prompts(project);
```

### SQLite Configuration

```sql
PRAGMA journal_mode = WAL;        -- Write-Ahead Logging for concurrency
PRAGMA busy_timeout = 5000;       -- 5 second timeout for locks
PRAGMA synchronous = NORMAL;      -- Balanced durability/performance
PRAGMA foreign_keys = ON;         -- Enforce referential integrity
```

---

## MCP Tools (15 Tools)

### Tool Profiles

| Profile | Tools | Description |
|---------|-------|-------------|
| **agent** | 11 tools | Tools AI agents use during coding sessions |
| **admin** | 4 tools | Tools for TUI, dashboards, manual curation |
| **all** | 15 tools | Everything (default) |

### Core Tools (Eager — always in context)

| Tool | Parameters | Description |
|------|------------|-------------|
| **mem_search** | `query`, `type?`, `project?`, `scope?`, `limit?` | FTS5 full-text search across all memories |
| **mem_save** | `title*`, `content*`, `type?`, `session_id?`, `project?`, `scope?`, `topic_key?` | Save structured observation (What/Why/Where/Learned) |
| **mem_context** | `project?`, `scope?`, `limit?` | Get recent session history (sessions + observations) |
| **mem_session_summary** | `content*`, `session_id?`, `project*` | Save end-of-session summary (Goal/Discoveries/Accomplished/Files) |
| **mem_get_observation** | `id*` | Get full untruncated content by ID |
| **mem_save_prompt** | `content*`, `session_id?`, `project?` | Save user prompt for context |

### Deferred Tools (require ToolSearch)

| Tool | Parameters | Description |
|------|------------|-------------|
| **mem_update** | `id*`, `title?`, `content?`, `type?`, `project?`, `scope?`, `topic_key?` | Update existing observation |
| **mem_delete** | `id*`, `hard_delete?` | Soft-delete (default) or hard-delete |
| **mem_suggest_topic_key** | `type?`, `title?`, `content?` | Suggest stable topic_key for upserts |
| **mem_stats** | — | Show memory statistics |
| **mem_timeline** | `observation_id*`, `before?`, `after?` | Chronological context around observation |
| **mem_session_start** | `id*`, `project*`, `directory?` | Register session start |
| **mem_session_end** | `id*`, `summary?`, `project?` | Mark session completed |
| **mem_capture_passive** | `content*`, `session_id?`, `project?`, `source?` | Extract learnings from "## Key Learnings:" sections |
| **mem_merge_projects** | `from*`, `to*` | Merge project name variants (admin only) |

### Memory Types

```
decision, architecture, bugfix, pattern, config, discovery, learning, manual,
tool_use, file_change, command, file_read, search, preference
```

### Scopes

```
project  (default)  — project-specific memories
personal              — personal notes not tied to any project
```

---

## Compaction Flow

Engram uses **agent-driven compression** — no separate LLM service required. The agent already has the model, context, and API key.

### Two-Level Compression

```
┌─────────────────────────────────────────────────────────┐
│  Level 1: Per-Action (mem_save)                         │
│  ─────────────────────────────────────────────────────  │
│  Structured summaries:                                   │
│    **What**: One sentence — what was done               │
│    **Why**: What motivated it (user request, bug, etc.) │
│    **Where**: Files or paths affected                   │
│    **Learned**: Gotchas, edge cases (omit if none)      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Level 2: Session Summary (mem_session_summary)         │
│  ─────────────────────────────────────────────────────  │
│  Comprehensive end-of-session summary:                  │
│    ## Goal [What we were working on]                    │
│    ## Instructions [User preferences/constraints]       │
│    ## Discoveries [Technical findings, gotchas]         │
│    ## Accomplished [Completed items with details]       │
│    ## Next Steps [What remains for next session]        │
│    ## Relevant Files [path — what changed]              │
└─────────────────────────────────────────────────────────┘
```

### After Compaction Protocol

When the agent receives a compaction/context reset message:

1. **IMMEDIATELY** call `mem_session_summary` with compacted content
2. Then call `mem_context` to recover additional context
3. Only THEN continue working

```python
# Pseudocode for compaction recovery
def after_compaction(compacted_summary):
    mem_session_summary(content=compacted_summary)
    context = mem_context()
    continue_working()
```

### Why No Raw Auto-Capture?

- Raw tool calls (`edit: {file: "foo.go"}`) are **noisy** and pollute FTS5
- Agent's curated summaries are **higher signal**, more searchable
- Doesn't bloat the database
- Shell history and git provide the **raw audit trail**

---

## Save Triggers (Complete List)

### Mandatory Save Events

| Event | Tool | When |
|-------|------|------|
| Bug fix completed | `mem_save` | Immediately after fixing |
| Architecture/design decision | `mem_save` | After deciding |
| Non-obvious discovery | `mem_save` | After discovering |
| Configuration change | `mem_save` | After changing |
| Pattern established | `mem_save` | After establishing |
| Session ending | `mem_session_summary` | Before saying "done" / "listo" |
| After compaction | `mem_session_summary` | Immediately after compaction |

### Passive Capture

| Event | Tool | Trigger |
|-------|------|---------|
| Task completion | `mem_capture_passive` | Text contains `## Key Learnings:` section |
| Auto-extraction | Automatic | Each numbered/bulleted item becomes separate observation |

### Optional Proactive Search

| Event | Tool | When |
|-------|------|------|
| User asks to recall | `mem_context` → `mem_search` | User says "remember", "what did we do" |
| Starting similar work | `mem_search` | Before working on something done before |
| No context on topic | `mem_search` | User mentions topic with no context |

---

## Search Capabilities

### FTS5 Full-Text Search

```sql
-- Searches across:
--   title, content, tool_name, type, project, topic_key

-- Query sanitization: wraps each word in quotes
-- Input:  "fix auth bug"
-- Output: '"fix" "auth" "bug"'
```

### Three-Layer Progressive Disclosure

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 1: mem_search                                         │
│  ────────────────────                                        │
│  Find relevant observations via FTS5                         │
│  Returns previews (first 300 chars)                          │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 2: mem_timeline                                       │
│  ──────────────────────                                      │
│  Drill into chronological neighborhood                       │
│  Shows N observations before/after within same session       │
│  Default: 5 before, 5 after                                  │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 3: mem_get_observation                                │
│  ──────────────────────────────                              │
│  Get full untruncated content by ID                          │
└──────────────────────────────────────────────────────────────┘
```

### Search Filters

| Filter | Parameter | Values |
|--------|-----------|--------|
| Type | `type` | decision, architecture, bugfix, pattern, config, discovery, learning, manual |
| Project | `project` | Normalized project name |
| Scope | `scope` | project, personal |
| Limit | `limit` | 1-20 (default: 10) |

### mem_context (Quick Recent History)

Returns recent sessions and observations — faster than full search for recent work.

---

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENGRAM_DATA_DIR` | Override data directory | `~/.engram` |
| `ENGRAM_PORT` | HTTP server port | `7437` |
| `ENGRAM_PROJECT` | Override project name for MCP server | auto-detected via git |

### CLI Commands

```bash
engram serve [port]        # Start HTTP + MCP server
engram mcp                 # Start MCP server (stdio)
engram mcp --tools=agent   # MCP with specific tool profile
engram mcp --project=foo   # Override project detection
engram tui                 # Launch terminal UI
engram search <query>      # Search from CLI
engram save <title> <msg>  # Save memory from CLI
engram context [project]   # Recent session context
engram stats               # Memory statistics
engram export [file]       # Export to JSON
engram import <file>       # Import from JSON
engram sync                # Git sync export
engram sync --import       # Git sync import
engram sync --status       # Check sync status
engram projects list|consolidate|prune  # Manage projects
engram setup [agent]       # Install agent integration
engram obsidian-export     # Export to Obsidian vault (beta)
```

### Project Detection Priority

1. `--project` flag
2. `ENGRAM_PROJECT` environment variable
3. Git remote origin URL (extracts repo name)
4. Git repository root directory name
5. Current working directory basename

### Project Name Normalization

- **Rule**: lowercase + trimmed + collapsed hyphens/underscores
- **Warning**: If name changes during normalization, warning included in response
- **Similar-project warnings**: Levenshtein distance, substring, case-insensitive matching

---

## Notable Design Decisions

### 1. Go over TypeScript
- **Reason**: Single binary, cross-platform, no runtime
- Initial prototype was TS but was rewritten

### 2. SQLite + FTS5 over Vector DB
- **Reason**: FTS5 covers 95% of use cases
- No ChromaDB/Pinecone complexity

### 3. Agent-Agnostic Core
- **Reason**: Go binary is the brain, thin plugins per-agent
- Not locked to any specific agent

### 4. Agent-Driven Compression
- **Reason**: The agent already has an LLM
- No separate compression service needed

### 5. Privacy at Two Layers
- **Reason**: Defense in depth
- `<private>...</private>` stripped at plugin AND store layers

### 6. Pure Go SQLite (modernc.org/sqlite)
- **Reason**: No CGO means true cross-platform binary distribution

### 7. No Raw Auto-Capture
- **Reason**: Agent's curated summaries are higher signal
- Shell history and git provide raw audit trail

### 8. TUI with Bubbletea
- **Reason**: Interactive terminal UI following Gentleman patterns

### 9. Git Sync with Chunks
- **Reason**: Avoids merge conflicts, compressed, content-hashed

---

## Git Sync Architecture

### Directory Structure

```
.engram/
├── manifest.json        # Index of all chunks (small, git-mergeable)
├── chunks/
│   ├── a3f8c1d2.jsonl.gz   # Chunk 1 (gzipped JSONL)
│   ├── b7d2e4f1.jsonl.gz   # Chunk 2
│   └── ...
└── engram.db           # Local working DB (gitignored)
```

### Why Chunks?

- Each `engram sync` creates a **NEW** chunk — old chunks never modified
- **No merge conflicts**: each dev creates independent chunks
- Chunks are **content-hashed** (SHA-256 prefix) — imported only once
- Manifest is the **only file git diffs** — small and append-only
- **Compressed**: 8 sessions + 10 observations ≈ 2KB

### Sync Commands

```bash
engram sync                    # Export new memories as chunk
engram sync --all              # Export ALL memories from every project
engram sync --import           # Import chunks not yet imported
engram sync --status           # Local vs remote chunk counts
engram sync --project NAME     # Filter export to specific project
```

---

## Dependencies

### Go

| Package | Version | Purpose |
|---------|---------|---------|
| `github.com/mark3labs/mcp-go` | v0.44.0 | MCP protocol implementation |
| `modernc.org/sqlite` | v1.45.0 | Pure Go SQLite (no CGO) |
| `github.com/charmbracelet/bubbletea` | v1.3.10 | Terminal UI |
| `github.com/charmbracelet/lipgloss` | v1.1.0 | Terminal styling |
| `github.com/charmbracelet/bubbles` | v1.0.0 | TUI components |

---

## Integration Matrix

| Agent | One-liner / Setup |
|-------|-------------------|
| Claude Code | `claude plugin marketplace add Gentleman-Programming/engram && claude plugin install engram` |
| OpenCode | `engram setup opencode` |
| Gemini CLI | `engram setup gemini-cli` |
| Codex | `engram setup codex` |
| VS Code | `code --add-mcp '{"name":"engram","command":"engram","args":["mcp"]}'` |
| Cursor / Windsurf | See docs/AGENT-SETUP.md |

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `internal/store/store.go` | Core SQLite + FTS5 engine (113KB) |
| `internal/mcp/mcp.go` | MCP server implementation |
| `internal/server/server.go` | HTTP REST API |
| `internal/sync/sync.go` | Git chunked sync |
| `internal/project/detect.go` | Project detection/normalization |
| `skills/memory-protocol/SKILL.md` | Agent behavior protocol |
| `DOCS.md` | Full technical reference |
| `README.md` | Quick start guide |