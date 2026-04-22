# Plan: Trifecta Auto-Index + Context Injection via Pi Extensions

## Summary
Integrate Trifecta into the agent lifecycle via a pi extension (auto-context injection on agent start) and a git post-commit hook (auto-reindex). Zero changes to Trifecta codebase — all integration in tmux_fork + pi extensions.

## In Scope
- Pi extension `trifecta-context-loader.ts` — inject codebase context on `before_agent_start`
- Git post-commit hook via pre-commit — auto `trifecta graph index` after commits
- EventSpine event `TrifectaIndexEvent` — emit telemetry when index runs
- `fork doctor status` — show Trifecta graph staleness
- Telemetry — emit `agent.spawn` from orchestrator spawn path
- PLAN.md as roadmap anchor — survives compaction, evolves across runs

## Out of Scope
- Changes to Trifecta codebase itself (separate repo, separate roadmap)
- Trifecta MCP server integration with pi (deferred — pi already has MCP bridge)
- Method-level graph resolution (Trifecta limitation — only top-level symbols)
- Daemon mode auto-start (nice-to-have, not blocking)

## Architecture Decisions
- **Pi extension over shell script** — `before_agent_start` fires for ALL sessions (interactive, sub-agent via tmux-live, etc.), not just orchestrated ones. Shell scripts in orchestrator only fire in Phase 3.
- **pre-commit over .husky** — already using pre-commit config, no new infra. `trifecta-sync.sh` already exists but only rebuilds context pack, not graph.
- **Always reindex before search** — `graph index` takes only 300ms for 5892 files. No staleness check needed; just reindex on every `before_agent_start`.
- **EventSpine event** — `FileWrittenEvent` already exists for file ops. New `TrifectaIndexEvent` tracks index runs with duration + node count for telemetry.
- **No Trifecta code changes** — all integration via CLI invocations and graph DB reads. Trifecta stays immutable.
- **Reuse keyword extraction from `trifecta-context-inject`** — 80 lines of bash (extract_keywords, stem_word, stop words) are trifecta-independent. Port to TypeScript.

## Key Technical Findings (from exploration)

### Pi Extension API
- 27 methods on ExtensionAPI, 28 event types
- `before_agent_start` returns `{ systemPrompt: event.systemPrompt + appended }` — chains across extensions
- `resources_discover` returns `{ skillPaths, promptPaths, themePaths }`
- `pi.exec()` — async shell command execution (replaces child_process)
- All handlers support async/await — runner awaits results
- `registerTool()` — adds LLM-callable tools (like `n8n-mcp-bridge.ts`)

### Trifecta Performance
| Command | Time | Notes |
|---------|------|-------|
| `graph status` | 257ms | Health check |
| `graph search` | 141ms | Symbol search |
| `graph callers` | 141ms | Top-level only, no methods |
| `graph index` | **300ms** | Full reindex of 5892 files |
| `ctx plan` | 172ms | PRIME-based plan |
| `status` | 134ms | Feature flags |

All commands < 350ms. **Safe to call synchronously in `before_agent_start`.**

### Trifecta Output Formats
- `graph status --json`: `{status, exists, segment_id, node_count, edge_count, last_indexed_at}`
- `graph search --json`: `{status, query, nodes: [{id, file_rel, symbol_name, kind, line}]}`
- `graph index --json`: `{status, segment_id, node_count, edge_count, indexed_at}`
- `ctx search`: NO `--json` flag. Use `--explain --explain-format json`
- Graph only indexes top-level symbols (no methods). `MemoryService.save` fails; must use `save`.

### Existing `trifecta-context-inject` Pipeline (320 lines, 774ms avg)
- 4-tier cascade: load → ctx plan → ctx search → FTS5 fallback → skill-resolver
- Keyword extraction: 70+ stop words, 30+ English suffix stemmers, CJK detection, role-based broadeners
- Cache: content-validated (checks for "Project Standards" substring), no TTL
- Budget: clamped [1-5000], truncates at budget * 4 chars
- Zero-hit tracking: `~/.local/share/trifecta-inject-zero-hits.jsonl`
- Role limits: explorer/architect/analyst get 5 results, others get 3

### 9 Orchestrator Scripts Using Trifecta
| Script | Lines | Purpose |
|--------|-------|---------|
| `trifecta-context-inject` | 320 | 4-tier context injection pipeline |
| `trifecta-preload` | 140 | Explorer pre-loading |
| `trifecta-affected-symbols` | 115 | Symbol extraction from task files |
| `trifecta-verifier-check` | 145 | Post-impl verification |
| `trifecta-quality-report` | 150 | Quality metrics from telemetry |
| `trifecta-session-log` | 55 | Session log append |
| `trifecta-ast-snippet` | 55 | Code snippet extraction |
| `trifecta-auto-sync` | 30 | Auto-rebuild stale context |
| `trifecta-daemon-warmup` | 30 | LSP daemon warmup |

## Tasks

### Phase A: Pi Extension `trifecta-context-loader.ts` (NEW)

- [x] CREATE `~/.pi/agent/extensions/trifecta-context-loader.ts`
  - 3-layer detection architecture:
    - Layer 1: `which trifecta` — no-op if unavailable (0ms)
    - Layer 2: `graph index` + `graph search` — works on ANY repo (zero-config)
    - Layer 3: `ctx search` — only if `.trifecta/` + `_ctx/` exist (opt-in)
  - Hook: `session_start` → reindex graph, cache for session
  - Hook: `before_agent_start` → keyword extraction + graph search + optional ctx search
  - Command: `/trifecta-status` — show graph health, node count, staleness
  - Budget cap: 2000 chars (~500 tokens)
  - Port keyword extraction from bash: 80 stop words, simple stemmer, CJK detection

- [ ] TEST: start pi in tmux_fork, verify system prompt includes "Codebase Symbols (trifecta)"
- [ ] TEST: start pi in project WITHOUT .trifecta/, verify silent skip
- [ ] TEST: verify `/trifecta-status` command works

### Phase B: Git Post-Commit Auto-Index

- [x] MODIFY `scripts/trifecta-sync.sh` — add graph reindex after context pack rebuild
  ```bash
  # Existing: trifecta index -r . --json (context pack)
  # Add after:
  if [ -d ".trifecta" ]; then
      echo "[trifecta-sync] Reindexing graph..."
      trifecta graph index -s . --json 2>/dev/null || true
  fi
  ```

- [ ] TEST: `git commit --allow-empty -m "test"`, verify graph timestamp updates

### Phase C: Telemetry Events

- [x] ADD `TrifectaIndexEvent` to `src/application/services/orchestration/events.py`
  - Fields: `repo_path`, `duration_ms`, `node_count`, `edge_count`

- [x] EMIT from `scripts/trifecta-sync.sh` after successful index
  - `fork telemetry emit --type trifecta.index --attrs '{"node_count": N, "duration_ms": T}'`

- [ ] VERIFY: `fork telemetry report` shows new event type

### Phase D: `fork doctor status` Enhancement

- [x] ADD Trifecta graph health check to doctor output
  - Read `.trifecta/cache/graph_*.db` → `SELECT * FROM graph_index`
  - Show: "Trifecta: 658 nodes, 218 edges, indexed 2h ago (fresh)"
  - Show: "Trifecta: STALE (47h ago) — run `trifecta graph index -s .`"
  - Show: "Trifecta: not initialized (no .trifecta/ found)"

- [x] TEST: `fork doctor status` shows Trifecta line

### Phase E: Roadmap Anchor (this file)

- [x] CREATE `PLAN-trifecta-integration.md` — living roadmap document
- [ ] UPDATE after each phase completion
- [ ] ADD "Future" section for Trifecta repo-side changes

## Validation
```bash
# Phase A
pi --version  # extension loads, no errors
# System prompt should contain "Codebase Symbols (trifecta)" section
/trifecta-status  # shows graph health

# Phase B
git commit --allow-empty -m "test: trigger trifecta reindex"
trifecta graph status -s . --json  # verify timestamp updated

# Phase C
fork telemetry report --type trifecta.index

# Phase D
fork doctor status  # shows Trifecta health line
```

## Risks
- **Extension performance** — `trifecta graph index` + `graph search` = ~440ms per agent start. Acceptable for interactive use, may add up in multi-agent spawns. Mitigation: cache for session duration (index once per session).
- **System prompt size** — Adding 500 tokens of symbol info. Pi has ~200k context window. Negligible.
- **pre-commit latency** — `trifecta graph index` adds ~300ms to every commit. Acceptable.
- **Trifecta not installed** — Extension checks `which trifecta` and silently skips. No error.

## Multi-Run Strategy
1. **This run**: Phase A (extension) + Phase B (git hook) — highest impact, lowest risk
2. **Next run**: Phase C (telemetry) + Phase D (doctor) — observability
3. **Future runs**: Phase E evolves as Trifecta repo changes
4. Each run reads this file to pick up where it left off

## Future (Trifecta repo-side, separate roadmap)
- Method-level graph resolution (tree-sitter improvements)
- `graph search --json` edge inclusion (caller/callee inline)
- `ctx search --json` native JSON output (currently needs `--explain`)
- Daemon auto-start from pi extension
- MCP bridge for direct tool registration

---

## Exploration Round 3 Findings (Apr 22)

### Daemon Architecture
- **Unix socket server** at `/tmp/trifecta_lsp_<segment_id>.sock` (max 100 chars path)
- **Protocol**: newline-delimited JSON, max 16KB per message
- **Operations**: PING, HEALTH, SHUTDOWN + LSP method routing (textDocument/hover, etc.)
- **Security**: runtime dir allowlist (`~/.local/share/trifecta`, `~/.config/trifecta`, `~/.cache/trifecta`)
- **TTL**: 300s idle timeout (configurable via `TRIFECTA_DAEMON_TTL`)
- **Auto-start**: NOT on-demand. Must be started manually via `trifecta daemon start`
- **Client**: `DaemonClient(socket_path, timeout=5.0).send(request)` → JSON response

### MCP Server (7 tools)
Entry point: `trifecta-mcp --repo <path>` → stdio JSON-RPC 2.0

| Tool | Params | Returns | State-dependent |
|------|--------|---------|-----------------|
| `ctx_search` | `query: string` | Search results | YES (needs READY/DEGRADED) |
| `ctx_get` | `ids: array` | Retrieved chunks | YES |
| `ctx_init` | (none) | Bootstrap confirmation | NO |
| `ast_analyze` | `path: string` | `{symbols: [name]}` | YES |
| `graph_query` | `symbol: string` | Graph data | YES |
| `ctx_plan` | `task: string` | Plan result | YES |
| `ctx_health` | (none) | `{state, engram_detected}` | NO |

**State machine**: `UNINITIALIZED` → `SYNCING` → `READY` → `DEGRADED` → `FAILED`

### Trifecta Telemetry
- **File-based**: `_ctx/telemetry/events.jsonl`, `metrics.json`, `last_run.json`
- **Health check**: zero-hit ratio threshold (30% warn), LSP invariants
- **Exit codes**: 0=OK, 2=WARN, 3=FAIL
- **Metrics**: search counts, zero-hits by source, operational vs fixture ratios

### Multi-Repo State
- **110 registered repos**, 108 are dead temp directories (cleanup candidate)
- **Registration is optional** — graph, index, context all work without it
- **Segment** (`_ctx/` dir) is the real organizational unit, not repo registration
- **5 repos have graph DBs**: tmux_fork (658 nodes), anchor_dope, examen_grado, + 2 others
- **Repo registry**: `~/.trifecta/trifecta_repos.json` (JSON file, not DB)

### Pi Spawn Paths — ALL Load Extensions

| Spawn method | Extensions? | session_start | before_agent_start | UI? |
|---|---|---|---|---|
| `pi` interactive | YES | YES | YES | YES |
| `pi -p "prompt"` | YES | YES | YES | NO |
| `pi --mode json -p` | YES | YES | YES | NO |
| `pi --plan` | YES | YES | YES | NO |
| tmux-live launch | YES (fresh) | YES | YES | NO |
| `/fork` | YES (same proc) | YES | YES | YES |
| `/reload` | YES (fresh) | YES | YES | YES |

**Critical**: ALL spawn paths fire `before_agent_start`. Our extension will inject context for EVERY agent, not just orchestrated ones.

### Extension Execution Order
- **Alphabetical by filename** within each directory
- `context-loader.ts` (5th) runs before `tool-guard.ts` (14th)
- Deterministic but not configurable — name the extension appropriately
- `trifecta-context-loader.ts` sorts after `tool-guard.ts` — executes AFTER context-loader, which is fine (independent)

### Existing Extension Patterns (for reuse)

| Extension | Pattern | Reuse Value |
|-----------|---------|-------------|
| `context-loader.ts` | `before_agent_start` → system prompt append + cache | **Exact template** |
| `compact-memory-bridge.ts` | `before_agent_start` → keyword search + inject + `session_before_compact` | Recovery pattern |
| `n8n-mcp-bridge.ts` | `registerTool()` × 6 + lazy MCP process spawn | MCP bridge pattern |
| `tool-guard.ts` | `tool_call` → policy check | Policy enforcement |
| `auto-session-name.ts` | `session_start` → set name from cwd | Naming pattern |
| `passive-capture.ts` | `turn_end` → capture tool usage | Passive tracking |

---

## Exploration Round 4 Findings (Apr 22)

### Graph Search Output Format
```json
{
  "status": "ok",
  "query": "memory service",
  "results": [
    {"file": "/abs/path/to/file.py", "snippet": "...<b>highlighted</b>..."}
  ]
}
```
- **97 tokens/node** — very compact
- `graph search -q "X" -s . --json` works (NOT `--symbol`)
- **Bug**: `graph callers`/`callees` return empty despite 200 edges in DB
- **Bug**: `metadata_json` always null

### FTS Query Output Format
```json
{
  "status": "ok",
  "query": "memory service",
  "results": [
    {"file": "/abs/path/to/file.py", "snippet": "...<b>highlighted</b>..."}
  ]
}
```
- **~200 tokens/result**
- **Critical**: No `.gitignore` — indexes `.venv/`, `__pycache__/`, `.worktrees/`
- Must post-filter: skip `.venv/`, `node_modules/`, `__pycache__/`, `.git/`
- Both ~140ms latency

### context-inject Pipeline (5-tier cascade)
```
Cache check → Tier -1 (trifecta load) → Tier 0 (ctx plan+search) → Tier 2 (FTS5) → skill-resolver → empty
```

**Tier -1**: `trifecta load -s . -t "task" -m pcc` — single macro, ~168ms
**Tier 0**: `ctx plan --json` → extract 6 keywords → `ctx search` multi-pass → `ctx get` with budget
**Tier 2**: `trifecta query -r . "keywords" --json` — FTS5 fallback
**Tier 3**: `skill-resolver` — skill-hub tag matching
**Tier 4**: Empty stub + zero-hit tracking

### Keyword Extraction (portable to TypeScript)
- 80+ stop words (English + domain: `write create implement fix build...`)
- CJK/non-Latin detection via Unicode ranges (perl → JS: trivial)
- Min length: CJK=1, Latin=3
- 4 original + 2 stemmed = 6 terms max
- Stemmer: 25+ suffix patterns with fix table (50 lines)
- **Portable**: pure string manipulation, no NLP deps

### ctx get (chunk retrieval)
- Modes: `excerpt`, `skeleton`, `raw` (NO `full`)
- `--budget-token-est` controls excerpt length
- IDs: `repo:<relative_path>:<fingerprint>`
- With 500 token budget across 2 chunks: ~417 tokens output

### Config Files
| File | Purpose |
|------|---------|
| `trifecta_config.json` | Segment metadata (name, scope, repo_root, profile) |
| `anchors.yaml` | Strong/weak anchors + multilingual map (25+ Spanish→English terms) |
| `aliases.yaml` | Schema v3 — 17 feature groups with priority, triggers, bundle paths |
| `prime_*.md` | Ordered reading list (258 lines, 80+ file refs) |
| `agent_*.md` | Tech stack reference (181 lines) |

### BootstrapUseCase — MCP Injection
- **Claude**: separate JSON per server in `~/.claude/mcp/trifecta.json`
- **OpenCode**: merged into `~/.config/opencode/settings.json` → `mcpServers`
- MCP command: `uvx --from git+https://github.com/Gentleman-Programming/trifecta_dope trifecta-mcp run --repo <path>`
- **pi is NOT supported** — needs `PiConfigAdapter` implementing `AgentConfigAdapter` protocol

### F1 Makefile Targets
| Target | Command | Purpose |
|--------|---------|---------|
| `sync` | `trifecta ctx sync --segment .` | Refresh context pack |
| `warmup` | `trifecta_manager.sh warmup` | Deep intelligence (LSP+Graph activation) |
| `search` | `trifecta ctx search --segment . --query "$(Q)" --limit 6` | Search |
| `status`/`doctor`/`check`/`clean` | Various | Ops |

### Recommendation for Extension Architecture
1. **Primary**: `graph index` (300ms) + `graph search` (140ms) = **440ms total**
2. **Skip FTS**: 70% noise from `.venv/` — not worth post-filtering overhead
3. **Token budget**: 5 graph results ≈ 500 tokens — compact enough for system prompt
4. **Cache**: reuse content-validation pattern from context-inject (marker-based, no TTL)
5. **Keyword extraction**: port 50-line stemmer + 80-word stop list to TypeScript
