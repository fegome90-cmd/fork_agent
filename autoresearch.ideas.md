# autoresearch.ideas.md

## CLI Startup Optimization (Converged ✅)

- Lazy dependencies.py — 290→186ms (-36%)
- Fast workspace detection — DI bypass 170→15ms

## Hybrid Mode Optimization (Converged ✅)

- Raw httpx MCP client — 234→28ms (8.4x)

## Test Suite Optimization (Converged ✅)

- Eliminate time.sleep — 17.8→8.9s (-50%)

## CLI Lifecycle Latency (Converged ✅)

- 250ms irreducible for subprocess boundary (ADR-002)

## Code-Path Cartographer Skill Quality (Converged ✅)

- **98/100** — benchmark scores 6 dimensions over real tmux_fork targets
- Coverage 87% (13/15): 2 points are rg adapter limitation (indirect refs), not skill defect
- All improvements from 3 rounds merged: examen_grado best items, LSP operation guide, scope column
- LSP `incomingCalls` resolves the 2-point gap but adding LSP to benchmark tests LSP, not skill

## Dead Ideas (do not revisit)

- Cross-process session reuse — only benefits shell mode
- httpx.Client pooling — saves ~5ms, diminishing returns
- HTTP/2 keep-alive — requires server changes
- DB integrity monitoring — not measurable in autoresearch
- pytest-xdist — TRIED, 37 failures from shared SQLite state
- Event-based stop for health_monitor — not benchmarked, production-only benefit
- Improving benchmark score past 98 — would require LSP in benchmark (tests adapter, not skill)
