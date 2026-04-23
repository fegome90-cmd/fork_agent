# Trifecta Context Loader — Post-Stabilization Technical Report

**Date:** 2026-04-22
**Version:** 2.0 (post-stabilization)
**File:** `~/.pi/agent/extensions/trifecta-context-loader.ts` (1273 lines)

## Executive Summary

The Trifecta Context Loader was stabilized by replacing CLI subprocess calls with direct `node:sqlite` queries, eliminating the 145ms subprocess overhead per query. Direct graph search now runs at 0.31ms mean latency (468x faster than the subprocess path). Retrieval quality on the 50-query benchmark is 76.0% CF@5 overall, with easy-tier queries at 93.3%. The remaining 12 failures split between scoring limitations (50% — no file content in graph), vague queries (33%), and zero-result conceptual queries (17%). The extension is production-ready for read-only mode with manual reindex.

## 1. Architecture Overview

| Property | Value |
|----------|-------|
| Total lines | 1273 |
| Functions | 16 |
| `pi.on(` hooks | 2 (`session_start`, `before_agent_start`) |
| `registerCommand` | 3 (`/trifecta-reindex`, `/trifecta-status`, `/trifecta-debug-compare`) |
| Core dependency | `node:sqlite` (Node >= 22), subprocess fallback to `trifecta` CLI |

The extension hooks into the pi-coding-agent lifecycle. `session_start` runs once to detect and validate the graph DB. `before_agent_start` runs on every user query to extract keywords, search graph + context pack, and inject results into the system prompt.

## 2. Data Flow

### 2.1 session_start (runs ONCE per pi session)

```
session_start event
  |
  v
state.projectRoot = ctx.cwd || process.cwd()
state.gitHead = getGitHead(root)              -- READ: .git/HEAD
state.mode = "read_only"
  |
  v
findGraphDb(root)                             -- READ: .trifecta/cache/graph_*.db
  |-- null?  --> state.trifectaAvailable=false, DONE
  |
  v
sqliteModule available?
  |-- no? --> state.graphStatus="unavailable", DONE
  |
  v
Open DB ──> validateGraphDbContract(db)
              |-- fail? --> state.graphStatus="schema_mismatch"
              |-- pass? --> continue
  |
  v
SELECT indexed_at, COUNT(nodes), COUNT(edges)
  |
  v
Age check (maxAgeMs = 60 min) + Git HEAD drift check
  |-- HEAD changed --> state.graphStatus="stale", graphRepresentsCommittedOnly=false
  |-- age >= 60min --> state.graphStatus="stale"
  |-- fresh        --> state.graphStatus="fresh"
  |
  v
state.trifectaAvailable=true
state.indexed = nodeCount > 0
state.graphDb = dbPath
db.close()
```

### 2.2 before_agent_start (runs on EVERY user query)

```
before_agent_start event
  |
  v
state.trifectaAvailable? --no--> return (no injection)
state.indexed?
  |-- no + read_only? --> return silently
  |-- no + repair?    --> lazy index via subprocess (max 5s)
  |
  v
extractKeywords(prompt) --0 keywords?--> return
  |
  v
Cache check (30s TTL) --HIT--> inject cached parts, return
  |
  v
MISS --> cacheMisses++
  |
  v
  +-------------------------------------------+
  | 1. searchGraph(root, keywords, pi)        |
  |    ├─ searchGraphDirect() [primary]       |
  |    │   ├─ 3 SQL queries per expanded kw   |
  |    │   │   (symbol_name / file_rel /       |
  |    │   │    qualified_name LIKE)           |
  |    │   ├─ Edge expansion (top-5, 1-hop)   |
  |    │   └─ Scoring + sort, top 8           |
  |    └─ searchGraphSubprocess() [fallback]  |
  |        (BLOCKED in read_only mode)         |
  |                                            |
  | 2. searchContextPackDirect(keywords)       |
  |    ├─ Read _ctx/context_pack.json (5m TTL)|
  |    └─ Score: text +1, title +2, top 3      |
  +-------------------------------------------+
  |
  v
Format output: "## Trifecta Context"
  |-- "### Symbols" (graph hits, max 8)
  |-- "### Context" (ctx chunks, max 3)
  |
  v
truncateToBudget(parts, 2000 chars)
  |
  v
Cache result (30s TTL), update metrics + telemetry
  |
  v
RETURN { systemPrompt + formatted context }
```

## 3. Scoring Algorithm

### 3.1 Graph Search Scoring

For each expanded keyword, 3 SQL queries run against the graph DB:

1. `SELECT ... WHERE symbol_name LIKE '%kw%' LIMIT 15`
2. `SELECT DISTINCT file_rel ... WHERE file_rel LIKE '%kw%' LIMIT 10`
3. `SELECT ... WHERE qualified_name LIKE '%kw%' LIMIT 10`

Edge expansion: 1-hop callees from top-5 hits by hitCount.

**Final score per symbol:**

```
score = exactBonus + fileKwCount * 10 + hitCount * 5 + kindBoost(kind) + broadPenalty
```

| Component | Weight | Condition |
|-----------|--------|-----------|
| `exactBonus` | +50 | `symbol_name.toLowerCase() === kw.toLowerCase()` |
| `fileKeywordHits` | +10 per unique keyword | Keywords matching the file path |
| `hitCount` | +5 per match | Keyword queries that matched this symbol |
| `kindBoost` | +3 (class), +2 (function/method), +1 (other) | Symbol kind |
| `broadPenalty` | -5 | File matched some but not all expanded keywords |

**Sort:** Descending by score. Top 8 returned.

### 3.2 Context Pack Scoring

Per chunk, per expanded keyword:

| Match location | Score |
|---------------|-------|
| Text contains keyword | +1 |
| Title path contains keyword | +2 |

**Sort:** Descending by score. Top 3 returned.

### 3.3 Keyword Extraction Pipeline

1. Lowercase + strip non-word chars (preserves CJK: `\u3400-\u9FFF`, `\u3040-\u30FF`, `\uAC00-\uD7AF`)
2. Split on whitespace, filter 94 stop words + min length (CJK: >=2, else: >=3)
3. Deduplicate, take up to 4 raw keywords
4. Stem remaining words via 42 suffix patterns, add unique stems up to 6 total

### 3.4 Query Classification

| Priority | Condition | Class |
|----------|-----------|-------|
| 1 | keyword is `test`, `pytest`, or `fixture` | `test` |
| 2 | single keyword >= 4 chars | `symbol` |
| 3 | 2+ keywords with path keyword (`cli`, `api`, `mcp`, `ctx`) | `file` |
| 4 | any keyword matches vague list | `vague` |
| 5 | any keyword contains arch substring | `architecture` |
| 6 | none of the above | `unknown` |

## 4. Contracts & Validation

### 4.1 GRAPH_DB_CONTRACT

```typescript
{
  expectedSchemaVersion: 1,
  requiredTables: ["nodes", "edges", "schema_version", "graph_index"],
  nodesColumns: ["id", "segment_id", "file_rel", "symbol_name", "qualified_name", "kind", "line"],
  edgesColumns: ["id", "segment_id", "from_node_id", "to_node_id", "edge_kind"],
  freshnessSource: "graph_index.indexed_at",
  maxAgeMs: 3_600_000,                 // 60 minutes
  edgeExpansionMaxHops: 1,
}
```

**Validation steps (`validateGraphDbContract`):**
1. `SELECT version FROM schema_version` — must equal 1
2. `SELECT 1 FROM <table> LIMIT 0` — probe each of 4 required tables
3. `PRAGMA table_info(nodes)` — verify all 7 columns present
4. `PRAGMA table_info(edges)` — verify all 5 columns present

### 4.2 CONTEXT_PACK_CONTRACT

```typescript
{
  expectedVersion: 1,
  requiredTopLevelKeys: ["chunks"],
  chunkRequiredFields: ["id", "text", "title_path", "source_path"],
  cacheTtlMs: 300_000,                // 5 minutes
  invalidationTriggers: ["context_pack.json mtime changed"],
}
```

**Validation status:** Enforced at load time. `validateContextPackContract()` checks `requiredTopLevelKeys` and validates ALL chunks against `chunkRequiredFields`. Malformed context packs set `ctxStatus = "schema_mismatch"` and return empty results.

## 5. Mode System

### 5.1 Modes

| Mode | Default | Activation |
|------|---------|------------|
| `read_only` | YES | Set at `session_start`, always reset after repair |
| `repair` | NO | Temporarily set by `/trifecta-reindex`, reset immediately after |

### 5.2 Operations by Mode

| Operation | `read_only` | `repair` |
|-----------|-------------|----------|
| Graph search (direct SQLite) | ALLOWED | ALLOWED |
| Graph search (subprocess fallback) | **BLOCKED** — returns empty | ALLOWED |
| Lazy index in `before_agent_start` | **BLOCKED** — returns silently | ALLOWED (5s timeout) |
| Context pack search | ALLOWED | ALLOWED |
| `/trifecta-reindex` | ALLOWED (sets temp repair) | ALLOWED |
| `/trifecta-status` | ALLOWED | ALLOWED |
| `/trifecta-debug-compare` | ALLOWED | ALLOWED |
| Auto-reindex on stale | **NEVER** — always manual | N/A |

### 5.3 Key Design Decisions

- **Never auto-reindex.** Stale graphs emit `console.debug` suggesting `/trifecta-reindex`.
- **Subprocess fallback blocked in read_only.** If direct SQLite returns 0 results, the extension returns empty rather than shelling out to the CLI. Safety constraint to prevent unintended mutations.
- **Mode is NOT persistent.** `repair` exists only for the duration of `/trifecta-reindex` execution.
- **Git HEAD drift detection.** If HEAD changes between session start and reindex, `graphRepresentsCommittedOnly` is set to `false`.

## 6. Performance KPIs

### 6.1 Latency

| Component | p50 | p95 | Max | Notes |
|-----------|-----|-----|-----|-------|
| Graph search (direct SQLite) | 0.33ms | 0.52ms | 0.52ms | 20 queries, 3 runs each |
| Context pack search | 7.73ms | — | 7.87ms | 10 queries, 5 runs each |
| Full hot path | ~8.0ms | — | — | graph + ctx search |
| Subprocess (eliminated) | 145.0ms | — | — | CLI startup overhead per call |
| Extension cache hit | ~0.01ms | — | — | 30s TTL cache |

### 6.2 Retrieval Quality

**50-query benchmark results:**

| Tier | Queries | CF@5 | CF@5% | Avg KW Precision |
|------|---------|------|-------|-----------------|
| **Overall** | 50 | 38 | **76.0%** | **0.8067** |
| Easy | 15 | 14 | **93.3%** | 1.0000 |
| Medium | 20 | 14 | **70.0%** | 0.8667 |
| Hard | 15 | 10 | **66.7%** | 0.5333 |

### 6.3 Optimization Impact

| Metric | Before (subprocess) | After (direct SQLite) | Improvement |
|--------|--------------------|-----------------------|-------------|
| Graph query latency | 145ms (CLI startup) | 0.31ms (mean) | **468x faster** |
| Hot path total | ~153ms | ~8ms | **19x faster** |
| Subprocess calls per query | 1-6 | 0 (read_only) | Eliminated |

### 6.4 Per-Query Latency Samples (Graph Search)

| Query | Avg (ms) | Results |
|-------|----------|---------|
| memoryservice | 0.14 | 1 |
| tmuxag | 0.16 | 1 |
| observa | 0.16 | 10 |
| memoryhook | 0.14 | 2 |
| forkagentconfig | 0.14 | 1 |
| persistence | 0.17 | 10 |
| cli workspace create | 0.52 | 30 |
| agent message send | 0.51 | 27 |
| workflow execute | 0.40 | 19 |
| memory search retrieve | 0.52 | 23 |
| observa repository | 0.34 | 20 |
| error handling | 0.34 | 10 |
| messaging system | 0.33 | 16 |
| workflow lifecycle | 0.30 | 10 |
| diff comparison | 0.31 | 10 |
| retriev search | 0.37 | 20 |
| schedul task | 0.35 | 19 |
| export functional | 0.33 | 4 |
| cleanup operation | 0.32 | 10 |
| terminal control | 0.35 | 20 |

## 7. Failure Analysis

### 7.1 Failed Queries: 12/50

| Query | Tier | KW Prec | Results | Category |
|-------|------|---------|---------|----------|
| Observation | easy | 1.00 | 5 | scoring_problem |
| persistence layer | medium | 0.50 | 3 | vague_query |
| workflow execute | medium | 1.00 | 5 | scoring_problem |
| observation repository | medium | 1.00 | 5 | scoring_problem |
| API routes memory | medium | 0.67 | 5 | vague_query |
| session management service | medium | 1.00 | 5 | scoring_problem |
| hook runner workspace | medium | 1.00 | 5 | scoring_problem |
| domain structure | hard | 0.00 | 0 | no_results |
| concurrency patterns | hard | 0.00 | 0 | no_results |
| configuration management | hard | 0.50 | 4 | vague_query |
| data access | hard | 0.50 | 5 | vague_query |
| security validation | hard | 1.00 | 5 | scoring_problem |

### 7.2 Root Cause Categories

| Category | Count | % of failures | Description |
|----------|-------|---------------|-------------|
| scoring_problem | 6 | 50% | Keywords match but expected file not in top 5 |
| vague_query | 4 | 33% | Multi-word queries matching unrelated high-connectivity nodes |
| no_results | 2 | 17% | Conceptual queries with no matching symbols in graph |

### 7.3 Root Cause Analysis

1. **scoring_problem (6 failures):** The graph stores no file content — only `symbol_name`, `qualified_name`, `file_rel`. Queries like "observation" match `memory.py` because "observation" appears in imports/references within that node's metadata. The scoring weights `symbol_name` > `qualified_name` > `file_rel` but cannot distinguish between a file that defines a symbol vs one that imports it.

2. **vague_query (4 failures):** "persistence layer" matches workspace-related files because `workspace_manager.py` has high connectivity. "configuration management" — "configura" matches many files. These are conceptually broad queries that the structural graph is not designed to handle.

3. **no_results (2 failures):** "domain structure" and "concurrency patterns" are conceptual queries with no matching code symbols. The graph is code-structure based, not conceptual.

## 8. State & Telemetry

### 8.1 State Shape

```typescript
const state = {
  trifectaAvailable: boolean,          // Graph DB exists + sqlite available + contract valid
  indexed: boolean,                     // node_count > 0
  graphStats: GraphStats | null,        // { node_count, edge_count, indexed_at }
  projectRoot: string,
  graphDb: string | null,               // Absolute path to graph_*.db
  searchCache: CachedSearch | null,     // { query, root, parts[], timestamp } — TTL: 30s
  contextPack: ContextPack | null,      // { chunks[], loadedAt } — TTL: 5min
  lastTelemetry: QueryTelemetry | null,
  metrics: SessionMetrics,
  strictMode: boolean,                  // Currently unused (always false)
  mode: ExtensionMode,                  // "read_only" | "repair"
  graphRepresentsCommittedOnly: boolean,
  gitHead: string,
  contextPackMtime: number,             // Currently unused (always 0)
  graphStatus: GraphStatus,             // "fresh" | "stale" | "schema_mismatch" | "unavailable"
}
```

### 8.2 SessionMetrics (10 fields)

| Field | Type | Description |
|-------|------|-------------|
| `totalQueries` | number | Total queries processed |
| `cacheHits` | number | Queries served from 30s cache |
| `cacheMisses` | number | Queries that hit graph/ctx |
| `fallbackCount` | number | Times subprocess fallback was used |
| `strictViolations` | number | Strict mode violations (currently always 0) |
| `graphDirectZeroCount` | number | Times graph search returned 0 results |
| `ctxDirectZeroCount` | number | Times ctx search returned 0 results |
| `symbolsInjectedTotal` | number | Cumulative symbol hits injected |
| `ctxChunksInjectedTotal` | number | Cumulative ctx chunks injected |
| `durationSamples` | number[] | All query durations for percentile calc |

### 8.3 QueryTelemetry (14 fields)

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO timestamp |
| `query` | string | First 100 chars of prompt |
| `keywords` | string[] | Extracted keywords (max 6) |
| `cacheHit` | boolean | 30s cache hit |
| `fallbackUsed` | boolean | Subprocess fallback used |
| `fallbackReason` | string | Why fallback triggered |
| `graphDurationMs` | number | Graph search wall time |
| `ctxDurationMs` | number | Context pack search wall time |
| `totalDurationMs` | number | Total query processing time |
| `symbolsInjected` | number | Symbols in this query |
| `ctxChunksInjected` | number | Context chunks in this query |
| `tokensEstimated` | number | Approx tokens: `formatted.length / 4` |
| `strictModeViolation` | boolean | Currently always false |
| `queryClass` | QueryClass | Classification result |

### 8.4 Cache TTLs

| Cache | TTL | Scope |
|-------|-----|-------|
| `searchCache` | 30,000 ms (30s) | Per keywords+root combo |
| `contextPack` | 300,000 ms (5min) | Global, re-reads `_ctx/context_pack.json` |
| `GRAPH_DB_CONTRACT.maxAgeMs` | 3,600,000 ms (60min) | Freshness threshold for graph DB |

## 9. Known Limitations

1. **Stemmer is suffix-only.** The `stemWord` function iterates 42 suffix patterns but does not handle prefix stemming or lemmatization. This is adequate for code symbols but limits effectiveness on natural language queries.

2. **No semantic search.** All matching is keyword-based LIKE queries. Conceptual queries ("concurrency patterns", "domain structure") produce zero results because there are no matching code symbols.

3. **Graph has no content column.** The `nodes` table stores only `symbol_name`, `qualified_name`, `file_rel`, `kind`, `line`. No file content is indexed, limiting scoring to structural matching.

## 10. Residual Risk Fixes (2026-04-22)

The following risks identified during stabilization were closed:

| Risk | Fix | Lines Changed |
|------|-----|---------------|
| strictMode not wired | Added `/trifecta-strict` toggle command. Strict mode now blocks stale/invalid graph and ctx in hot path. Shown in `/trifecta-status` output. | +20 |
| Context pack validation sampled only first 5 chunks | `validateContextPackContract` now validates ALL chunks, not just first 5. Safe because pack is loaded once and cached for 5 minutes. | 1 |
| ctxStatus "unavailable" used for multiple failure modes | `ctxStatus` now distinguishes: `unavailable` (file missing), `stale` (file exists but not loaded or mtime changed), `schema_mismatch` (contract violation), `fresh` (successfully loaded). Session start performs initial availability check. | +25 |
| contextPackMtime always 0 | Wired in session_start (initial check) and searchContextPackDirect (mtime comparison for invalidation). | +5 |

## 11. Next Steps

1. **FTS5 for ranked search.** Replace the 3 LIKE queries per keyword with SQLite FTS5 `MATCH` queries. Enables ranked results with BM25 scoring, reducing the scoring_problem failure category.

2. **Context pack contract validation.** IMPLEMENTED. `validateContextPackContract()` validates ALL chunks. Contract violations set `ctxStatus = "schema_mismatch"` and prevent silent empty results.

3. **strictMode enforcement.** IMPLEMENTED. `/trifecta-strict` toggle command. When ON, blocks stale/invalid graph and ctx in hot path. Increments `strictViolations` counter. Shown in `/trifecta-status`.

4. **Session-level `cache_hit_rate` instrumentation.** IMPLEMENTED. Cache hit rate computed as `(cacheHits / totalQueries * 100).toFixed(1)%` in `/trifecta-status`.

5. **Semantic query bridge.** For queries classified as `vague` or `architecture`, consider a lightweight embedding-based reranking step on the keyword-matched results to improve relevance ranking within the top-8 cutoff.

6. **Rate limiting mitigation.** Consider using `glm-5.1` (different rate limit pool) for late-session agent spawns. Document in known-issues.md (W6).

7. **Automated extension tests.** IMPLEMENTED. 40 tests across 6 pure functions. Run via `npx tsx ~/.pi/agent/extensions/trifecta-context-loader.test.ts`.
