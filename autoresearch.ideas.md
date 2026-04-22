# autoresearch.ideas.md — Trifecta Extension Optimization

## Done ✅
1. **Direct SQLite via node:sqlite** — 0.14ms vs 111ms subprocess (793x faster). searchGraphDirect() + subprocess fallback. Committed: 99d5acb.
2. **AND semantics fix** — Individual keyword search + merge instead of AND query. 0→5-8 results per query.
3. **State encapsulation (F1)** — Module-level vars → `state` object with JSDoc.
4. **Search cache (F2)** — 30s TTL cache, cache hits = ~0ms.
5. **Post-commit hook** — Symlinked trifecta-sync.sh to .git/hooks/post-commit.

## Benchmark Inconsistency — Corrected
- Original claim: "CLI startup = 145ms, graph search = 102ms (includes 145ms startup)" — WRONG
- Corrected: `--help` = 131ms (imports ALL modules), `graph search` = 98ms (lazy subcommand, fewer imports)
- Typer lazy-loads subcommand groups, so `graph search` is actually FASTER than `--help`
- The 145ms was `--help` measurement, not the floor for `graph search`
- Direct SQLite: 0.028ms per query — 3598x faster than subprocess

## External Audit — KPIs to Add (from comparative analysis)
Priority order per audit:
1. **Fix benchmark with hyperfine**: cold/warm, p50/p95, startup separated ✅ DONE above
2. **Batch query**: `trifecta graph search --any kw1 kw2 kw3` single subprocess call
3. **Robust cache key**: segment + git_sha + normalized_query + mode
4. **cache_hit_rate**: measure in real sessions (target >70%)
5. **correct_file@5**: measure if top-5 symbols include the right file (baseline then target >70%)
6. **useful_symbol_precision@k**: what % of injected symbols are actually used by agent
7. **tokens_saved_vs_raw**: compare token count with/without context injection
8. **agent_used_context_rate**: how often agent cites/uses injected symbols in response

## Correctness Improvements (not performance)
- Add schema_version check before direct SQLite query
- session_start: replace `which trifecta` subprocess with direct DB existence check
- ctx search: investigate if context_pack can be read via node:sqlite

## Tried and Rejected
- ❌ Lazy imports in trifecta cli.py — first run worse (1091ms JIT), no steady-state improvement
