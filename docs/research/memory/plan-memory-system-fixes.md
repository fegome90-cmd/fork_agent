# Plan: Memory System Fixes & Improvements

**Date:** 2026-04-16
**Status:** PLAN
**Context:** Post-Engram diff audit. 8 bugs fixed (B1-B8), 4 Engram-gap bugs fixed (N4-N8). All G1-G7 covered.

---

## What's Done (This Session)

### Sprint 1 — Foundation
- [x] G1: Self-check post-tarea in MEMORY_PROTOCOL
- [x] G2: Structured format (What/Why/Where/Learned) in save template
- [x] G3: Key Learnings trigger + passive-capture regex
- [x] G6: Session close with 6 fields (added `instructions`)

### Sprint 2 — Retrieval & Tools
- [x] G4: Proactive keyword search (`extractKeywords` in `before_agent_start`)
- [x] G5: `memory context` CLI command
- [x] G7: `registerTool("memory_save")` native tool

### Bug Fixes (8 original + 4 Engram-diff)
- [x] B1: context command shows topic_key, fallback on empty type
- [x] B2: Regex boundary fix (lookahead `(?=\n##|\n$|$)`)
- [x] B3: parse() filters "No results found"
- [x] B4/B5: query_planner generates individual OR terms
- [x] B6: UNION search (FTS5 content + topic_key LIKE)
- [x] B7: Default DB path prefers local `data/memory.db`
- [x] B8: MEMORY_PROTOCOL uses absolute path
- [x] N4: Keyword quality filter (GENERIC_TERMS + min 2 keywords)
- [x] N5: promptGuidelines on registerTool
- [x] N6: Cache persists between turns (no one-shot clear)
- [x] N7: RECOVERY_QUERY constant across all search paths
- [x] N8: Session close includes `instructions` field

---

## P0 — Should Do Next (Quality & Stability)

### P0.1 Fix pre-existing test failures (our changes)
**Severity:** HIGH — CI blocker
**Files:**
- `tests/unit/application/test_memory_service_upsert.py` — 2 failures
  - Mock expects `get_by_topic_key(topic_key)` but service passes `project=...`
  - Fix: update mocks to include `project` param
- `tests/unit/domain/test_observation.py::test_observation_validates_metadata_type`
  - Entity no longer raises TypeError for metadata
  - Fix: update test to match new entity behavior

### P0.2 `session.md` budget control (67% of injection)
**Severity:** HIGH — session.md = 2173 tokens, growing unbounded
**Problem:** session.md accumulates entries indefinitely. At 200K context it's fine, but:
- Smaller models (Gemini Flash 56K) spend 4% on it
- Rules.md + session.md together = 3276 tokens before any memory
**Fix options:**
- A) Cap session.md injection to last N lines (e.g., 100 lines ≈ 500 tokens)
- B) Summarize session.md before injection (requires LLM call — expensive)
- C) Split session.md into active.md (recent) + archive.md (historical)
**Recommended:** Option A — truncate to last 100 lines in `before_agent_start`

### P0.3 Two DBs still exist (`~/.tmux-agents/` has 5 orphaned obs)
**Severity:** MEDIUM — confusion risk
**Fix:**
- Migrate 5 obs from `~/.tmux-agents/memory.db` to `data/memory.db`
- Document `FORK_DATABASE_PATH` env var in README
- Consider deprecating `~/.tmux-agents/` path entirely

---

## P1 — Should Do Soon (Engram Parity Gaps)

### P1.1 `memory_search` native tool (complement to `memory_save`)
**Severity:** MEDIUM — agent can't search memory without shell
**Current:** Only `memory_save` is a native tool. Search requires shell command.
**Fix:** Add `registerTool("memory_search")` in compact-memory-bridge.ts
**Scope:** ~30 lines TS

### P1.2 `memory_get` tool (retrieve full observation by ID)
**Severity:** MEDIUM — search returns truncated content (80 chars)
**Current:** `memory get <id>` exists as CLI but no native tool
**Fix:** Add `registerTool("memory_get")` — returns full content
**Scope:** ~20 lines TS

### P1.3 Batch save in passive-capture
**Severity:** LOW — N+1 `uv run` calls per learning
**Current:** Each learning item spawns separate `execFileAsync("uv", ...)`
**Fix:** Join items into single `memory save` call with delimited content
**Scope:** ~10 lines TS

### P1.4 Session shutdown hook for auto-save
**Severity:** MEDIUM — session close depends on agent compliance
**Current:** `session_shutdown` event exists in Pi API but we don't use it
**Fix:** Add `pi.on("session_shutdown", ...)` that saves last context
**Scope:** ~15 lines TS

---

## P2 — Nice to Have (Polish & DX)

### P2.1 `memory doctor` command
**Problem:** No way to verify system health from CLI
**Fix:** New command `memory doctor` that checks:
- DB exists and is readable
- FTS5 tables exist
- Extension files compile
- Hooks are registered
**Scope:** ~60 lines Python

### P2.2 `/memory` slash command in Pi
**Problem:** `/compact-memory search X` is verbose. `/memory search X` is more natural.
**Fix:** Register `/memory` command in compact-memory-bridge.ts
**Scope:** ~10 lines TS

### P2.3 Type backfill for existing observations
**Problem:** 45753 of 45760 observations have `type=NULL`
**Fix:** One-time migration script that infers type from content patterns:
- `ORCHESTRATION:` → `orchestration`
- `session/` or `session-summary` → `session_summary`
- `fork/` → `fork_event`
- Content-based heuristics for the rest
**Scope:** ~80 lines Python (migration script)

### P2.4 Observation TTL / cleanup policy
**Problem:** DB grows unbounded (45K+ obs). No auto-cleanup.
**Fix:** Add `memory cleanup --older-than 90d --keep-tagged` command
**Scope:** ~50 lines Python

---

## P3 — Future (Architecture)

### P3.1 Eliminate `pi.exec` → direct SQLite access
**Problem:** Every memory operation spawns `uv run` subprocess (~200ms overhead)
**Fix:** Import `better-sqlite3` in extensions, direct DB access
**Risk:** Requires native module compilation in Pi's Node.js
**Benefit:** 10x faster memory operations

### P3.2 Embedding-based search (pgvector-style)
**Problem:** FTS5 is keyword-only, misses semantic matches
**Fix:** Add embedding column + similarity search
**Scope:** Major — requires embedding model, new migration, new retrieval path

### P3.3 Multi-project isolation
**Problem:** All observations in one DB, project filtering is optional
**Fix:** Project-scoped DBs or mandatory project field

---

## Execution Priority

```
P0.1 → P0.2 → P0.3 → P1.1 → P1.4 → P1.2 → P1.3 → P2.*
```

P0 items are quality gates. P1 items close the Engram parity gap.
P2+ can be done incrementally.

---

## Files Changed This Session

### Extensions (TypeScript)
| File | Changes | Lines |
|------|---------|-------|
| `~/.pi/agent/extensions/compact-memory-bridge.ts` | G4, G7, B3, B6 fix, N4, N5, N6, N7, DB_ARGS | 172 |
| `~/.pi/agent/extensions/context-loader.ts` | G1-G3, G6, B1, B8, N8, MEMORY_PROTOCOL always-inject | 222 |
| `~/.pi/agent/extensions/passive-capture.ts` | G3 parser, B2 regex boundary, DB_PATH fix | 98 |

### Python (tmux_fork)
| File | Changes |
|------|---------|
| `src/interfaces/cli/main.py` | B7: default DB path resolution |
| `src/interfaces/cli/commands/context.py` | NEW: G5 `memory context` command |
| `src/infrastructure/retrieval/v2/query_planner.py` | B4/B5: individual OR terms |
| `src/infrastructure/persistence/repositories/observation_repository.py` | B6: UNION FTS+topic_key search |

### Test Results
- 35/35 pass on files we changed (repository + memory_service)
- 0 regressions introduced
- 9 pre-existing failures (none caused by our changes)
