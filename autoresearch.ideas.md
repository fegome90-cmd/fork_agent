# autoresearch.ideas.md — Trifecta Extension Optimization

## Done ✅
1. **Direct SQLite via node:sqlite** — 0.14ms vs 111ms subprocess (793x faster). searchGraphDirect() + subprocess fallback. Committed: 99d5acb.
2. **AND semantics fix** — Individual keyword search + merge instead of AND query. 0→5-8 results per query.
3. **State encapsulation (F1)** — Module-level vars → `state` object with JSDoc.
4. **Search cache (F2)** — 30s TTL cache, cache hits = ~0ms.
5. **Post-commit hook** — Symlinked trifecta-sync.sh to .git/hooks/post-commit.

## KPI Autoresearch — Retrieval Quality ✅ DONE
- Baseline: correct_file@5 = 37.5% (3/8)
- Final: correct_file@5 = 83.3% (10/12), correct_file@1 = 66.7% (8/12)
- Target 70% EXCEEDED. Changes implemented in extension:
  1. File-level scoring: files matching more keywords get 10x weight
  2. Original+stemmed keyword search
  3. File path LIKE matching
  4. Qualified name LIKE matching
  5. Kind boosting: class=3, function=2, other=1
  6. 1-hop edge expansion from top-5 results

## Correctness Improvements (not performance)
- Add schema_version check before direct SQLite query
- session_start: replace `which trifecta` subprocess with direct DB existence check
- ctx search: investigate if context_pack can be read via node:sqlite

## Tried and Rejected
- ❌ Lazy imports in trifecta cli.py — first run worse (1091ms JIT), no steady-state improvement
- ❌ symbol_precision@8 target 60% — hard to improve without semantic search (current 21%). Correct files are found (83%) but too many symbols from those files included.

## Future Improvements
- **symbol_precision**: Add result filtering — only include symbols matching >= 1 keyword directly (not just from the same file)
- **cache_hit_rate**: Needs session-level instrumentation
- **agent_used_context_rate**: Needs response analysis
- **FTS5**: If available, would provide ranked full-text search instead of LIKE matching
