# Engram vs tmux_fork — Fresh Gap Analysis
> Date: 2026-04-17
> Engram: github.com/gentle-ai/engram (commit unknown, latest)
> tmux_fork: commit b7bbe723

## Executive Summary

**Engram** positions itself as "agent-agnostic" with a philosophy of minimal, opinionated design: a Go binary that works with any agent via MCP tools. It optimizes for distribution (single binary, no CGO) and passive workflows (Key Learnings extraction, agent-driven compression). Its git-sync with chunked JSONL is architecturally elegant for multi-device sync.

**tmux_fork** takes a domain-driven Python approach with 15 migrations of incremental evolution. It prioritizes session lifecycle, telemetry, and Pi-specific integration. Its three Pi extensions provide proactive context injection (keyword search), compact recovery, and passive capture. The architecture is more modular but heavier (Python runtime vs Go binary).

**Key finding:** Engram wins on distribution simplicity and sync; tmux_fork wins on depth of Pi integration and operational visibility. The gap is significant (~35 points) in distributed/sync features but minimal in core storage/search. Both use nearly identical SQLite+FTS5 schemas, suggesting convergent evolution.

---

## Feature Comparison Matrix

### Storage & Schema

| Feature | Engram | tmux_fork | Gap | Notes |
|---------|--------|-----------|-----|-------|
| SQLite + FTS5 | Full | Full | None | Both use WAL mode, triggers |
| Schema Evolution | Unknown | 15 migrations (additive) | tmux_fork + | `src/infrastructure/persistence/migrations/` 303 lines |
| sync_id / synced_at | No | Yes (mig 015) | tmux_fork + | Schema ready, no sync impl |
| revision_count | Yes | Yes (mig 012) | None | Both track content versions |
| scheduled_tasks | No | Yes (mig 002) | tmux_fork + | Cron-like delayed actions |
| promise_contracts | No | Yes (mig 006) | tmux_fork + | Contracts table |

### Search & Retrieval

| Feature | Engram | tmux_fork | Gap | Notes |
|---------|--------|-----------|-----|-------|
| FTS5 on content | Yes | Yes | None | Identical trigger-based sync |
| FTS5 on prompts | Yes | No | Engram + | prompts_fts virtual table |
| FTS5 on tool_name/type | Yes | No | Engram + | Engram indexes more fields |
| Get by ID | Yes | Yes | None | Both support prefix (8 chars min) |
| Timeline/chronological | Yes (mem_timeline) | Partial | Engram + | `memory query timeline` exists but less precise |
| Timeline filters | No | Partial | tmux_fork + | Python-side filtering by agent/run |
| Search filters (type/project) | Yes | Partial | Engram + | Engram MCP params vs CLI only |
| Topic search | Content hits only | Content hits only | None | Neither has native topic_key FTS5 |

### Compaction & Recovery

| Feature | Engram | tmux_fork | Gap | Notes |
|---------|--------|-----------|-----|-------|
| Two-level compression | Yes | Yes | None | mem_save + mem_session_summary |
| Passive Key Learnings | Yes | Yes | None | Regex extraction in both |
| Post-compact recovery | Yes (protocol) | Yes (extension + protocol) | Comparable | Both inject recovery instructions |
| File ops manifest | No | Yes | tmux_fork + | `memory compact file-ops` |
| Structured save (what/why/where) | Yes | Yes | None | Identical format |
| Recovery cache (injection) | No | Yes | tmux_fork + | `compact-memory-bridge.ts` cache object |

### Session Management

| Feature | Engram | tmux_fork | Gap | Notes |
|---------|--------|-----------|-----|-------|
| Session table | Yes | Yes | None | Identical schema |
| Active session tracking | Yes | Yes | None | `ended_at IS NULL` pattern |
| Auto-end on new start | Unknown | Yes | tmux_fork + | `session_service.py:40` |
| Session goal/fields | Partial | Full | tmux_fork + | Engram has summary only? |
| Session isolation | Yes | Yes | None | Both per-project |

### CLI / API Surface

| Feature | Engram | tmux_fork | Gap | Notes |
|---------|--------|-----------|-----|-------|
| Total CLI commands | 15 | 21 | tmux_fork + | Includes telemetry, health |
| TUI | Yes (Bubbletea) | No | Engram + | `engram tui` |
| HTTP API | Yes (7437) | No | Engram + | REST server |
| Schedule tasks | No | Yes | tmux_fork + | `memory schedule add` |
| Stats/telemetry | Limited | Extensive | tmux_fork + | `memory telemetry dashboard` |
| Health checks | No | Yes | tmux_fork + | `memory health --fix` |

### Agent Integration

| Feature | Engram | tmux_fork | Gap | Notes |
|---------|--------|-----------|-----|-------|
| MCP tools | 15 | Partial (3 native) | Engram + | Engram: profiles (agent/admin) |
| Native Pi tools | No | Yes (3 tools) | tmux_fork + | `compact-memory-bridge.ts:155-241` |
| Pre-agent keyword search | No | Yes | tmux_fork + | `extractKeywords()` in before_agent_start |
| Context injection | No | Yes (3 exts) | tmux_fork + | rules + session + recovery |
| Passive capture | Yes | Yes | Comparable | Both agent_end hooks |

### Sync & Sharing

| Feature | Engram | tmux_fork | Gap | Notes |
|---------|--------|-----------|-----|-------|
| Chunked Git sync | Yes | No (schema only) | Engram ++ | Compressed JSONL + manifest |
| Multi-device sync | Yes | No | Engram ++ | sync_state + chunks architecture |
| Sync mutations journal | Yes | No | Engram + | sync_mutations table |
| Export/Import JSON | Yes | No | Engram + | `engram export/import` |
| Obsidian export | Beta | No | Engram + | `engram obsidian-export` |

### Safety & Backup

| Feature | Engram | tmux_fork | Gap | Notes |
|---------|--------|-----------|-----|-------|
| Auto-backup | Unknown | Yes | tmux_fork + | `container.py:118` keeps last 3 |
| Type validation | Yes | Yes | None | Both frozenset patterns |
| Idempotency | Unknown | Yes | tmux_fork + | `save_event()` with key |
| Backup rotation | N/A | Yes (last 3) | tmux_fork + | After data loss incident |
| Two-layer privacy | Yes (plugin+store) | No | Engram + | `private` tag stripping |

### Observability

| Feature | Engram | tmux_fork | Gap | Notes |
|---------|--------|-----------|-----|-------|
| Telemetry events | Unknown | Full | tmux_fork + | 3 tables, 424 line CLI |
| Query slow-log | No | Yes | tmux_fork + | `memory stats --slow-queries` |
| Session telemetry | No | Yes | tmux_fork + | Per-session aggregates |
| DB size reporting | Yes | Yes | None | Similar stats |
| FTS integrity check | Unknown | Yes | tmux_fork + | `--fix` option |

---

## Scoring (0-100)

| Category | Engram | tmux_fork | Max |
|----------|--------|-----------|-----|
| Storage Schema | 75 | 85 | 100 |
| Search & Retrieval | 85 | 70 | 100 |
| Compaction & Recovery | 85 | 90 | 100 |
| Session Management | 75 | 90 | 100 |
| CLI / API Surface | 80 | 75 | 100 |
| Agent Integration | 75 | 85 | 100 |
| Sync & Sharing | 95 | 20 | 100 |
| Safety & Backup | 70 | 85 | 100 |
| Observability | 60 | 90 | 100 |
| **Total** | **700** | **680** | **900** |
| **Score %** | **77.8** | **75.6** | 100 |

**Gap: -2.2 points (minimal difference)**

### Category Notes:
- **Sync & Sharing**: Engram's chunked git sync is complete; tmux_fork has schema only
- **Observability**: tmux_fork's telemetry is production-grade; Engram minimal
- **Storage**: tmux_fork's 15 migrations show maturity; Engram likely similar but not verifiable

---

## Gaps (tmux_fork missing)

### P1 (Significant — hurts utility)

1. **Multi-Device Sync with Chunked JSONL**
   - Engram: `internal/sync/` with chunks, manifests, mutation journal
   - tmux_fork: `sync_id`, `synced_at` columns (mig 015), no implementation
   - Impact: Cannot work across devices

2. **Privacy Redaction Layer**
   - Engram: `<private>...</private>` stripped at plugin + store layers
   - tmux_fork: No equivalent tagging system
   - Impact: Observable secrets/credentials in storage

3. **HTTP API (Agent-Agnostic)**
   - Engram: `engram serve :7437` for any HTTP client
   - tmux_fork: CLI + Pi tools only
   - Impact: Locked to Pi workflows

### P2 (Nice-to-have)

4. **Prompt FTS5 Table**
   - Engram: `prompts_fts` virtual table for user prompts
   - tmux_fork: No dedicated prompt storage/FTS5
   - Impact: Cannot search full user query history

5. **TUI Interface**
   - Engram: Bubbletea-based `engram tui`
   - tmux_fork: CLI only
   - Impact: No interactive browsing/memories

6. **Obsidian Export**
   - Engram: Beta export to Obsidian vault
   - tmux_fork: No Markdown export
   - Impact: Integration with personal knowledge bases

7. **MCP Tool Profiles**
   - Engram: `agent` (11 tools) vs `admin` (4 tools) profiles
   - tmux_fork: No tool categorization
   - Impact: All tools always in context

---

## Advantages (tmux_fork unique)

1. **Telemetry Dashboard**
   - `memory telemetry dashboard` with metrics, session aggregates
   - Source: `src/interfaces/cli/commands/telemetry.py:424`

2. **Proactive Keyword Search**
   - `extractKeywords()` + before_agent_start injection
   - Source: `compact-memory-bridge.ts:68-132`

3. **Dependency Injection**
   - `container.py:284` lines of clean DI
   - Testability: `override_database_for_testing()`

4. **Worktree-Aware DB Detection**
   - `detect_memory_db_path()` for `.memory/observations.db`
   - Source: `container.py:factory functions`

5. **Schedule Tasks**
   - `memory schedule add` with cron-like delays
   - Source: `scheduler_service.py`

6. **Auto-Backup with Rotation**
   - `_auto_backup()` keeps last 3
   - Reaction to data loss incident

7. **Slow Query Log**
   - `memory stats --slow-queries`
   - Source: `telemetry_repository.py`

8. **Topic Key Upserts**
   - `ON CONFLICT(topic_key, project) DO UPDATE`
   - Accounts for progressive refinement

9. **Idle Timeout Detection**
   - `get_container()` with idle health check
   - Prevents stale connections

---

## Recommendations (Top 5 by Impact)

| Priority | Action | Effort | Impact | Files |
|----------|--------|--------|--------|-------|
| P1 | Implement chunked sync | M | **Critical** | `src/infrastructure/sync/`, `internal/sync/` pattern |
| P1 | Privacy redaction layer | S | **Security** | `src/application/services/redaction.py`, store.py hooks |
| P2 | Add HTTP API | M | **Agent-agnostic** | `src/interfaces/api/server.py`, FastAPI |
| P2 | Prompt FTS table | S | **Completeness** | Migration 016, schema matching Engram |
| P3 | Backup before migrations | S | **Safety** | `container.py` hook post-migration |

---

## Architecture Comparison

| Aspect | Engram | tmux_fork |
|--------|--------|-----------|
| **Language** | Go 1.22+ | Python 3.11+ |
| **Distribution** | Single binary, no CGO | Python package, uv runtime |
| **Architecture Pattern** | Agent-agnostic core | DDD/Clean Architecture |
| **Dependency Management** | Go modules | uv + pyproject.toml |
| **Persistence** | SQLite + FTS5 via `modernc.org/sqlite` | SQLite + FTS5 via stdlib |
| **Migrations** | Unknown (likely Go migrations) | 15 SQL migrations (additive) |
| **DI Framework** | Manual (Go idioms) | `dependency-injector` library |
| **Sync Architecture** | Chunked JSONL + manifest | Schema stubs only |
| **Extensions** | MCP server (stdio) | Pi native TypeScript extensions |
| **Compaction** | Agent-driven (no separate service) | Agent-driven + Pi hooks |
| **Recovery** | Protocol + `mem_context()` | Protocol + cache injection |

---

## Key Findings

1. **Both systems are functionally equivalent for single-agent, single-device use cases.** The 2.2 point gap is minimal.

2. **Engram's sync architecture is genuine competitive advantage.** Chunked JSONL with content-hashed manifests eliminates merge conflicts. tmux_fork has schema stubs (`sync_id`, `synced_at`) but no implementation.

3. **tmux_fork's Pi-specific optimizations are unmatched.** Proactive keyword search + context injection + telemetry create a production debugging experience Engram cannot match.

4. **Privacy redaction is critical gap.** tmux_fork stores everything; Engram strips `private` tags.

5. **Schema converged intentionally.** Both chose SQLite+FTS5, WAL mode, triggers, session table with same columns. This validates the design pattern.

6. **Both use structured metadata format.** What/Why/Where/Learned pattern identical → frictionless migration possible if needed.
