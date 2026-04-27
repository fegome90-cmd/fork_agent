# autoresearch.ideas.md

## CLI Startup Optimization (Converged ✅)
- Lazy dependencies.py — 290→186ms (-36%)
- Fast workspace detection — DI bypass 170→15ms
- Irreducible ~200ms: Python startup + typer + container imports

## Hybrid Mode Optimization (Converged ✅)
- **Raw httpx MCP client** — 234→28ms dispatch latency (8.4x)
  - Replaced MCP SDK (streamablehttp_client 233ms import) with raw httpx POST
  - Direct JSON-RPC protocol implementation, SSE parsing via line split
  - Fully synchronous — no asyncio.run() overhead
  - Protocol breakdown: initialize=2.6ms, notification=0.5ms, tool_call=2.5ms

## Test Suite Optimization (Converged ✅)
- **Eliminate time.sleep in tests** — 17.8→8.9s (-50%, 8.9s removed)
  - Circuit breaker tests: recovery_timeout=0 + fake clock instead of real sleeps
  - test_invariants: 0.5s→fake clock, 1.5s→0 (recovery_timeout=0)
  - test_agent_manager health_check: 5s→1s (set interval=1, check thread.is_alive)
  - Total removed: 4.6s sleeps + 4.2s thread join timeout
- **Remaining**: ~8.9s for 2025 tests (4.4ms/test avg)
  - ~1.5s subprocess tests (structurally necessary)
  - ~1.5s concurrency tests (structurally necessary)
  - ~5.9s across ~2000 fast tests (near pytest floor)

## Future (not pursued)
- **Cross-process session reuse** — Unix socket + shared session. Only benefits shell mode, not one-shot CLI
- **httpx.Client pooling** — Pre-create client at import time. Saves ~5ms per call. Diminishing returns
- **HTTP/2 keep-alive** — Reuse TCP connection across processes. Requires server changes
- **DB integrity monitoring** — Auto-detect corruption before it causes fallbacks
- **pytest-xdist** — TRIED. 37 failures, high variance. Tests share SQLite state. Dead without test isolation refactoring.
- **Production code: Event-based stop** — Replace time.sleep(30) in health_monitor_loop with threading.Event.wait(30) for instant shutdown

## CLI Lifecycle Latency (Converged ✅)
- **Baseline: 250ms** per fork launch call (subprocess)
- Breakdown: Python 15ms + typer/rich 43ms + container 36ms + other 156ms
- Previous optimization already reduced from ~350ms (lazy DI, fast workspace detection)
- 250ms is irreducible: subprocess boundary inherent to ADR-002 (bash→Python CLI)
- Acceptable: tmux spawn + pi startup takes 5-10s, so 250ms is noise
- **Not pursuing**: Unix socket shared session, httpx pooling, HTTP/2 keep-alive
