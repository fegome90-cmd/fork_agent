# Autoresearch Ideas — Deferred Optimizations

## Test Speed (current best: 8.27s, baseline 15.33s)

### Already tried (prune from consideration)
- ~~pytest-xdist -n auto~~ → 9.85s (works but not optimal)
- ~~--dist=loadfile~~ → 9.29s (decent, loadscope better)
- ~~--import-mode=importlib~~ → no improvement
- ~~-p no:cacheprovider~~ → no improvement
- ~~--forked (pytest-forked)~~ → incompatible, 35 tests fail
- ~~Remove -v from addopts~~ → no improvement (benchmark uses -q)
- ~~Worker counts~~ → tried 4/6/8/10/auto, sweet spot is 6
- ~~-n auto in pyproject addopts~~ → bad for default config

### Promising to explore
- **Profile test durations**: Run `pytest --durations=50` to identify slowest tests — then target them specifically
- **SQLite in-memory for tests**: Many tests likely create temp DB files; switching to `:memory:` could reduce I/O
- **Shared fixture session scope**: Audit fixtures that could be `scope="session"` instead of function-level — would reduce setup overhead in parallel workers
- **Lazy imports in test files**: Check if tests import heavy modules at module level that could be deferred
- **pytest-split**: Use `pytest-split` for consistent test timing data to optimize distribution
