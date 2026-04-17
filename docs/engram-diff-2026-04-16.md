# Engram vs Pi Memory — Gap Analysis

> **Generated:** 2026-04-16
> **Engram:** Go single-binary, 2592 stars, MIT
> **Pi Memory:** Python DDD, CLI-first, SQLite+FTS5

---

## 1. Feature Comparison Table

| # | Feature | Engram | Pi Memory | Gap | Priority | Effort |
|---|---------|--------|-----------|-----|----------|--------|
| 1 | SQLite + FTS5 storage | Go modernc.org/sqlite, no CGO | Python sqlite3 stdlib + FTS5 | **none** | — | — |
| 2 | Full-text search | FTS5 across title, content, tool_name, type, project, topic_key | FTS5 across content only (no title, type, project columns) | **medium** | P1 | ~40 LOC (migration + reindex) |
| 3 | Topic-key upsert | Yes, with normalized_hash dedup | Yes, with UNIQUE index | **none** | — | — |
| 4 | Idempotent saves | sync_id field | idempotency_key field | **none** | — | — |
| 5 | Session management | Dedicated sessions table, start/end/summary | session_id column on observations only (no sessions table) | **large** | P1 | ~200 LOC (table + service + CLI) |
| 6 | MCP server | 15 tools, stdio transport, tool profiles (agent/admin) | None — CLI only | **large** | P0 | ~500 LOC (MCP server + tool bindings) |
| 7 | Agent-native tool exposure | registerTool via MCP (15 tools) | No registerTool, CLI commands only | **large** | P0 | ~500 LOC (same as #6) |
| 8 | Compaction flow | Agent-driven: save compacted summary + recover context | None — manual cleanup only | **large** | P0 | ~100 LOC (protocol doc + hooks) |
| 9 | Post-compaction recovery | `mem_session_summary` + `mem_context` → resume | None | **large** | P0 | ~50 LOC (protocol + CLI) |
| 10 | Session summaries | Structured: Goal/Discoveries/Accomplished/Next Steps/Files | None | **large** | P1 | ~150 LOC (entity + service + migration) |
| 11 | Passive capture | `mem_capture_passive` extracts "Key Learnings" sections | MemoryHook with gates (toggle, policy, rate-limit) | **small** | P2 | ~30 LOC (minor feature parity) |
| 12 | Privacy/redaction | Two-layer: `<private>` stripped at plugin + store | None | **medium** | P2 | ~60 LOC (store-layer redaction) |
| 13 | Git sync (chunked) | SHA-256 hashed chunks, compressed JSONL, merge-free | None | **large** | P2 | ~400 LOC (sync service) |
| 14 | HTTP API | REST on :7437 | None | **medium** | P3 | ~300 LOC (FastAPI endpoint wrapper) |
| 15 | TUI | Bubbletea, Catppuccin Mocha | None (Typer CLI only) | **medium** | P3 | ~800 LOC (Textual or Rich TUI) |
| 16 | Project isolation | Per-project, per-scope (project/personal) | Per-project only (no personal scope) | **small** | P2 | ~20 LOC (scope column + filter) |
| 17 | Project detection/normalization | Git remote → repo name, 5-level priority | Manual `--project` flag | **medium** | P1 | ~80 LOC (detection heuristics) |
| 18 | Scope (project/personal) | `project` and `personal` scopes | Project only | **small** | P2 | ~20 LOC (column + default) |
| 19 | Export/Import (JSON) | Full export/import with INSERT OR IGNORE | None | **medium** | P2 | ~150 LOC (CLI commands) |
| 20 | Observation types | 14 types (decision, architecture, bugfix, pattern, config, discovery, learning, manual, tool_use, file_change, command, file_read, search, preference) | Free-form text (no enum enforcement) | **small** | P2 | ~30 LOC (enum + validation) |
| 21 | Timeline view | `mem_timeline` — N before/after within session | CLI `query timeline` (basic) | **small** | P2 | ~50 LOC (session-aware timeline) |
| 22 | Deduplication | normalized_hash + duplicate_count tracking | idempotency_key only | **medium** | P2 | ~80 LOC (hash + count columns) |
| 23 | Soft delete | deleted_at column + soft/hard toggle | Hard delete only | **small** | P3 | ~40 LOC (column + service change) |
| 24 | Stats | Memory stats (counts by type, project, etc.) | CLI `stats` (basic) | **small** | P3 | ~50 LOC (richer queries) |
| 25 | Multi-agent integration | Claude Code, OpenCode, Gemini CLI, Codex, VS Code, Cursor, Windsurf | tmux_fork ecosystem only | **large** | P3 | N/A (by design — we serve our ecosystem) |
| 26 | Telemetry | None | Full telemetry: events, sessions, metrics tables | **none** (we lead) | — | — |
| 27 | Scheduled tasks | None | `scheduled_tasks` table + SchedulerService | **none** (we lead) | — | — |
| 28 | Hook system | None (uses agent plugins) | Full hook system: SessionStart, SubagentStart/Stop, PreToolUse, Workflow events | **none** (we lead) | — | — |
| 29 | Promise contracts | None | `promise_contracts` table with state machine | **none** (we lead) | — | — |
| 30 | Query planning (v2) | Simple FTS5 query sanitization | Concept extraction, synonym generation, multi-query UNION, context-aware additions | **none** (we lead) | — | — |
| 31 | Health monitoring | None | CLI `health` + slow query log | **none** (we lead) | — | — |
| 32 | Cleanup/retention | None | CleanupService with days-based retention | **none** (we lead) | — | — |
| 33 | Obsidian export | Beta | None | **small** | P3 | ~100 LOC (markdown exporter) |
| 34 | Tool profiles | agent (11 tools) vs admin (4 tools) vs all (15) | N/A | **small** | P3 | Design decision (when MCP is built) |
| 35 | Auto project consolidation | `projects consolidate` — merge name variants | None | **small** | P3 | ~60 LOC (CLI command) |

---

## 2. Critical Gaps (P0 — Must Fix)

### P0-1: No MCP Server / Agent-Native Tool Exposure

**What's missing:** Engram exposes 15 MCP tools (mem_search, mem_save, mem_context, mem_session_summary, etc.) that any MCP-compatible agent can call directly. Pi Memory has zero tool registration — agents must shell out to CLI.

**Why it matters:** Without MCP, no agent (Claude Code, OpenCode, Cursor, VS Code) can use Pi Memory natively. This is the #1 adoption blocker. The CLI-first approach forces string parsing and loses structured return types.

**Implementation suggestion:**
- File: `src/interfaces/mcp/server.py` (new)
- Approach: Use `mcp` Python SDK (`pip install mcp`)
- Expose 6 core tools first: `memory_search`, `memory_save`, `memory_get`, `memory_context`, `memory_update`, `memory_delete`
- Run as stdio transport (same as Engram)
- Each tool maps directly to existing `MemoryService` methods
- Estimated: ~500 LOC

### P0-2: No Compaction Flow

**What's missing:** Engram defines a clear protocol: after agent compaction, immediately call `mem_session_summary` to persist the compacted context, then call `mem_context` to recover. Pi Memory has no compaction awareness at all.

**Why it matters:** Without compaction support, long sessions lose all context when the agent's context window fills up. This is the #2 usability gap — the system accumulates memories but can't help the agent recover them after a reset.

**Implementation suggestion:**
- File: `src/interfaces/cli/commands/compact.py` (new) + update `MEMORY_PROTOCOL`
- Add `session save-summary` CLI command that stores Goal/Discoveries/Accomplished/Next Steps/Files
- Add `session recover` CLI command that returns recent summaries + recent observations
- Wire into hooks.json: `PostCompaction` → auto-save summary
- Estimated: ~150 LOC (commands + protocol doc)

### P0-3: No Post-Compaction Recovery

**What's missing:** Engram's `mem_context` returns recent sessions + observations as a structured recovery payload. Pi Memory's `context` command exists but doesn't prioritize session summaries or recent work context.

**Why it matters:** This is the recovery half of compaction. Without it, even if summaries are saved, the agent doesn't know how to load them back.

**Implementation suggestion:**
- Enhance existing `src/interfaces/cli/commands/context.py`
- Query: last 3 session summaries + last 20 observations for current project
- Return structured markdown with sections: Recent Sessions, Key Decisions, Active Patterns
- Estimated: ~80 LOC (query enhancement)

---

## 3. Architecture Differences

### Storage
| Aspect | Engram | Pi Memory |
|--------|--------|-----------|
| Language | Go (single binary, no CGO) | Python 3.11+ (uv, requires runtime) |
| SQLite driver | modernc.org/sqlite (pure Go) | sqlite3 stdlib |
| Migrations | Inline in store.go | Incremental SQL files in `migrations/` |
| Timestamps | TEXT (ISO 8601) | INTEGER (Unix ms) |
| IDs | INTEGER AUTOINCREMENT | TEXT (UUID) |
| PRAGMA config | WAL, busy_timeout=5000, synchronous=NORMAL, foreign_keys=ON | Not explicitly configured |

### Access Pattern
| Aspect | Engram | Pi Memory |
|--------|--------|-----------|
| Primary interface | MCP stdio (15 tools) | CLI (Typer) |
| Secondary | HTTP REST API | None |
| Tertiary | CLI, TUI | — |
| Agent integration | Native (MCP tools are first-class) | Indirect (shell commands) |

### Compaction
| Aspect | Engram | Pi Memory |
|--------|--------|-----------|
| Trigger | Agent-driven (protocol in SKILL.md) | None |
| Recovery | `mem_session_summary` + `mem_context` | None |
| Scope | Per-session structured summaries | N/A |

### Scope
| Aspect | Engram | Pi Memory |
|--------|--------|-----------|
| Projects | Per-project isolation with auto-detection | Per-project (manual --project flag) |
| Personal scope | `personal` scope for cross-project notes | Project-only |
| Multi-agent | 7+ agents supported | tmux_fork ecosystem only |

---

## 4. What Pi Memory Does Better (Honest Assessment)

### Telemetry System (Engram has none)
Pi Memory has a **complete observability stack**: `telemetry_events`, `telemetry_sessions`, `telemetry_metrics` tables with proper indexing, event correlation, expiration, and structured querying. Engram has zero telemetry. This is a significant operational advantage for debugging and monitoring.

### Query Planning v2 (Engram uses basic sanitization)
Pi Memory's `QueryPlanner` extracts concepts, generates synonyms, builds multi-query UNIONs, and adds context-aware terms (e.g., "where" → "endpoint/route"). Engram just quotes each word. Our retrieval is meaningfully smarter.

### Hook System (Engram uses agent plugins)
Pi Memory has a **full event-driven hook system**: SessionStart, SubagentStart/Stop, PreToolUse guards, Workflow lifecycle events. Engram relies on each agent's plugin system. Our hooks are centralized and composable.

### Scheduled Tasks (Engram has none)
`SchedulerService` + `scheduled_tasks` table for deferred actions. Useful for cleanup, reminders, periodic sync. Engram has no scheduling.

### Promise Contracts (Engram has none)
`promise_contracts` table with a full state machine (created → running → verify_passed → shipped → failed). This enables verifiable work tracking that Engram doesn't support.

### Retention/Cleanup (Engram has none)
`CleanupService` with configurable days-based retention, VACUUM, and FTS optimize. Engram data grows forever with no built-in cleanup.

### DDD Architecture
Clean separation: domain entities (frozen dataclasses), application services, infrastructure repositories, interface adapters. Engram is a monolithic Go store. Our architecture is more testable and extensible.

### Idempotent Events
`save_event()` with idempotency_key and INSERT OR IGNORE. Engram's sync_id serves a similar purpose but our implementation includes event metadata (run_id, task_id, agent_id, correlation_id) that enables rich event tracing.

### Health Monitoring
CLI `health` command + slow query logging. Engram has no health checks or query performance monitoring.

---

## 5. What Engram Does Better

### MCP Server (15 tools, production-grade)
Engram's MCP implementation is the reference. Tool profiles (agent vs admin), stdio transport, proper error handling. Pi Memory has zero MCP support. This is the single biggest gap.

### Compaction Protocol
Engram defines a clear, agent-agnostic compaction flow: save summary → recover context. The protocol is documented in a SKILL.md that any agent follows. Pi Memory has nothing equivalent.

### Session Management
Dedicated `sessions` table with start/end/summary. Agents explicitly start/end sessions. Pi Memory only has a `session_id` column — no session lifecycle management.

### Agent-Agnostic Design
Engram works with 7+ agents out of the box. Pi Memory is tightly coupled to the tmux_fork ecosystem. Engram's Go binary is the universal brain; each agent just needs an MCP client.

### Git Sync
Chunked, compressed, content-hashed JSONL sync that avoids merge conflicts. This enables team memory sharing. Pi Memory has no sync mechanism.

### Project Detection
5-level priority (flag → env → git remote → git root → cwd). Pi Memory requires manual `--project` flag or environment variable.

### Privacy/Redaction
Two-layer `<private>...</private>` stripping. Defense in depth. Pi Memory stores everything as-is.

### TUI
Bubbletea-based interactive terminal UI. Pi Memory is CLI-only.

### Scope (project/personal)
Engram supports `personal` scope for cross-project notes. Pi Memory is project-only.

### Soft Delete
`deleted_at` column with soft/hard delete toggle. Pi Memory only supports hard delete.

### Simplicity
Single Go binary, zero dependencies beyond SQLite. `engram mcp` just works. Pi Memory requires Python 3.11+, uv, and multiple dependencies.

---

## 6. Recommended Sprint Plan

### Sprint 1: Agent Integration (P0) — ~2-3 days

| # | Item | File(s) | Approach |
|---|------|---------|----------|
| 1.1 | MCP server skeleton | `src/interfaces/mcp/server.py` (new) | Use `mcp` Python SDK, stdio transport |
| 1.2 | Core MCP tools (6) | `src/interfaces/mcp/tools.py` (new) | `memory_search`, `memory_save`, `memory_get`, `memory_context`, `memory_update`, `memory_delete` — wrap existing `MemoryService` |
| 1.3 | MCP entry point | `pyproject.toml` | Add `memory-mcp` console script |
| 1.4 | Compaction protocol | `docs/COMPACTION_PROTOCOL.md` (new) | Document save-summary + recover flow |
| 1.5 | Session summary command | `src/interfaces/cli/commands/session.py` (new) | `session save-summary` with structured fields |
| 1.6 | Session recover command | `src/interfaces/cli/commands/session.py` | `session recover` — last 3 summaries + 20 observations |
| 1.7 | MCP session tools | `src/interfaces/mcp/tools.py` | Add `memory_session_summary`, `memory_session_recover` to MCP |

### Sprint 2: Data Model Parity (P1) — ~2 days

| # | Item | File(s) | Approach |
|---|------|---------|----------|
| 2.1 | Sessions table | `migrations/` (new migration) | `CREATE TABLE sessions (id, project, directory, started_at, ended_at, summary)` |
| 2.2 | Expand FTS5 columns | `migrations/` | Rebuild FTS5 to include `type`, `project`, `topic_key` alongside `content` |
| 2.3 | Project detection | `src/infrastructure/project/detection.py` (new) | Git remote → repo name, fallback chain like Engram |
| 2.4 | Personal scope | `migrations/` + `MemoryService` | Add `scope` column (default 'project'), filter in queries |
| 2.5 | Session service | `src/application/services/session_service.py` (new) | start(), end(), summary(), recent() methods |

### Sprint 3: Quality & Safety (P2) — ~2 days

| # | Item | File(s) | Approach |
|---|------|---------|----------|
| 3.1 | Privacy redaction | `src/infrastructure/persistence/redaction.py` (new) | Strip `<private>...</private>` at store layer |
| 3.2 | Deduplication | `migrations/` + `ObservationRepository` | Add `normalized_hash` + `duplicate_count`, upsert logic |
| 3.3 | Soft delete | `migrations/` + `MemoryService` | Add `deleted_at`, change delete() to soft by default |
| 3.4 | Export/Import | `src/interfaces/cli/commands/export.py` (new) | JSON export/import with INSERT OR IGNORE |
| 3.5 | Type enum | `src/domain/entities/observation.py` | Define `ObservationType` enum, validate in `save()` |

### Sprint 4: Polish (P3) — ~3-4 days

| # | Item | File(s) | Approach |
|---|------|---------|----------|
| 4.1 | HTTP API | `src/interfaces/api/server.py` (new) | FastAPI wrapper around MemoryService |
| 4.2 | TUI | `src/interfaces/tui/` (new) | Textual-based, session browsing + search |
| 4.3 | Obsidian export | `src/interfaces/cli/commands/export.py` | Markdown files with frontmatter |
| 4.4 | Project consolidation | `src/interfaces/cli/commands/project.py` (new) | Merge project name variants |
| 4.5 | SQLite PRAGMA config | `src/infrastructure/persistence/connection.py` | Add WAL, busy_timeout=5000, synchronous=NORMAL, foreign_keys=ON |

---

## 7. Scores

### Overall Parity Score: 52/100

| Category | Weight | Engram | Pi Memory | Parity |
|----------|--------|--------|-----------|--------|
| **Agent Integration** | 25% | 10/10 | 1/10 | **10%** |
| **Search & Retrieval** | 15% | 7/10 | 8/10 | **114%** (we lead) |
| **Data Model** | 15% | 8/10 | 6/10 | **75%** |
| **Compaction & Recovery** | 15% | 9/10 | 1/10 | **11%** |
| **Observability** | 10% | 2/10 | 9/10 | **450%** (we dominate) |
| **Hook/Event System** | 10% | 3/10 | 9/10 | **300%** (we dominate) |
| **Scheduling & Workflows** | 5% | 1/10 | 8/10 | **800%** (we dominate) |
| **Sync & Sharing** | 5% | 8/10 | 0/10 | **0%** |

### Summary
- **We dominate:** Telemetry, hooks, scheduling, query planning, retention — the "platform" layer
- **We trail badly:** Agent integration (MCP), compaction/recovery, session management — the "agent experience" layer
- **The bet:** Pi Memory is a better **platform** but a worse **agent tool**. The MCP server (Sprint 1) flips the equation.
