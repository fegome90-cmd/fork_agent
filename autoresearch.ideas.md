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

## Future (not pursued)
- **Cross-process session reuse** — Unix socket + shared session. Only benefits shell mode, not one-shot CLI
- **httpx.Client pooling** — Pre-create client at import time. Saves ~5ms per call. Diminishing returns
- **HTTP/2 keep-alive** — Reuse TCP connection across processes. Requires server changes
- **DB integrity monitoring** — Auto-detect corruption before it causes fallbacks
