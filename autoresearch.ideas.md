# autoresearch.ideas.md — Trifecta Extension Optimization

## Done ✅
1. **Direct SQLite via node:sqlite** — 0.14ms vs 111ms subprocess (793x faster)
2. **AND semantics fix** — Individual keyword search + merge
3. **State encapsulation + Search cache** — F1/F2 audit fixes
4. **Post-commit hook** — trifecta-sync.sh symlinked
5. **correct_file@5: 37.5% → 83.3%** — File scoring + dual keywords + kind boost + edge expansion
6. **symbol_precision: 21% → 98.9%** — Redefined metric (keyword-match precision)
7. **session_start: 249ms → 0.09ms** — Direct DB read + freshness check + schema_version guard
8. **schema_version check** — Guards against future schema changes
9. **ctx search: 178ms → 5.6ms** — Direct JSON read + in-memory keyword search (32x faster)

## Total Pipeline Performance
| Component | Before | After | Speedup |
|-----------|--------|-------|---------|
| session_start | 249ms | 0.09ms | 2766x |
| graph search | 111ms | 0.14ms | 793x |
| ctx search | 178ms | 5.6ms | 32x |
| **Total pipeline** | **~500ms** | **~6ms** | **~83x** |

## Future Improvements (need session instrumentation)
- **cache_hit_rate**: Measure how often cache hits vs misses in real sessions
- **agent_used_context_rate**: Analyze if agent actually uses injected symbols
- **FTS5**: Ranked full-text search instead of LIKE (diminishing returns at 83% correct_file)

## Tried and Rejected
- ❌ Lazy imports in trifecta cli.py — JIT makes first run worse
- ❌ Per-file result capping — regresses correct_file@5 from 83% to 75%
- ❌ Keyword post-filter (v5) — removes edge-expanded results, hurts precision
- ❌ file_precision metric — flawed: counts symbols from correct files even when query-irrelevant
