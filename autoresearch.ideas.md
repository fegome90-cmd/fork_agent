# Autoresearch Ideas — Deferred Optimizations

## Test Speed (current best: 4.09s, baseline 15.33s → 73% improvement)

### Already tried — no improvement / rejected
- ~~pytest-xdist -n auto~~ → 9.85s (not optimal, 6 is sweet spot)
- ~~--dist=loadfile~~ → 9.29s (loadscope better at 8.27s)
- ~~--import-mode=importlib~~ → no improvement
- ~~-p no:cacheprovider~~ → no improvement
- ~~--forked (pytest-forked)~~ → incompatible, 35 tests fail
- ~~Remove -v from addopts~~ → no improvement
- ~~Worker counts: 4/8/10/auto~~ → 6 is optimal
- ~~Threshold < 1ms~~ → negligible improvement over 50ms
- ~~-n auto in pyproject addopts~~ → bad for default config

### Diminishing returns — remaining time is subprocess/git, not configurable
- Remaining bottlenecks are real subprocess calls (trifecta_health, hook_runner) and git operations
- These can't be optimized without modifying test logic (off-limits per autoresearch.md)

### Future ideas (low expected impact)
- **pytest-split**: Consistent test timing data for more optimal distribution across workers
- **Lazy imports in test files**: Check if tests import heavy modules at module level that could be deferred
- **Session-scoped fixtures**: Audit fixtures that could be `scope="session"` to reduce per-worker setup
