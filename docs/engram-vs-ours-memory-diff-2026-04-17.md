# Engram vs tmux_fork Memory — Detailed Diff
> Date: 2026-04-17
> Engram: github.com/Gentleman-Programming/engram (Go binary, MCP stdio)
> Sources: gentle-ai docs/engram.md, assets/claude/engram-protocol.md, assets/codex/engram-instructions.md,
>          assets/codex/engram-compact-prompt.md, assets/skills/_shared/engram-convention.md, testdata/golden/*

---

## 1. Protocol Layer (How Agents Are Told To Use Memory)

### Engram Protocol (injected into CLAUDE.md / AGENTS.md)

```
<!-- gentle-ai:engram-protocol -->
MANDATORY and ALWAYS ACTIVE — not something you activate on demand.
<!-- /gentle-ai:engram-protocol -->
```

**Key directives:**
1. **PROACTIVE SAVE TRIGGERS** — 12 explicit triggers (decision, bugfix, config change, etc.)
2. **Self-check** after EVERY task: "Did I make a decision, fix a bug, learn something?"
3. **Save format**: title (Verb+what), type (bugfix|decision|architecture|...), scope (project|personal), topic_key, content (What/Why/Where/Learned)
4. **Search protocol**: On "remember"/"recall" → `mem_context` → `mem_search` → `mem_get_observation`
5. **Proactive search**: On first message referencing project/feature → search before responding
6. **Session close**: MUST call `mem_session_summary` with Goal/Instructions/Discoveries/Accomplished/Next Steps/Relevant Files
7. **After compaction**: FIRST ACTION → `mem_session_summary` + `mem_context`
8. **Passive capture**: Include `## Key Learnings:` section → Engram auto-extracts
9. **Topic upsert rules**: Different topics must not overwrite, same topic_key = upsert, unsure = `mem_suggest_topic_key`

### tmux_fork Protocol (injected via Pi system prompt + AGENTS.md)

```
## Memory Protocol (MANDATORY - always active)
POST-COMPACT RECOVERY: search memory first
Self-check after EVERY task
Save triggers: bug fix, decision, discovery, pattern, config, preference, workflow, performance, security
Session close: NOT optional — save session-summary
Key Learnings: End EVERY response with actionable findings
```

**Key differences:**

| Aspect | Engram | tmux_fork |
|--------|--------|-----------|
| Injection method | MCP tools (runtime) + Markdown markers in CLAUDE.md | Pi system prompt (before_agent_start) + AGENTS.md |
| Agent calls via | MCP tool calls (`mem_save`, `mem_search`, etc.) | CLI commands (`uv run memory save/search`) |
| Save triggers | 12 explicit triggers listed | 9 trigger categories (similar but fewer items) |
| Self-check wording | "Did I make a decision, fix a bug..." | "Did I decide/fix/learn/establish something?" |
| Passive capture | Regex extraction from `## Key Learnings:` | Regex extraction from `## Key Learnings:` |
| After compaction | "FIRST ACTION REQUIRED: Call mem_session_summary" | "POST-COMPACT RECOVERY: cd ... && uv run memory search" |
| Topic key help | `mem_suggest_topic_key` tool | No equivalent (manual) |
| Scope field | project \| personal | No scope field |
| Privacy tags | `<private>...</private>` stripped | No equivalent |

**Verdict:** Protocols are **functionally identical** in intent. Engram has cleaner injection via MCP tools
(no shell commands needed by agent). tmux_fork relies on CLI which works but is more verbose.

---

## 2. MCP Tools vs CLI Commands

### Engram: 15 MCP Tools

| Tool | tmux_fork equivalent | Gap |
|------|---------------------|-----|
| `mem_save` | `uv run memory save` | CLI works but agent must shell out |
| `mem_search` | `uv run memory search` | Same |
| `mem_context` | `uv run memory search "compact/session-summary"` | Engram has dedicated fast-path |
| `mem_session_summary` | `uv run memory save ... -m '{"type":"session-summary"}'` | Engram has dedicated tool |
| `mem_get_observation` | `uv run memory get <id>` | Both work |
| `mem_save_prompt` | No equivalent | **Engram +** — saves user prompts |
| `mem_update` | Implicit via topic_key upsert | Both support upsert |
| `mem_suggest_topic_key` | No equivalent | **Engram +** — helps agents choose keys |
| `mem_session_start/end` | `uv run memory session start/end` | Both have |
| `mem_stats` | `uv run memory stats` | Both have |
| `mem_delete` | `uv run memory delete` | Both have |
| `mem_timeline` | `uv run memory query timeline` | Engram more precise |
| `mem_capture_passive` | Pi extension (passive-capture.ts) | Both have |
| `mem_merge_projects` | No equivalent | **Engram +** — merges duplicate project names |

### tmux_fork: 21 CLI Commands

| Command | Engram equivalent | Advantage |
|---------|-------------------|-----------|
| `memory save` | `mem_save` | — |
| `memory search` | `mem_search` | — |
| `memory get` | `mem_get_observation` | — |
| `memory list` | `mem_timeline` | — |
| `memory delete` | `mem_delete` | — |
| `memory update` | `mem_update` | — |
| `memory session start/end/info` | `mem_session_start/end` | Full session lifecycle |
| `memory health --fix` | No equivalent | **tmux_fork +** — FTS integrity repair |
| `memory stats --slow-queries` | No equivalent | **tmux_fork +** — query perf analysis |
| `memory telemetry dashboard` | No equivalent | **tmux_fork +** — full metrics |
| `memory schedule add/list/cancel` | No equivalent | **tmux_fork +** — cron-like tasks |
| `memory compact` | No equivalent | **tmux_fork +** — explicit compaction |
| `memory context` | `mem_context` | — |
| `memory query timeline` | `mem_timeline` | — |
| `memory prompt save/search` | No equivalent | **tmux_fork +** — prompt storage |
| `memory sync export/import` | `engram sync/--import` | Engram more complete |
| `memory workflow outline/execute/verify/ship` | SDD phases (separate) | Different paradigm |
| `fork doctor` | No equivalent | **tmux_fork +** — tmux health |
| `fork message send/receive` | No equivalent | **tmux_fork +** — inter-agent IPC |

---

## 3. Schema Comparison

### Engram Schema (inferred from docs + gentle-ai assets)

```
observations:       id, timestamp, content, metadata, project, type, topic_key, revision_count
observations_fts:   content (FTS5)
sessions:           id, project, started_at, ended_at, goal, summary
prompts_fts:        prompt_text, role, model, provider, session_id (FTS5)
sync_state:         last_sync_at, chunks exported/imported
```

### tmux_fork Schema (from migrations)

```
observations:       id, timestamp, content, metadata, idempotency_key, topic_key, project, type,
                    revision_count, session_id, sync_id, synced_at
observations_fts:   content (FTS5)
sessions:           id, project, directory, started_at, ended_at, goal, instructions, summary
scheduled_tasks:    id, scheduled_at, action, context, status, created_at
promise_contracts:  id, session_id, plan_id, task, state, verify_evidence, created_at, updated_at, metadata
telemetry_events:   id, event_type, event_category, timestamp, session_id, correlation_id, attributes, metrics
telemetry_metrics:  id, metric_name, metric_type, labels, bucket_start, value_count, value_sum, value_min, value_max
telemetry_sessions: id, workspace_id, started_at, ended_at, hooks_fired, agents_spawned, memory_saves, ...
prompts:            id, prompt_text, role, model, provider, session_id, timestamp, metadata
prompts_fts:        prompt_text, role, model, provider, session_id (FTS5)
sync_chunks:        chunk_id, source, imported_at, observation_count, checksum
sync_mutations:     seq, entity, entity_key, op, payload, source, project, created_at
sync_status:        id, last_export_at, last_import_at, last_export_seq, mutation_count
```

### Key Schema Differences

| Feature | Engram | tmux_fork | Notes |
|---------|--------|-----------|-------|
| Core observations | Same columns | Same + idempotency_key, session_id, sync_id, synced_at | tmux_fork has more tracking columns |
| FTS5 on prompts | Yes (prompts_fts) | Yes (prompts_fts) | Both have this now |
| Scheduled tasks | No | Yes | tmux_fork unique |
| Promise contracts | No | Yes | tmux_fork unique |
| Telemetry (3 tables) | No | Yes | tmux_fork unique, extensive |
| Sync chunks | Yes (chunked JSONL) | Yes (schema exists) | Engram implementation complete |
| Sync mutations | Yes (journal) | Yes (with seq tracking) | Both track mutations |
| Sync status | Yes | Yes | Both track last sync |
| Indexes | Basic | Extensive (15+ indexes) | tmux_fork more indexed |

---

## 4. Integration Layer

### Engram Integration (via gentle-ai)

**Agent adapters inject Engram in 3 ways:**
1. **MCP config** — adds `engram mcp --tools=agent` to agent's MCP settings
2. **System prompt** — injects `<!-- gentle-ai:engram-protocol -->...<!-- /gentle-ai:engram-protocol -->` into CLAUDE.md / AGENTS.md
3. **Compact prompt** — `engram-compact-prompt.md` prepends "FIRST ACTION REQUIRED" to compacted output

**Per-agent MCP config (from golden files):**

| Agent | Config location | Format |
|-------|----------------|--------|
| Claude Code | `~/.claude/mcp/engram.json` | `{"command": ["engram", "mcp", "--tools=agent"]}` |
| OpenCode | `~/.config/opencode/settings.json` | `{"mcp": {"engram": {"command": [...], "type": "local"}}}` |
| Windsurf | `~/.windsurf/mcp.json` | `{"mcpServers": {"engram": {...}}}` |
| Kiro | `~/.kiro/mcp.json` | `{"mcpServers": {"engram": {...}}}` |
| Antigravity | `~/.antigravity/mcp.json` | `{"mcpServers": {"engram": {...}}}` |
| Codex | AGENTS.md instructions | Markdown protocol |

**MCP tool profiles:**
- `--tools=agent` (11 tools): mem_save, mem_search, mem_context, mem_session_summary, mem_get_observation, etc.
- `--tools=admin` (4 tools): mem_stats, mem_delete, mem_update, mem_merge_projects

### tmux_fork Integration

1. **Pi extensions** (3 TypeScript):
   - `compact-memory-bridge.ts` — before_agent_start: keyword extraction + search + cache injection
   - `passive-capture.ts` — agent_end: extract Key Learnings from response
   - `context-session-hub.ts` — session management

2. **CLI commands** — any agent can use `uv run memory save/search/...`

3. **AGENTS.md** — protocol injected in system prompt

4. **HTTP API** (FastAPI, 3093 LOC):
   - `/api/memory/*` — save, search, get, delete, stats
   - `/api/workflow/*` — outline, execute, verify
   - `/api/agents/*` — discovery, pm2
   - `/api/system/*` — health, telemetry

### Integration Comparison

| Aspect | Engram | tmux_fork |
|--------|--------|-----------|
| **Agent calls** | MCP tools (native in agent runtime) | CLI commands (shell out) or HTTP API |
| **Config injection** | Per-agent adapter (11 agents) | Pi extensions (native), CLI (any) |
| **MCP server** | Built-in (`engram mcp`) | No MCP server |
| **HTTP API** | Built-in (`engram serve :7437`) | FastAPI (`/api/*`) |
| **Proactive search** | No (agent must call mem_search) | Yes (Pi before_agent_start auto-injects) |
| **Passive capture** | Regex on `## Key Learnings:` | Same regex in Pi extension |
| **Compact recovery** | Protocol in system prompt | Protocol + cached context injection |
| **Multi-agent** | Each agent gets own MCP connection | tmux sessions + IPC messaging |

---

## 5. Sync & Sharing

### Engram Sync

```
engram sync         → exports to .engram/ (chunked JSONL + manifest)
engram sync --import → imports from .engram/
```

- **Chunked JSONL** with content-hashed manifests
- **Deduplication** via checksum per chunk
- **Git-friendly** — .engram/ committed to repo
- **Team sharing** — clone repo → `engram sync --import`
- **Multi-device** — export on device A, import on device B
- **Project auto-detection** from git remote (v1.11.0+)

### tmux_fork Sync

```
uv run memory sync export  → exports mutations journal
uv run memory sync import  → imports from external source
```

- Schema exists (sync_chunks, sync_mutations, sync_status tables)
- Implementation is **stub-level** — schema ready but no complete flow
- No git-integrated sync
- No team sharing mechanism
- No multi-device support

**Gap: CRITICAL.** Engram's sync is production-grade. tmux_fork has empty tables.

---

## 6. Privacy & Security

### Engram

- **`<private>...</private>` tag stripping** at two layers:
  1. Plugin layer — strips before save
  2. Store layer — strips on retrieval
- Agent can mark any content as private, it never hits storage

### tmux_fork

- **Redaction module** exists (`src/application/services/redaction/`)
- No `<private>` tag equivalent
- Idempotency keys prevent duplicate saves
- Auto-backup rotation (last 3)

---

## 7. SDD Artifact Storage (Engram Convention)

Engram defines a deterministic naming convention for SDD artifacts:

```
title:     sdd/{change-name}/{artifact-type}
topic_key: sdd/{change-name}/{artifact-type}
type:      architecture
```

Artifact types: explore, proposal, spec, design, tasks, apply-progress, verify-report, archive-report, state

**Recovery protocol (2-step):**
1. `mem_search("sdd/{change-name}/{artifact-type}")` → get ID
2. `mem_get_observation(id)` → get full content

**tmux_fork equivalent:** workflow commands (outline→execute→verify→ship) store state in promise_contracts
table, but no SDD artifact convention.

---

## 8. Project Detection

### Engram (v1.11.0+)
- Reads git remote URL at startup
- Normalizes to lowercase
- Uses as project name
- Warns on similar existing names
- `engram projects consolidate` to merge variants

### tmux_fork
- `--project` flag or `PROJECT` env var
- No git remote auto-detection
- No project consolidation

---

## 9. Summary Scorecard (Memory Only)

| Category | Engram | tmux_fork | Winner | Gap |
|----------|--------|-----------|--------|-----|
| **Protocol completeness** | 95 | 85 | Engram | +10 — MCP tools cleaner, suggest_topic_key |
| **MCP tools** | 15 | 0 | Engram | +15 — native agent integration |
| **CLI commands** | 8 | 21 | tmux_fork | +13 — broader command surface |
| **Schema depth** | 75 | 90 | tmux_fork | +15 — 15 migrations, more tables |
| **Sync/sharing** | 95 | 20 | Engram | +75 — chunked JSONL vs empty stubs |
| **Privacy** | 85 | 40 | Engram | +45 — private tag stripping |
| **Telemetry** | 40 | 95 | tmux_fork | +55 — 3 tables, dashboard, slow-log |
| **HTTP API** | 80 | 70 | Engram | +10 — simpler, MCP-native |
| **Proactive search** | 30 | 90 | tmux_fork | +60 — auto keyword injection |
| **Session lifecycle** | 70 | 90 | tmux_fork | +20 — goal, instructions, auto-end |
| **Project detection** | 90 | 50 | Engram | +40 — git remote auto-detect |
| **SDD artifact storage** | 85 | 30 | Engram | +55 — deterministic convention |
| **TUI** | 80 | 0 | Engram | +80 — Bubbletea browser |
| **Auto-backup** | 50 | 85 | tmux_fork | +35 — rotation, data-loss proven |
| **Orchestration** | 30 | 80 | tmux_fork | +50 — tmux multi-agent, IPC |
| **Average** | **69** | **59** | Engram | **+10 pts** |

---

## 10. Actionable Recommendations for tmux_fork

### P0 — Close Critical Gaps

| # | Action | Effort | Impact | Files |
|---|--------|--------|--------|-------|
| G1 | **MCP stdio server** — implement `memory mcp` command | L | Agent-native integration | New: `src/interfaces/mcp/` |
| G2 | **Git-sync implementation** — complete sync_chunks flow | M | Multi-device, team sharing | `src/application/services/sync/`, `src/infrastructure/sync/` |
| G3 | **Privacy redaction** — `<private>` tag stripping | S | Security critical | `src/application/services/redaction/` |

### P1 — Match Parity

| # | Action | Effort | Impact | Files |
|---|--------|--------|--------|-------|
| G4 | **`mem_suggest_topic_key` equivalent** | S | Better topic keys | New: `src/application/services/keyword_service.py` |
| G5 | **Project auto-detection** from git remote | S | Eliminates manual `--project` | `src/infrastructure/platform/git/` |
| G6 | **Project consolidation** command | S | Fixes name drift | New CLI command |
| G7 | **Dedicated `mem_context` fast-path** | S | Faster session recovery | `src/application/use_cases/` |

### P2 — Nice-to-have

| # | Action | Effort | Impact | Files |
|---|--------|--------|--------|-------|
| G8 | **TUI** (Textual) for memory browsing | L | UX improvement | New: `src/interfaces/tui/` |
| G9 | **Obsidian export** | S | Knowledge base integration | New command |
| G10 | **SDD artifact convention** in memory | S | Structured SDD storage | Convention docs |

---

## 11. What tmux_fork Already Does Better

1. **Proactive keyword search** — before_agent_start auto-injects context (Engram relies on agent calling mem_search)
2. **Telemetry** — 3 tables, dashboard, slow-query log, session aggregates
3. **Auto-backup with rotation** — proven by data loss incident
4. **Session lifecycle** — goal, instructions, summary, auto-end, directory tracking
5. **Scheduled tasks** — cron-like delayed actions
6. **Promise contracts** — state machine for workflow tracking
7. **Multi-agent orchestration** — tmux sessions + IPC + health checks
8. **HTTP API** — FastAPI with routes for memory, workflow, agents, system
9. **Topic key upserts** — ON CONFLICT DO UPDATE for progressive refinement
10. **Health checks** — `memory health --fix` with FTS integrity repair
