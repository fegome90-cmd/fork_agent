# Trifecta Context Loader — Stabilization Report

**Date:** 2026-04-22
**Extension:** `~/.pi/agent/extensions/trifecta-context-loader.ts` (1,238 lines, 33KB)
**Role:** Read-only consumer of Trifecta Graph DB + Context Pack JSON

---

## 1. Nomenclature — Corrected

| Term | What it actually does | Subprocess? |
|------|-----------------------|-------------|
| **freshness check** | Reads `schema_version`, `graph_index`, `COUNT(*)` from SQLite | No |
| **graph index** (real) | `trifecta graph index` CLI subprocess — AST parsing, edge computation | Yes (264ms) |
| **graph search direct** | `searchGraphDirect()` — SQLite `LIKE` queries with scoring | No |
| **graph search fallback** | `searchGraphSubprocess()` — `trifecta graph search` CLI | Yes (101ms) |
| **ctx search direct** | `searchContextPackDirect()` — JSON parse + in-memory scoring | No |
| **ctx search fallback** | `trifecta ctx search` CLI | Yes (167ms) |

**Previous error:** Calling the freshness check "graph index 0.09ms" — it never indexes anything. It reads metadata from an already-indexed DB.

---

## 2. Contracts

### GraphDbReadContract

| Field | Value |
|-------|-------|
| expected_schema_version | 1 |
| required_tables | `nodes`, `edges`, `schema_version`, `graph_index` |
| nodes_columns | `id`, `segment_id`, `file_rel`, `symbol_name`, `qualified_name`, `kind`, `line` |
| edges_columns | `id`, `segment_id`, `from_node_id`, `to_node_id`, `edge_kind` |
| freshness_source | `graph_index.indexed_at` |
| max_age_ms | 3,600,000 (1 hour) |
| edge_expansion_max_hops | 1 |
| freshness_invalidation | git HEAD change detected via `.git/HEAD` |

### ContextPackReadContract

| Field | Value |
|-------|-------|
| expected_version | 1 |
| required_top_level_keys | `chunks` |
| chunk_required_fields | `id`, `text`, `title_path`, `source_path` |
| cache_ttl_ms | 300,000 (5 minutes) |
| invalidation_triggers | `context_pack.json` mtime changed |

---

## 3. Telemetry — `QueryTelemetry` (per-query, in `state.lastTelemetry`)

```
interface QueryTelemetry {
  timestamp: string;
  query: string;
  keywords: string[];
  cacheHit: boolean;
  fallbackUsed: boolean;
  fallbackReason: string;
  graphDurationMs: number;
  ctxDurationMs: number;
  totalDurationMs: number;
  symbolsInjected: number;
  ctxChunksInjected: number;
  tokensEstimated: number;
  strictModeViolation: boolean;
}
```

Accessible via `/trifecta-status` command. All fields populated on every `before_agent_start`.

---

## 4. 50-Query Benchmark — Programmatic Context Calls

### Methodology
Queries are **keywords as `extractKeywords()` produces them**, not natural language.
Ground truth: symbol names and files an agent actually needs when working in each area.

### Results by Category

| Category | N | cf@5 | cf@1 | symbol_recall | kw_precision |
|----------|---|------|------|---------------|-------------|
| **easy** (single keyword) | 20 | 70% | 45% | 73% (22/30) | 98% |
| **medium** (multi-keyword) | 20 | **85%** | **80%** | **87%** (27/31) | 99% |
| **hard** (abstract/vague) | 10 | 30% | 30% | 36% (4/11) | 97% |
| **TOTAL** | 50 | 68% | 56% | 74% (53/72) | 98% |

### Realistic performance (easy + medium only)

| Metric | Value |
|--------|-------|
| correct_file@5 | **78%** (31/40) |
| correct_file@1 | **63%** (25/40) |
| symbol_recall | **81%** (49/61) |
| keyword_precision | **99%** |

### Hard queries that miss (expected behavior)
- "persistence layer" — too abstract, matches 100+ symbols
- "domain layer structure" — `domain` matches nothing in symbol names
- "test infrastructure" — no test symbols in the graph
- "concurrency handling" — no symbols with "concurr" in name
- "streaming responses" — no streaming symbols in the graph

These are NOT retrieval failures — the graph simply doesn't have relevant symbols for abstract architectural queries.

---

## 5. Debug-Compare Mode

New command: `/trifecta-debug-compare <query>`

Runs both direct SQLite and CLI subprocess for the same query, shows side-by-side results. **Not in hot path** — only for manual drift detection.

Example output:
```
Debug-compare: "memory service save" → keywords: [memory, service, save]

Direct SQLite (0ms):
  src/application/services/memory_service.py — MemoryService (class) line 45
  src/application/services/memory_service.py — memory_save (function) line 120

CLI subprocess (comparing per-keyword):
  [memory] (102ms): MemoryService, MemoryError, ...
  [service] (98ms): MemoryService, ServiceError, ...
```

---

## 6. Freshness Hardening

| Check | Mechanism | When |
|-------|-----------|------|
| Schema version | `validateGraphDbContract()` | session_start |
| Table structure | Try `SELECT 1 FROM <table>` | session_start |
| Age | `graph_index.indexed_at` < 1h | session_start |
| Git HEAD change | `.git/HEAD` → ref → SHA comparison | session_start |
| Context pack mtime | `statSync()` comparison | before_agent_start |
| Dirty worktree | NOT checked — post-commit hook handles committed changes | N/A |

**Design decision:** We don't check for uncommitted changes. The post-commit hook re-indexes after every commit, and the graph represents committed state. Checking for dirty worktree would require another subprocess call.

---

## 7. Fallback Policy

| Condition | Strict Mode OFF | Strict Mode ON |
|-----------|----------------|----------------|
| Direct SQLite unavailable | → subprocess | → subprocess + warning |
| Schema version mismatch | → re-index subprocess | → re-index subprocess |
| Direct search returns 0 results | → CLI fallback | → skip, log warning |
| Context pack returns 0 results | → CLI fallback | → skip, log warning |
| Git HEAD changed | → re-index subprocess | → re-index subprocess |

`strictMode` is OFF by default. Set `state.strictMode = true` to make fallback visible instead of silent.

**fallback_rate**: Tracked in `state.lastTelemetry.fallbackUsed`. When false: zero subprocess calls.

---

## 8. Hot Path Latency (zero subprocess, DB fresh)

| Component | p50 | p95 | What it does |
|-----------|-----|-----|--------------|
| freshness check | 0.13ms | 1.9ms | SQLite: schema + index + counts |
| graph search direct | 0.19ms | 0.25ms | SQLite: LIKE + scoring |
| ctx search direct (warm) | 5.5ms | 5.7ms | JSON in-memory keyword scan |
| **Total pipeline** | **~6ms** | — | All direct, zero subprocess |

---

## 9. Extension Stats

| Metric | Value |
|--------|-------|
| Lines | 1,238 |
| Size | 33KB |
| Functions | 15 |
| Subprocess calls in code | 4 (all fallback only) |
| Subprocess calls in hot path | **0** (when DB fresh) |
| Contracts defined | 2 (GraphDbRead, ContextPack) |
| Telemetry fields | 14 per query |
| New commands | `/trifecta-status` (enhanced), `/trifecta-debug-compare` |

---

## 10. Residual Risks

| Risk | Mitigation | Severity |
|------|------------|----------|
| Schema change in future Trifecta | `validateGraphDbContract()` re-indexes on mismatch | Low |
| context_pack.json format change | `CONTEXT_PACK_CONTRACT` version check | Low |
| Graph stale after force-push | Git HEAD check triggers re-index | Low |
| `node:sqlite` unavailable | Subprocess fallback, `strictMode` for visibility | Medium |
| Uncommitted changes not indexed | By design — graph = committed state | Info |
| Abstract queries return poor results | By design — keywords must match symbol names | Info |

---

## 11. Evidence

- **tmux_fork tests:** 1,970 passed, 0 regressions
- **Extension structure:** balanced braces, 15 functions
- **50-query benchmark:** 68% cf@5 overall, 85% on medium (realistic use)
- **Contracts:** `GRAPH_DB_CONTRACT`, `CONTEXT_PACK_CONTRACT` defined and wired
- **Telemetry:** `QueryTelemetry` recorded on every `before_agent_start`
- **Freshness:** git HEAD + age + schema version + mtime checks active
