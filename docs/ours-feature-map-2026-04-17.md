# tmux_fork Memory System Feature Map
> Date: 2026-04-17
> Source: ~/Developer/tmux_fork (commit b7bbe723)
> Total lines mapped: ~7,000+ (src + extensions + migrations)

---

## Architecture Overview

**Pattern:** Domain-Driven Design / Clean Architecture (Ports & Adapters)
**Stack:** Python 3.11+, Typer CLI, SQLite (WAL), FTS5, TypeScript Pi Extensions
**DI:** dependency-injector (`Container` class in container.py)

```
Layers (dependency points inward):
  interfaces/cli/    → Typer commands (16 command files, ~2,100 lines)
  application/       → Services (memory, session, cleanup, telemetry, scheduler)
  domain/            → Entities (frozen dataclasses) + Protocols (ports)
  infrastructure/    → SQLite repos, DI container, migrations (15 SQL files, 303 lines)
  ~/.pi/agent/extensions/ → 3 TypeScript extensions (614 lines total)
```

**Data flow:**
```
CLI/Pi Tool → Service (business logic) → Repository (SQL) → SQLite + FTS5
                                         ↕
                              TelemetryService (sidecar tracking)
```

**DI Container** (`container.py`, 284 lines):
- `DatabaseConnection` (Singleton, WAL mode)
- `ObservationRepository` (Singleton)
- `SessionRepositoryImpl` (Singleton)
- `MemoryService` (Singleton, wired to repo + telemetry)
- `SessionService` (Singleton, wired to session repo)
- `CleanupService`, `HealthCheckService`, `TelemetryService`, `SchedulerService`
- `TmuxOrchestrator` (Singleton, safety_mode=False)
- `WorkspaceManager` (lazy singleton via `get_workspace_manager()`)

**Factory functions:** `get_memory_service(db_path?)`, `get_session_service(db_path?)`, `get_memory_service_auto()` (worktree-aware DB detection)

---

## Feature Catalog

### F1: Save Observation
- **Description:** Create a new observation in memory with optional structured metadata
- **Implementation:**
  - `src/interfaces/cli/commands/save.py` (112 lines)
  - `src/application/services/memory_service.py` → `save()` (line ~40)
  - `src/infrastructure/persistence/repositories/observation_repository.py` → `create()` (line ~37)
- **Configuration:** `--db` flag for custom DB path
- **API surface:**
  ```
  memory save "content" [--type TYPE] [--project P] [--topic-key K]
                      [--what W] [--why Y] [--where W] [--learned L]
                      [--metadata JSON] [-m JSON]
  ```
  - Pi tool: `memory_save(content, type, what?, why?, where?, learned?)`
- **ObservationType enum:** decision, bugfix, discovery, pattern, config, preference, architecture, security, performance, learning, session-summary

### F2: Search Observations
- **Description:** Full-text search via FTS5 on observation content
- **Implementation:**
  - `src/interfaces/cli/commands/search.py` (44 lines)
  - `src/application/services/memory_service.py` → `search()` (line ~140)
  - `src/infrastructure/persistence/repositories/observation_repository.py` → `search()` (line ~215)
- **API surface:**
  ```
  memory search "query" [--limit N] [-l N]
  ```
  - Pi tool: `memory_search(query, limit?=5)`

### F3: Get Observation
- **Description:** Retrieve a single observation by full ID or prefix (min 8 chars)
- **Implementation:**
  - `src/interfaces/cli/commands/get.py` (28 lines)
  - `src/application/services/memory_service.py` → `get_by_id()` (line ~155)
  - `src/infrastructure/persistence/repositories/observation_repository.py` → `get_by_id()` (line ~107)
- **API surface:**
  ```
  memory get <observation_id>
  ```
  - Pi tool: `memory_get(id)`

### F4: List Observations
- **Description:** List recent observations with pagination, ordered by timestamp DESC
- **Implementation:**
  - `src/interfaces/cli/commands/list.py` (25 lines)
  - `src/application/services/memory_service.py` → `get_recent()` (line ~160)
  - `src/infrastructure/persistence/repositories/observation_repository.py` → `get_all()` (line ~127)
- **API surface:**
  ```
  memory list [--limit N] [-l N] [--offset N] [-o N]
  ```

### F5: Update Observation
- **Description:** Update content and/or metadata of an existing observation (increments revision_count)
- **Implementation:**
  - `src/interfaces/cli/commands/update.py` (59 lines)
  - `src/application/services/memory_service.py` → `update()` (line ~82)
  - `src/infrastructure/persistence/repositories/observation_repository.py` → `update()` (line ~155)
- **API surface:**
  ```
  memory update <observation_id> [--content "new"] [-c "new"] [--metadata JSON] [-m JSON]
  ```

### F6: Delete Observation
- **Description:** Delete an observation by ID with confirmation prompt (bypass with --force)
- **Implementation:**
  - `src/interfaces/cli/commands/delete.py` (46 lines)
  - `src/application/services/memory_service.py` → `delete()` (line ~180)
  - `src/infrastructure/persistence/repositories/observation_repository.py` → `delete()` (line ~185)
- **API surface:**
  ```
  memory delete <observation_id> [--force] [-f]
  ```

### F7: Context Quick View
- **Description:** Show recent context — session summaries and relevant observations
- **Implementation:**
  - `src/interfaces/cli/commands/context.py` (59 lines)
  - `src/application/services/memory_service.py` → `get_recent()` with type filter
- **API surface:**
  ```
  memory context [--limit N] [-l N] [--type TYPE] [-t TYPE]
  ```

### F8: Structured Event Query
- **Description:** Query memory events with structured filters (agent, run_id, event_type, time). Uses Python-side filtering with scan_limit safety.
- **Implementation:**
  - `src/interfaces/cli/commands/query.py` (282 lines)
  - `src/application/services/memory_service.py` → `query()` (line ~190)
- **API surface:**
  ```
  memory query query [--agent A] [-a A] [--run R] [-r R] [--event-type E] [-e E]
                    [--limit N] [-l N] [--scan-limit N] [--since T] [--json] [-j]
  memory query timeline <run_id> [--scan-limit N]
  ```

### F9: Session Lifecycle Management
- **Description:** Start/end/list/context for work sessions, stored in dedicated `sessions` table
- **Implementation:**
  - `src/interfaces/cli/commands/session.py` (170 lines)
  - `src/application/services/session_service.py` (156 lines)
  - `src/infrastructure/persistence/repositories/session_repository.py` (206 lines)
  - `src/domain/entities/session.py` (88 lines)
- **API surface:**
  ```
  memory session start --project P [-p P] [--goal G] [-g G] [--instructions I] [-i I]
  memory session end [--summary S] [-s S] [--project P] [-p P]
  memory session list [--project P] [-p P] [--limit N] [-l N]
  memory session context [--project P] [-p P] [--limit N] [-l N]
  ```
- **Lifecycle:** start → active → (auto-ended on next start) → ended
- **States:** `is_active()` returns `ended_at is None`

### F10: Compaction Protocol
- **Description:** Save session summaries and file operation manifests for post-compaction recovery
- **Implementation:**
  - `src/interfaces/cli/commands/compact.py` (262 lines)
- **API surface:**
  ```
  memory compact save-summary --goal G [-g G] [--instructions I] [-i I]
                              [--discoveries D] [-d D] [--accomplished A] [-a A]
                              [--next-steps N] [-n N] [--files F] [-f F]
                              [--project P] [-p P]
  memory compact recover [--project P] [-p P]
                        [--summary-limit N] [-s N] [--obs-limit N] [-o N]
  memory compact file-ops [--read R] [-r R] [--written W] [-w W]
                         [--edited E] [-e E] [--project P] [-p P]
  ```
- **Topic keys:** `compact/session-summary`, `compact/file-ops`
- **Type tags:** `session-summary`, `file-ops`

### F11: Database Health Check
- **Description:** Check DB integrity, FTS sync, observation count, DB size. Optional FTS repair.
- **Implementation:**
  - `src/interfaces/cli/commands/health.py` (75 lines)
  - `src/infrastructure/persistence/health_check.py` (HealthCheckService)
- **API surface:**
  ```
  memory health [--verbose] [-v] [--fix] [-f]
  ```

### F12: Database Statistics
- **Description:** Show observation count, FTS entries, DB size, optional telemetry stats, slow query log
- **Implementation:**
  - `src/interfaces/cli/commands/stats.py` (105 lines)
- **API surface:**
  ```
  memory stats [--slow-queries] [-s] [--telemetry] [-t]
  memory clear-slow-queries
  ```

### F13: Database Cleanup
- **Description:** Delete old observations with dry-run preview, optional VACUUM and FTS optimization
- **Implementation:**
  - `src/interfaces/cli/commands/cleanup.py` (72 lines)
  - `src/application/services/cleanup_service.py` (CleanupService)
- **API surface:**
  ```
  memory cleanup [--days N] [-d N] [--dry-run/--no-dry-run] [--vacuum] [-v] [--optimize-ft] [-o]
  ```

### F14: Schedule Tasks
- **Description:** Schedule delayed actions (cron-like) stored in `scheduled_tasks` table
- **Implementation:**
  - `src/interfaces/cli/commands/schedule.py` (101 lines)
  - `src/application/services/scheduler_service.py`
  - `src/infrastructure/persistence/repositories/scheduled_task_repository.py`
- **API surface:**
  ```
  memory schedule add <action> <delay_seconds> [--context C] [-c C]
  memory schedule list
  memory schedule show <id>
  memory schedule cancel <id>
  ```

### F15: Telemetry
- **Description:** Track CLI operations (saves, searches, deletes) with session-based aggregation
- **Implementation:**
  - `src/interfaces/cli/commands/telemetry.py` (424 lines)
  - `src/application/services/telemetry/telemetry_service.py`
  - `src/infrastructure/persistence/repositories/telemetry_repository.py`
- **API surface:**
  ```
  memory telemetry status
  memory telemetry metrics
  memory telemetry events
  memory telemetry session
  memory telemetry export
  memory telemetry cleanup
  memory telemetry dashboard
  ```
- **Tables:** telemetry_events (003), telemetry_metrics (004), telemetry_sessions (005)

### F16: Event Idempotency
- **Description:** Save structured events with deduplication via idempotency_key. Returns existing ID on duplicate.
- **Implementation:**
  - `src/application/services/memory_service.py` → `save_event()` (line ~105)
  - `src/infrastructure/persistence/repositories/observation_repository.py` → `save_event()` (line ~60), `get_by_idempotency_key()` (line ~93)
- **API surface:** Service-only (no direct CLI command; used by orchestration/workflow services)

### F17: Topic Key Upsert
- **Description:** Insert-or-update by `topic_key + project` unique constraint. Preserves original UUID, increments revision_count.
- **Implementation:**
  - `src/infrastructure/persistence/repositories/observation_repository.py` → `upsert_topic_key()` (line ~230), `get_by_topic_key()` (line ~263)
  - SQL: `ON CONFLICT(topic_key, project) DO UPDATE SET content=excluded.content, revision_count=revision_count+1, ...`
- **Note:** Exposed via service layer but not directly via CLI `save` (save creates new observation; upsert is for programmatic use)

### F18: Time Range Query
- **Description:** Retrieve observations within a timestamp range
- **Implementation:**
  - `src/application/services/memory_service.py` → `get_by_time_range()` (line ~185)
  - `src/infrastructure/persistence/repositories/observation_repository.py` → `get_by_timestamp_range()` (line ~240)
- **API surface:** Service-only (no direct CLI command)

### F19: Pi Native Tool: memory_save
- **Description:** RegisterTool allowing agent to save observations without shell commands
- **Implementation:** `~/.pi/agent/extensions/compact-memory-bridge.ts` (line ~155-195)
- **Parameters:** content, type (union literal), what?, why?, where?, learned?
- **Execution:** Delegates to `uv run memory save <content> -m <json>`

### F20: Pi Native Tool: memory_search
- **Description:** RegisterTool allowing agent to search memory without shell commands
- **Implementation:** `~/.pi/agent/extensions/compact-memory-bridge.ts` (line ~197-222)
- **Parameters:** query, limit? (default 5)
- **Execution:** Delegates to `uv run memory search <query> -l <n>`

### F21: Pi Native Tool: memory_get
- **Description:** RegisterTool allowing agent to retrieve full observation by ID
- **Implementation:** `~/.pi/agent/extensions/compact-memory-bridge.ts` (line ~224-241)
- **Parameters:** id (UUID string)
- **Execution:** Delegates to `uv run memory get <id>`

---

## Data Model

### Observation Entity
**File:** `src/domain/entities/observation.py` (92 lines)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `str` | UUID, non-empty | Primary key |
| `timestamp` | `int` | >= 0, milliseconds | Creation time |
| `content` | `str` | non-empty | Main text |
| `metadata` | `dict[str, Any] \| None` | JSON-serializable | Arbitrary structured data |
| `idempotency_key` | `str \| None` | non-empty if set | Dedup key for events |
| `project` | `str \| None` | non-whitespace if set | Project scope (lowercase, stripped) |
| `type` | `str \| None` | `_ALLOWED_TYPES` frozenset | Category classifier |
| `topic_key` | `str \| None` | no spaces | Stable key for upserts |
| `revision_count` | `int` | >= 1 | Tracks updates |
| `session_id` | `str \| None` | - | Links to sessions table |

**Allowed types (14):** decision, architecture, bugfix, pattern, config, discovery, learning, manual, tool_use, file_change, command, file_read, search, session-summary

**Note:** CLI `ObservationType` enum (11 types) is a subset: adds security, performance, preference; omits manual, tool_use, file_change, command, file_read, search. The entity accepts all 14.

### Session Entity
**File:** `src/domain/entities/session.py` (88 lines)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `str` | UUID, non-empty | Primary key |
| `project` | `str` | non-empty | Project name |
| `directory` | `str` | non-empty | Working directory path |
| `started_at` | `int` | >= 0, milliseconds | Start time |
| `ended_at` | `int \| None` | >= 0 if set | End time (None = active) |
| `goal` | `str \| None` | - | Session goal |
| `instructions` | `str \| None` | - | Constraints/instructions |
| `summary` | `str \| None` | - | What was accomplished |

**Methods:** `is_active()` → bool, `duration_ms()` → int | None, `to_metadata()` → dict

### Database Schema (15 migrations, 303 lines total)

| Migration | Purpose | Key changes |
|-----------|---------|-------------|
| 001 | Core table + FTS5 | `observations` (id, timestamp, content, metadata), FTS5 virtual table, 3 triggers (insert/delete/update) |
| 002 | Scheduled tasks | `scheduled_tasks` table |
| 003 | Telemetry events | `telemetry_events` table |
| 004 | Telemetry metrics | `telemetry_metrics` table |
| 005 | Telemetry sessions | `telemetry_sessions` table (with tmux_sessions_killed in 007) |
| 006 | Promise contracts | `promise_contracts` table |
| 008 | Idempotency | `idempotency_key TEXT` column |
| 009 | Topic key | `topic_key TEXT`, unique index (global) |
| 010 | Project + type | `project TEXT`, `type TEXT`, partial indexes |
| 011 | Topic key scoping | Drop global index, create composite `UNIQUE(topic_key, project)` WHERE topic_key NOT NULL |
| 012 | Revision tracking | `revision_count INTEGER NOT NULL DEFAULT 1` |
| 013 | Session linking | `session_id TEXT`, partial index |
| 014 | Sessions table | `sessions` (id, project, directory, started_at, ended_at, goal, instructions, summary), indexes on project + started_at |
| 015 | Sync metadata | `sync_id TEXT`, `synced_at INTEGER`, partial index on sync_id |

**Indexes (observations):**
- `idx_observations_timestamp` (timestamp)
- `idx_observations_topic_key_project` UNIQUE (topic_key, project) WHERE topic_key IS NOT NULL
- `idx_observations_project` (project) WHERE project IS NOT NULL
- `idx_observations_type` (type) WHERE type IS NOT NULL
- `idx_observations_revision_count` (revision_count)
- `idx_observations_session_id` (session_id) WHERE session_id IS NOT NULL
- `idx_observations_sync_id` (sync_id) WHERE sync_id IS NOT NULL

---

## Search & Retrieval

### FTS5 Full-Text Search
- **Virtual table:** `observations_fts USING fts5(content, content='observations', content_rowid='rowid')`
- **Sync mechanism:** 3 triggers (AFTER INSERT, AFTER DELETE, AFTER UPDATE) keep FTS in sync
- **Query flow:** Repository sanitizes query → joins `observations o JOIN observations_fts fts ON o.rowid = fts.rowid` → WHERE MATCH → ORDER BY timestamp DESC

### FTS5 Query Sanitizer
**Location:** `observation_repository.py` → `_sanitize_fts_query()` (line ~295)
- Strips: `* ^ " ' ( ) -`
- Filters FTS5 reserved words: AND, OR, NOT, NEAR, COLUMN
- Returns individual words joined by spaces (OR semantics via FTS5 default)

### UNION Search Gap
**Known limitation:** FTS5 only indexes `content` column. The `topic_key` field is NOT in the FTS index. Searching for `compact/session-summary` works because the `/` and `-` are stripped and `compact` and `session` and `summary` are searched as individual terms — they happen to match content that contains those words. This is fragile (documented in evolution.md as B1 bug, fixed).

### Proactive Keyword Search (G4)
**Location:** `compact-memory-bridge.ts` → `extractKeywords()` + `before_agent_start` handler
- Extracts keywords from user prompt
- Filters: stop words (120+ EN/ES), generic terms (40+ high-frequency English)
- Requires >= 2 meaningful keywords to avoid noise
- Searches top 3 results, injects up to 600 tokens into system prompt

### Query Planner (Memory Service)
**Location:** `memory_service.py` → `query()` (line ~190)
- Fetches up to `scan_limit` observations (default 1000) from DB
- Python-side filtering by: agent_id/from_agent_id, run_id, event_type, since_ms
- Sort by timestamp DESC, apply limit

---

## Compaction & Summarization

### Compact Save-Summary
**CLI:** `memory compact save-summary --goal G [options]`
- Saves as observation with `type="session-summary"`, `topic_key="compact/session-summary"`
- Structured metadata: goal, instructions, discoveries[], accomplished, next_steps[], files[]
- Content auto-generated from structured fields

### Compact Recover
**CLI:** `memory compact recover`
- Retrieves last N session summaries + last M observations
- Separates summaries from regular observations
- Displays structured fields (goal, done, next, files)

### Compact File-Ops
**CLI:** `memory compact file-ops --read R --written W --edited E`
- Saves file operation manifest as observation
- Topic key: `compact/file-ops`
- Tracks which files were read/written/edited during session

### Pi Extension: session_before_compact Hook
**Location:** `compact-memory-bridge.ts` (line ~68)
- Intercepts Pi compaction event
- Saves `preparation.previousSummary` (truncated to 500 chars) as `compact/session-summary`
- Saves file ops (read/written/edited sets) as `compact/file-ops`
- Never blocks compaction (fire-and-forget)

### Pi Extension: session_compact Hook
**Location:** `compact-memory-bridge.ts` (line ~85)
- Reloads cache from DB after compaction
- Searches `compact/session-summary` (last 3)

### Post-Compact Recovery (MEMORY_PROTOCOL)
**Location:** `context-loader.ts` → `MEMORY_PROTOCOL` constant (line ~21)
- Injected into EVERY agent turn via `before_agent_start`
- Instructs agent to run `memory search "compact/session-summary" -l 3` after compaction
- Then `memory get <id>` for full content
- **This is the FIRST instruction in MEMORY_PROTOCOL** (critical for context continuity)

### Recovery Cache
**Location:** `compact-memory-bridge.ts` → `cache` object
- In-memory cache: `{ entries: string[], loadedAt: number }`
- Populated at `session_start` and `session_compact`
- Lazy-reloaded at `before_agent_start` if empty
- Persists across turns (NOT one-shot clear)
- Truncates to 1200 tokens max for injection

---

## Session Management

### Sessions Table (Migration 014)
**Schema:** `sessions (id TEXT PK, project TEXT NOT NULL, directory TEXT NOT NULL, started_at INTEGER NOT NULL, ended_at INTEGER, goal TEXT, instructions TEXT, summary TEXT)`

### Session Repository
**File:** `src/infrastructure/persistence/repositories/session_repository.py` (206 lines)
- `create(session)`, `get_by_id(id)`, `get_recent(project, limit)`, `end_session(id, summary)`, `get_active(project)`
- `get_recent` returns ordered by `started_at DESC`

### Session Service
**File:** `src/application/services/session_service.py` (156 lines)
- `start_session(project, directory, goal?, instructions?)` — auto-ends previous active session for same project
- `end_session(session_id, summary?)` — sets ended_at + summary
- `get_context(project, limit=3)` — for context recovery
- `get_active(project)` — find active session
- `get_active_any()` — find most recent active session across all projects (used by `session end` when `-p` omitted)
- `list_sessions(project, limit=10, include_active=True)` — list with optional active filter

### Session Port
**File:** `src/domain/ports/session_repository.py` (Protocol)
- Methods: create, get_by_id, get_recent, end_session, get_active, get_active_any, update

### CLI Commands
```
memory session start --project P [--goal G] [--instructions I]
memory session end [--summary S] [--project P]
memory session list [--project P] [--limit N]
memory session context [--project P] [--limit N]
```
- Auto-detects project from `Path(os.getcwd()).name` if not provided

---

## Pi Extension Integration

### Extension 1: compact-memory-bridge.ts (214 lines)
**Load order:** 1st (alphabetical)
**Events handled:**

| Event | Action |
|-------|--------|
| `session_start` | Load compact/session-summary cache (last 3) |
| `session_before_compact` | Save summary + file-ops to DB |
| `session_compact` | Reload cache from DB |
| `before_agent_start` | (1) Proactive keyword search from prompt, (2) Inject recovery cache |

**Slash command:** `/compact-memory` (status | clear | search <q>)

### Extension 2: context-loader.ts (269 lines)
**Load order:** 2nd
**Events handled:**

| Event | Action |
|-------|--------|
| `session_start` | Load rules.md + session.md into file cache |
| `turn_start` | Refresh cache if TTL expired (5 min) |
| `before_agent_start` | Inject rules + session (capped 100 lines) + MEMORY_PROTOCOL into system prompt |
| `session_shutdown` | Save session snapshot to DB |

**Slash command:** `/elle-context` (status | reload | show <file>)
**Context dir:** `~/.claude/.context/core/` (rules.md, session.md)
**Cache:** File-based with mtime check + 5min TTL
**MEMORY_PROTOCOL:** ~50 lines of instructions injected every turn (save triggers, format, session close)

### Extension 3: passive-capture.ts (131 lines)
**Load order:** 3rd
**Events handled:**

| Event | Action |
|-------|--------|
| `agent_end` | Extract `## Key Learnings:` from last assistant message, save to DB |

**Slash command:** `/passive-capture` (status | test <text>)
**Regex:** `/^## Key Learnings:\s*\n((?:\s*[-*]?\s*\d*[.)]?\s+.+\n?)+?)(?=\n##|\n$|$)/m`
**Content handling:** Supports both string and structured `[{type:"text", text:...}]` message formats
**Batching:** Single item saved individually with djb2 hash as topic_key; multiple items saved as batch
**Deduplication:** djb2 hash → `topic_key=learning/<hash>`

### RegisterTool: Native Memory Tools (3 tools)
All registered in `compact-memory-bridge.ts`:

| Tool | Params | Delegates to |
|------|--------|-------------|
| `memory_save` | content, type, what?, why?, where?, learned? | `uv run memory save <content> -m <json>` |
| `memory_search` | query, limit? | `uv run memory search <query> -l <n>` |
| `memory_get` | id | `uv run memory get <id>` |

### Other Pi Extensions (non-memory, adjacent)
| Extension | Lines | Purpose |
|-----------|-------|---------|
| `context-session-hub.ts` | 1419 | Checkpoint/session management hub |
| `auto-update.ts` | 73 | Auto-update Pi |
| `compact-header.ts` | 69 | Custom compact header |
| `custom-footer.ts` | 96 | Custom footer |
| `git-guard.ts` | 45 | Git safety |
| `n8n-mcp-bridge.ts` | 332 | n8n integration |
| `n8n-mcp-helper.ts` | 50 | n8n helper |
| `openrouter.ts` | 80 | OpenRouter integration |
| `nvidia-nim.ts` | 29 | NVIDIA NIM |
| `auto-session-name.ts` | 29 | Auto session naming |

---

## Backup & Safety

### Auto-Backup
**Location:** `container.py` → `_auto_backup()` (line ~118)
- Runs on every `create_container()` call (before migrations)
- Only if DB exists and has > 0 observations
- Copies to `data/backups/memory_<timestamp>.db`
- **Rotation:** Keeps only last 3 backups
- Backup failure NEVER blocks container init (silenced)
- Created after data loss incident (agent deleted DB, 45K+ observations lost)

### _ALLOWED_TYPES Validation
**Location:** `observation.py` → `_ALLOWED_TYPES` ClassVar (line ~18)
- Frozenset of 14 valid type strings
- Enforced in `__post_init__` — raises ValueError for invalid types
- Prevents arbitrary type injection

### Input Validation
- All entity fields validated in `__post_init__` (TypeError + ValueError)
- topic_key: no spaces allowed
- project: no whitespace-only strings
- revision_count: >= 1
- content: non-empty
- timestamp: non-negative integer

### CLI Safety
- Delete requires confirmation (`typer.confirm`) unless `--force`
- Cleanup defaults to `--dry-run`
- Health check exits with code 1 if unhealthy

### Telemetry Flush
- All CLI commands that modify data flush telemetry on completion
- Service: `get_telemetry_service(db_path).flush()`

---

## Structured Save

### CLI Flags
```
memory save "content" --type decision --what "X" --why "Y" --where "Z" --learned "L"
```

### Metadata Structure
Structured fields are nested under `metadata.structured`:
```json
{
  "structured": {
    "what": "What was done",
    "why": "Why it matters",
    "where": "files, components",
    "learned": "Key takeaway"
  }
}
```

### Pi Tool Structured Save
`memory_save` tool sends what/why/where/learned as top-level metadata keys (not nested in `structured`):
```json
{
  "type": "bugfix",
  "what": "...",
  "why": "...",
  "where": "...",
  "learned": "..."
}
```

### Legacy JSON Metadata
`--metadata / -m` flag accepts raw JSON, merged with structured fields (structured takes precedence)

### Session Summary Format (compact save-summary)
```json
{
  "type": "session-summary",
  "project": "proj-name",
  "topic_key": "compact/session-summary",
  "structured": {
    "goal": "...",
    "instructions": "...",
    "discoveries": ["d1", "d2"],
    "accomplished": "...",
    "next_steps": ["s1", "s2"],
    "files": ["f1", "f2"]
  }
}
```

---

## Sync Schema

### Migration 015
```sql
ALTER TABLE observations ADD COLUMN sync_id TEXT;
ALTER TABLE observations ADD COLUMN synced_at INTEGER;
CREATE INDEX idx_observations_sync_id ON observations(sync_id) WHERE sync_id IS NOT NULL;
```

### Purpose
- `sync_id`: External sync identifier for cross-device synchronization
- `synced_at`: Unix timestamp (ms) of last sync
- Currently **schema-only** — no sync implementation yet
- Foundation for future multi-device sync

---

## Notable Design Decisions

### 1. Dual Search Architecture (FTS5 + Python filtering)
FTS5 handles content search; structured queries (agent, run_id, event_type) use Python-side filtering with `scan_limit` safety. This avoids complex SQL while keeping FTS5 simple.

### 2. Two Deduplication Mechanisms
- `idempotency_key`: For event deduplication (same event, skip duplicate)
- `topic_key + project`: For content evolution (same topic, update in place)
These serve fundamentally different purposes — idempotency prevents duplicates; topic_key enables progressive refinement.

### 3. Frozen Dataclasses for Entities
All entities use `@dataclass(frozen=True)` with full validation in `__post_init__`. Updates create new objects via `dataclasses.replace()`. This enforces immutability at the domain layer while the DB is mutable.

### 4. Fire-and-Forget Extensions
All 3 Pi extensions wrap every hook in try/catch and never throw. This prevents extension bugs from crashing the agent loop. The tradeoff: silent failures require explicit `/command status` checks.

### 5. Budget-Conscious System Prompt Injection
Total injection budget: ~3,750 tokens (1.9% of 200K window).
- context-loader: ~3,300 tokens (rules + session capped at 100 lines + MEMORY_PROTOCOL)
- compact-memory-bridge: ~450 tokens (keyword results + recovery cache)
Session.md aggressively capped to prevent budget overflow (was 67% before fix).

### 6. Worktree-Aware DB Detection
`get_memory_service_auto()` + `detect_memory_db_path()` automatically uses worktree-specific DB (`<worktree>/.memory/observations.db`) when inside a git worktree, falling back to repo-level `data/memory.db`.

### 7. Progressive Schema Evolution
15 migrations over ~2 months, all additive (ALTER TABLE ADD COLUMN). No destructive migrations. Backward compatibility maintained via `_row_to_observation()` fallback logic (tries DB column, falls back to metadata dict).

### 8. CLI Enum vs Entity Frozenset Mismatch
CLI `ObservationType` enum has 11 types; entity `_ALLOWED_TYPES` frozenset has 14. The entity is more permissive. CLI could reject valid types if extended via programmatic API only. This is a minor inconsistency.

### 9. No Native SQL Type/Project Filtering in Search
Despite having `project` and `type` columns with indexes, the `search()` method only uses FTS5 on content. The `get_all()` method supports `type` filtering but not FTS. A combined approach (FTS5 + SQL WHERE) would be more powerful.

### 10. Dependency Injection with dependency-injector Library
Uses `dependency-injector` (DeclarativeContainer) for production but manual factory functions (`get_memory_service()`) for convenience. Test override via `override_database_for_testing()`.

---

## Complete CLI Surface Summary

```
memory [global options]
  --db / -d                  Database path (default: data/memory.db)

  save        CONTENT        Save observation
  search      QUERY          FTS5 search
  list                       List recent observations
  get         ID             Get observation by ID
  delete      ID             Delete observation
  update      ID             Update observation
  context                    Quick context view
  cleanup                    Delete old observations
  health                     DB health check
  stats                      DB statistics
  clear-slow-queries         Clear slow query log

  session                     Session lifecycle
    start    --project P     Start session
    end      [--summary S]   End session
    list     [--limit N]     List sessions
    context  [--limit N]     Session context for recovery

  compact                     Compaction protocol
    save-summary --goal G    Save session summary
    recover                  Recover context
    file-ops  --read/written/edited  Track file ops

  query                       Structured event queries
    query    --agent/--run/--event-type/--since  Filtered query
    timeline <run_id>        Chronological event view

  schedule                    Task scheduling
    add      ACTION DELAY    Schedule action
    list                    List scheduled tasks
    show     ID             Show task details
    cancel   ID             Cancel task

  telemetry                   Telemetry system
    status                  Telemetry status
    metrics                 Aggregated metrics
    events                  Recent events
    session                 Session summary
    export                  Export data
    cleanup                 Clean expired events
    dashboard               Key metrics view
```

**Total CLI commands:** 30
**Total Pi native tools:** 3
**Total Pi slash commands:** 5 (compact-memory, elle-context, passive-capture, + context-session-hub commands)
