# Trifecta Full Integration Roadmap

**Created**: 2026-04-20  
**Status**: DRAFT — pending approval  
**Scope**: Wire 8 disconnected Trifecta subsystems into tmux-fork orchestrator pipeline  
**Source**: Explorer findings from 8 subsystems + 6 existing orchestrator scripts

---

## Current State

### WIRED (6 scripts, working)
| Script | Commands | Phase |
|--------|----------|-------|
| `trifecta-context-inject` | `load`, `ctx plan`, `ctx search`, `ctx get` | Phase 3 (Spawn) |
| `trifecta-affected-symbols` | `ast symbols` | Phase 3 (Implementers) |
| `trifecta-verifier-check` | AST callers via `ctx search` | Phase 5.5 (Validate) |
| `trifecta-quality-report` | `telemetry report` | Phase 6 (Cleanup) |
| `trifecta-preload` | `ctx plan`, `ctx search` | Phase 3 (Explorers) |
| `skill-resolver` | `load` (fallback) | Phase 3 (Fallback) |

### NOT WIRED (8 gaps)
1. `ctx stats` — BROKEN (surrogate unicode in `json.dumps`)
2. `session append` — working CLI, not wired to orchestrator
3. `ast hover` — LSP stub, WIP (daemon spawn + timeout logic exists)
4. `ast snippet` — STUB (returns "not implemented")
5. `daemon start/stop` — not automated, manual only
6. `ctx build/sync` — manual, not automated in flow
7. FTS5 index/query — `IndexUseCase` exists, disconnected from `ctx search`
8. LSP daemon unification — `lsp_daemon.py` vs `daemon_manager.py` duplication

---

## Roadmap — 8 Work Orders

Ordered: quick wins → foundation → integration → LSP completion.

```
WO-1 (XS)  ctx stats unicode fix
WO-2 (XS)  session append wiring
WO-3 (S)   daemon warmup automation
WO-4 (S)   ctx build/sync auto-trigger
WO-5 (M)   AST snippet wiring (SkeletonMapBuilder → ast snippet)
WO-6 (M)   FTS5 → ctx search integration
WO-7 (M)   LSP daemon unification
WO-8 (L)   LSP Hover Completion
```

### Dependency Graph

```
WO-1 ──────────────────────────────────────────────┐
WO-2 ──────────────────────────────────────────────┤
WO-3 ──┬── WO-5 ──┐                               │
       │           ├── WO-8 (LSP Hover)            │
       └── WO-7 ──┘                               │
WO-4 ───────────────────── WO-6 ───────────────────┤
                                                    ▼
                                              ALL DONE
```

**Critical path**: WO-3 → WO-7 → WO-8 (LSP Hover is the final milestone)

---

## WO-1: ctx stats Unicode Fix

**Priority**: P0 (blocking telemetry)  
**Effort**: XS (~30 min)  
**Status**: **DONE** (2026-04-21)  
**Blocks**: Nothing (unblocks `ctx stats` for monitoring)  
**Depends on**: Nothing

### Problem
`json.dumps()` in `telemetry.py` (lines 187, 229, 308) crashes on surrogate characters. Events with non-BMP Unicode (CJK, emoji, etc.) cause `UnicodeEncodeError` when writing to `events.jsonl`.

### Fix
Add `ensure_ascii=False` to all 3 `json.dumps()` calls in `src/infrastructure/telemetry.py`:

```python
# Line 187
content = json.dumps(payload, ensure_ascii=False)

# Line 229
content = json.dumps(summary, indent=2, ensure_ascii=False)

# Line 308
normalized_lines.append(json.dumps(row, ensure_ascii=False))
```

### Done Criteria
- [ ] All 3 `json.dumps()` calls in `telemetry.py` have `ensure_ascii=False`
- [ ] `trifecta ctx stats -s .` runs without error on a repo with CJK content
- [ ] `trifecta telemetry report -s .` runs without error
- [ ] Existing tests pass

---

## WO-2: Session Append Wiring

**Priority**: P1 (observability)  
**Effort**: XS (~1 hour)  
**Blocks**: Nothing  
**Depends on**: Nothing

### Problem
`trifecta session append` is a fully working CLI command but is never called by the orchestrator. Sub-agent sessions leave no trail in `_ctx/session_*.md`.

### Implementation
Create `~/.pi/agent/skills/tmux-fork-orchestrator/scripts/trifecta-session-log`:

```bash
#!/usr/bin/env bash
# trifecta-session-log - Append session entry after sub-agent completes
# Called by tmux-live after agent finishes (Phase 6 cleanup)
set -euo pipefail

SEGMENT="${1:-.}"
SUMMARY="$2"
FILES="$3"  # comma-separated

trifecta session append \
    --segment "$SEGMENT" \
    --summary "$SUMMARY" \
    --files "$FILES" \
    2>/dev/null || true  # non-blocking: never fail the orchestrator
```

Wire into orchestrator Phase 6 (cleanup):
- After `trifecta-quality-report`, call `trifecta-session-log`
- Pass: agent role, files modified, summary of work

### Done Criteria
- [ ] `trifecta-session-log` script exists in orchestrator scripts/
- [ ] Called in Phase 6 after quality report
- [ ] `_ctx/session_*.md` gets appended entries after sub-agent runs
- [ ] Non-blocking: failure doesn't halt orchestrator

---

## WO-3: Daemon Warmup Automation

**Priority**: P1 (foundation for WO-5, WO-7, WO-8)  
**Effort**: S (~2-3 hours)  
**Blocks**: WO-5, WO-7, WO-8  
**Depends on**: Nothing

### Problem
`trifecta daemon start` must be run manually before any LSP-dependent operations. No auto-start, no health-check-before-use. Two parallel daemon implementations exist (`lsp_daemon.py` vs `daemon_manager.py`).

### Implementation
Create `~/.pi/agent/skills/tmux-fork-orchestrator/scripts/trifecta-daemon-warmup`:

```bash
#!/usr/bin/env bash
# trifecta-daemon-warmup - Ensure daemon is warm before LSP operations
# Called before ast hover, ast snippet, or any LSP-dependent command
set -euo pipefail

SEGMENT="${1:-.}"
TIMEOUT="${2:-30}"  # seconds

# Check if daemon is already running
STATUS=$(trifecta daemon status --segment "$SEGMENT" 2>/dev/null || echo "stopped")
if echo "$STATUS" | grep -q "running"; then
    echo "daemon already warm"
    exit 0
fi

# Start daemon
trifecta daemon start --segment "$SEGMENT" 2>/dev/null || {
    echo "WARNING: daemon start failed, LSP operations will use fallback" >&2
    exit 0  # non-fatal
}

# Wait for ready (with timeout)
ELAPSED=0
while [[ $ELAPSED -lt $TIMEOUT ]]; do
    STATUS=$(trifecta daemon status --segment "$SEGMENT" 2>/dev/null || echo "starting")
    echo "$STATUS" | grep -q "running\|ready" && { echo "daemon warm (${ELAPSED}s)"; exit 0; }
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

echo "WARNING: daemon warmup timed out after ${TIMEOUT}s" >&2
exit 0  # non-fatal
```

Wire into orchestrator:
- Phase 3 (spawn): call `trifecta-daemon-warmup` in background before spawning implementers
- Phase 5.5 (validate): call before `trifecta-verifier-check` if AST needed

### Done Criteria
- [ ] `trifecta-daemon-warmup` script exists
- [ ] Called in Phase 3 (background) before implementers
- [ ] Timeout is configurable (default 30s)
- [ ] Non-blocking: daemon failure doesn't halt orchestrator (fallback path)
- [ ] Manual test: daemon auto-starts on `tmux-live init`

---

## WO-4: ctx build/sync Auto-Trigger

**Priority**: P1 (data freshness)  
**Effort**: S (~2-3 hours)  
**Blocks**: WO-6  
**Depends on**: Nothing

### Problem
`ctx build` and `ctx sync` must be run manually. Sub-agents may work against stale context packs. No automated trigger when source files change significantly.

### Implementation
Create `~/.pi/agent/skills/tmux-fork-orchestrator/scripts/trifecta-auto-sync`:

```bash
#!/usr/bin/env bash
# trifecta-auto-sync - Auto-sync context pack if stale
# Called at orchestrator init (Phase 1) and after implementer changes (Phase 5.5)
set -euo pipefail

SEGMENT="${1:-.}"
MAX_AGE_HOURS="${2:-4}"  # max age before forced sync

CTX_DIR="$SEGMENT/_ctx"
PACK="$CTX_DIR/context_pack.json"

# Check staleness
if [[ -f "$PACK" ]]; then
    AGE_SEC=$(( $(date +%s) - $(stat -f %m "$PACK" 2>/dev/null || stat -c %Y "$PACK" 2>/dev/null || echo 0) ))
    AGE_HOURS=$(( AGE_SEC / 3600 ))
    if [[ $AGE_HOURS -lt $MAX_AGE_HOURS ]]; then
        echo "context pack fresh (${AGE_HOURS}h old, threshold ${MAX_AGE_HOURS}h)"
        exit 0
    fi
fi

# Stale or missing — rebuild
echo "rebuilding context pack (stale/missing)..."
trifecta ctx sync --segment "$SEGMENT" 2>/dev/null || {
    echo "WARNING: ctx sync failed, using existing pack" >&2
    exit 0
}

echo "context pack rebuilt successfully"
```

Wire into orchestrator:
- Phase 1 (init): call `trifecta-auto-sync` before any sub-agent spawn
- Phase 5.5 (post-implementation): call `trifecta-auto-sync` if implementer modified 3+ files

### Done Criteria
- [ ] `trifecta-auto-sync` script exists
- [ ] Called in Phase 1 (init) before context-inject
- [ ] Called in Phase 5.5 after implementer work (conditional)
- [ ] Staleness threshold configurable (default 4h)
- [ ] `ctx sync` failure is non-blocking

---

## WO-5: AST Snippet Wiring

**Priority**: P2 (code quality context)  
**Effort**: M (~4-6 hours)  
**Blocks**: Nothing directly  
**Depends on**: WO-3 (daemon must be warm)

### Problem
`ast snippet` is a STUB — always returns "not implemented". Meanwhile, `SkeletonMapBuilder` in `ast_models.py` already builds skeleton maps from AST analysis. The snippet extraction logic exists in `ast_parser.py:189` (`extract_snippet`) but is dead code.

### Implementation

**Step 1**: Wire `SkeletonMapBuilder` output into `ast snippet` CLI command.

In `src/infrastructure/cli_ast.py`, replace the stub `snippet` command (line 170-189) with:

```python
@ast_app.command("snippet")
def snippet(
    uri: str = typer.Argument(..., help="File path"),
    segment: str = typer.Option(".", "--segment"),
    line: int = typer.Option(0, "--line", "-l", help="Focus line (0 = full file)"),
    context: int = typer.Option(3, "--context", "-C", help="Lines of context around symbol"),
):
    """Extract code snippets from a file using AST skeleton map."""
    root = Path(segment).resolve()
    file_path = root / uri
    
    if not file_path.is_file():
        _json_output({"error": f"File not found: {uri}"})
        raise typer.Exit(1)
    
    from src.domain.ast_models import SkeletonMapBuilder
    builder = SkeletonMapBuilder()
    skeleton = builder.build(file_path)
    
    if line > 0:
        # Find symbol containing target line
        for node in skeleton.children:
            if node.line <= line <= node.end_line:
                snippet_lines = file_path.read_text().splitlines()
                start = max(0, node.line - 1 - context)
                end = min(len(snippet_lines), node.end_line + context)
                _json_output({
                    "symbol": node.name,
                    "kind": node.kind,
                    "line": node.line,
                    "end_line": node.end_line,
                    "snippet": "\n".join(snippet_lines[start:end]),
                })
                return
        _json_output({"error": f"No symbol found at line {line}"})
    else:
        # Full skeleton
        _json_output({
            "file": uri,
            "symbols": [{"name": n.name, "kind": n.kind, "line": n.line, "end_line": n.end_line} for n in skeleton.children],
        })
```

**Step 2**: Create orchestrator script `trifecta-ast-snippet`:

```bash
#!/usr/bin/env bash
# trifecta-ast-snippet - Extract code snippet for a symbol
# Used by implementers to get symbol context without reading entire files
set -euo pipefail
URI="$1"
LINE="${2:-0}"
SEGMENT="${3:-.}"
trifecta ast snippet "$URI" --line "$LINE" --segment "$SEGMENT" 2>/dev/null || true
```

Wire into `trifecta-context-inject`:
- After `ctx get` retrieves chunk IDs, if chunk is a code file, augment with `ast snippet` for the symbol context

### Done Criteria
- [ ] `ast snippet` CLI returns actual code snippets (not "not implemented")
- [ ] `SkeletonMapBuilder` is the backend (deterministic, no LSP needed)
- [ ] `trifecta-ast-snippet` orchestrator script exists
- [ ] Snippets are used to augment context-inject output for code chunks
- [ ] Test: `trifecta ast snippet src/application/services/memory_service.py --line 45 --segment .` returns the containing symbol

---

## WO-6: FTS5 → ctx search Integration

**Priority**: P2 (search quality)  
**Effort**: M (~4-6 hours)  
**Blocks**: Nothing directly  
**Depends on**: WO-4 (auto-sync ensures FTS5 index is fresh)

### Problem
`IndexUseCase` builds a SQLite FTS5 index (`search.db`) but it's disconnected from `ctx search`. The FTS5 index could provide semantic fallback when `ctx search` (which uses `context_pack.json`) returns zero hits.

### Implementation

**Step 1**: Wire FTS5 as fallback in `trifecta-context-inject`.

In `trifecta-context-inject`, after all keyword-based `ctx search` queries fail (the zero-hit path), add:

```bash
# Tier 2: FTS5 fallback (broader coverage than context_pack)
if [[ ${#ALL_IDS[@]} -eq 0 ]]; then
    FTS_QUERY=$(trifecta query --repo "$SEGMENT" "$KEYWORDS" --limit "$LIMIT" --json 2>/dev/null || true)
    if [[ -n "$FTS_QUERY" ]]; then
        # Parse FTS5 results and extract file paths
        FTS_IDS=$(echo "$FTS_QUERY" | python3 -c "
import sys, json
try:
    data = json.loads(sys.stdin.read())
    for r in data.get('results', []):
        path = r.get('file_rel', r.get('file', ''))
        if path:
            print(f'repo:{path}')
except: pass
" 2>/dev/null || true)
        # Use FTS results to create synthetic context
        if [[ -n "$FTS_IDS" ]]; then
            # FTS results are raw files, not chunked — read first N lines
            for fpath in $FTS_IDS; do
                fpath=$(echo "$fpath" | sed 's/^repo://')
                if [[ -f "$SEGMENT/$fpath" ]]; then
                    echo "### $fpath (FTS5 fallback)"
                    head -50 "$SEGMENT/$fpath"
                fi
            done
        fi
    fi
fi
```

**Step 2**: Ensure FTS5 index is rebuilt during `trifecta-auto-sync` (WO-4).

Add to `trifecta-auto-sync`:
```bash
# Also rebuild FTS5 index
trifecta index --segment "$SEGMENT" 2>/dev/null || true
```

### Done Criteria
- [ ] FTS5 index is rebuilt during `trifecta-auto-sync`
- [ ] When `ctx search` returns zero hits, FTS5 `query` is used as Tier 2 fallback
- [ ] FTS5 fallback results are injected into context-inject output
- [ ] Zero-hit rate decreases by measurable amount (track via `trifecta-quality-report`)
- [ ] Non-blocking: FTS5 failure falls through to skill-resolver

---

## WO-7: LSP Daemon Unification

**Priority**: P1 (foundation for WO-8)  
**Effort**: M (~6-8 hours)  
**Blocks**: WO-8  
**Depends on**: WO-3 (daemon warmup)

### Problem
Two parallel daemon implementations:
1. `src/infrastructure/lsp_daemon.py` — `LSPDaemonClient` with socket-based IPC
2. `src/infrastructure/daemon/` — newer directory with `runner.py`, `socket_manager.py`, `protocol.py`, `lsp_handler.py`
3. `src/platform/daemon_manager.py` — platform-level daemon lifecycle

The `daemon/` directory appears to be a refactor-in-progress. The `ast hover` CLI uses `LSPDaemonClient` from `lsp_daemon.py` (the older one). Need to unify.

### Implementation

**Phase A — Audit** (1 hour):
1. Map which code paths use `lsp_daemon.py` vs `daemon/`
2. Identify which is "canonical" (likely `daemon/` given the directory structure)
3. Document the migration path

**Phase B — Consolidate** (3-4 hours):
1. If `daemon/` is canonical: migrate `ast hover` CLI to use `daemon/runner.py` instead of `LSPDaemonClient`
2. If `lsp_daemon.py` is canonical: delete `daemon/` directory and wire everything through `LSPDaemonClient`
3. Update `daemon_use_case.py` to use the unified implementation
4. Remove dead code path

**Phase C — Verify** (1-2 hours):
1. `trifecta daemon start` → `trifecta daemon status` → `trifecta daemon stop` lifecycle works
2. `trifecta ast hover` uses the unified daemon
3. `trifecta-daemon-warmup` (WO-3) works with unified daemon

### Done Criteria
- [ ] Only ONE daemon implementation exists (other is deleted or clearly marked deprecated)
- [ ] `ast hover` CLI uses the canonical daemon
- [ ] `daemon start/stop/status` lifecycle works end-to-end
- [ ] No dead daemon code paths remain
- [ ] `trifecta doctor -r .` passes daemon checks

---

## WO-8: LSP Hover Completion (Final Milestone)

**Priority**: P2 (completes the WIP stub)  
**Effort**: L (~8-12 hours)  
**Blocks**: Nothing (this IS the final milestone)  
**Depends on**: WO-3 (daemon warmup), WO-7 (daemon unification)

### Problem
`ast hover` has full infrastructure:
- Daemon spawn + connect logic (in `cli_ast.py:196-320`)
- LSP JSON-RPC protocol (`lsp_client.py` is production-ready)
- READY-state polling with timeout
- `textDocument/hover` request/response handling

BUT: The `--require-lsp` flag always errors with "LSP_NOT_IMPLEMENTED" (line 309). The hover response is generated correctly but then overridden. The final piece is:
1. Remove the artificial `--require-lsp` block
2. Validate the actual hover response content
3. Handle edge cases (multi-line hover, markdown contents, ranges)

### Implementation

**Step 1**: Remove the artificial block in `cli_ast.py` (~line 305-316):

```python
# REMOVE this block (it always errors even on success):
# if require_lsp:
#     response = LSPResponse.error_response(
#         error_code="LSP_NOT_IMPLEMENTED",
#         ...
#     )
```

**Step 2**: Validate hover response parsing:

The LSP hover response has structure:
```json
{
  "contents": { "kind": "markdown", "value": "..." },
  "range": { "start": {"line": 0, "character": 0}, "end": {...} }
}
```

Ensure the response formatter handles:
- `MarkupContent` (kind + value)
- `MarkedString` (plain string or {language, value})
- `array of MarkedString`
- Null/empty contents (return "no hover info")

**Step 3**: Create orchestrator script `trifecta-hover-context`:

```bash
#!/usr/bin/env bash
# trifecta-hover-context - Get LSP hover info for a symbol
# Used by verifiers to check type signatures without reading files
set -euo pipefail

FILE="$1"
LINE="$2"
CHAR="$3"
SEGMENT="${4:-.}"

# Ensure daemon is warm
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/trifecta-daemon-warmup" "$SEGMENT" 2>/dev/null || true

# Request hover
RESULT=$(trifecta ast hover "$FILE" --line "$LINE" --char "$CHAR" --segment "$SEGMENT" 2>/dev/null || true)

if [[ -n "$RESULT" ]]; then
    echo "$RESULT"
else
    echo '{"status": "no_hover", "message": "LSP returned no hover info"}'
fi
```

Wire into `trifecta-verifier-check`:
- After extracting symbols from modified files, request hover for each symbol
- Include hover info (type signatures, docstrings) in the verification report

**Step 4**: End-to-end test:

```bash
# Start daemon
trifecta daemon start --segment .

# Test hover on a real symbol
trifecta ast hover src/application/services/memory_service.py --line 1 --char 7 --segment .

# Should return type info for the module or first symbol
# Test --require-lsp flag
trifecta ast hover src/application/services/memory_service.py --line 1 --char 7 --segment . --require-lsp
# Should succeed (not error with LSP_NOT_IMPLEMENTED)
```

### Done Criteria
- [ ] `ast hover` returns actual LSP hover data (type signatures, docstrings)
- [ ] `--require-lsp` succeeds when LSP is available (no artificial block)
- [ ] `--require-lsp` fails gracefully when LSP unavailable (fallback response)
- [ ] Hover handles all MarkupContent variants (markdown, plaintext, arrays)
- [ ] `trifecta-hover-context` orchestrator script exists
- [ ] Hover info included in verifier-check output
- [ ] E2E test: daemon start → hover request → meaningful response
- [ ] No regressions in existing orchestrator scripts

---

## Summary

| WO | Effort | Priority | Depends | Blocks |
|----|--------|----------|---------|--------|
| WO-1 ctx stats fix | XS (30m) | P0 | — | — |
| WO-2 session append | XS (1h) | P1 | — | — |
| WO-3 daemon warmup | S (2-3h) | P1 | — | WO-5, WO-7, WO-8 |
| WO-4 ctx auto-sync | S (2-3h) | P1 | — | WO-6 |
| WO-5 AST snippet | M (4-6h) | P2 | WO-3 | — |
| WO-6 FTS5 integration | M (4-6h) | P2 | WO-4 | — |
| WO-7 daemon unification | M (6-8h) | P1 | WO-3 | WO-8 |
| WO-8 LSP Hover | L (8-12h) | P2 | WO-3, WO-7 | — |

**Total estimated effort**: ~28-40 hours  
**Critical path**: WO-1 → WO-3 → WO-7 → WO-8 (~18-24 hours)  
**Parallel tracks**: WO-2, WO-4 can run concurrently with WO-3  

### Execution Order

```
Sprint 1 (Day 1):     WO-1 + WO-2                    (quick wins, ~1.5h)
Sprint 2 (Day 2-3):   WO-3 + WO-4                    (foundation, ~5h)
Sprint 3 (Day 3-5):   WO-5 + WO-6 (parallel)         (integration, ~10h)
Sprint 4 (Day 5-7):   WO-7                            (consolidation, ~7h)
Sprint 5 (Day 7-10):  WO-8                            (final milestone, ~10h)
```

### Risks

1. **LSP binary dependency**: pyright/pylsp must be installed. Mitigate: detect at init, warn clearly.
2. **Daemon stability**: socket-based IPC may hang. Mitigate: timeout in all scripts, non-blocking fallback.
3. **Trifecta version compatibility**: changes to `telemetry.py` require a Trifecta release. Mitigate: PR to trifecta_dope, or fork the fix.
4. **Context pack freshness**: auto-sync may be slow on large repos. Mitigate: 4h staleness threshold, async rebuild.
5. **WO-7 scope creep**: daemon unification may reveal more duplication. Mitigate: time-box audit to 1h, escalate if >2 implementations found.

## Session Summary — 2026-04-20

### P4 Status: ALL COMPLETE (8/8 WOs + Bug Hunt)

| WO | Description | Status | Commits |
|----|-------------|--------|---------|
| WO-1 | ctx stats unicode fix | DONE | c0a4880e |
| WO-2 | session append wiring | DONE | script |
| WO-3 | daemon warmup automation | DONE | script |
| WO-4 | ctx build/sync auto-trigger | DONE | script |
| WO-5 | AST snippet wiring | DONE | script |
| WO-6 | FTS5 fallback integration | DONE | script |
| WO-7 | LSP daemon unification | DONE | 28422c70 |
| WO-8 | LSP hover completion | DONE | d7b10553 |

### Additional Fixes (post-WO-8)

| Fix | Severity | Description |
|-----|----------|-------------|
| Socket/pid/lock path divergence | HIGH | 9 weak points in DaemonManager |
| LSP handshake notification loop | HIGH | Pyright sends window/logMessage before init response |
| Auto-didOpen before hover | MEDIUM | Pyright needs didOpen for hover data |
| DaemonRunner path SSOT | HIGH | Runner also needed daemon_paths fix |
| Race condition TypeError | CRITICAL | _acquire_singleton_lock returned bare False |
| Silent socket failure | HIGH | Directory at socket path not detected |
| Warmup grep mismatch | HIGH | grep -q "running" matched "not running" |
| Nonexistent repo traceback | MEDIUM | mkdir log parent before opening |
| Orphan kill on timeout | MEDIUM | proc.kill() on startup timeout |

### Bug Hunt Results (real-world-bug-hunter skill)

- **Agents**: 3 (Ripper, Walker, Sniper)
- **Tests**: 28 test groups, 65+ individual scenarios
- **Bugs Found**: 9 (1 CRITICAL, 3 HIGH, 3 MEDIUM, 2 LOW)
- **Bugs Fixed**: 7
- **Bugs Closed**: 2 (non-reproducible / expected behavior)
- **Verdict**: PASS — 0 CRITICAL remaining, 0 HIGH remaining

### Key Metrics

| Metric | Before | After |
|--------|--------|-------|
| daemon start | Timeout | ~1s |
| daemon status | "not running" | Correct PID |
| LSP hover | FAILED/DEGRADED | FULL lsp_pyright |
| daemon stop | Can't find PID | Clean |
| Orphan processes | 11+ accumulated | 0 |
| Concurrent requests | Untested | 5 simultaneous |
| Crash recovery | Untested | Restart after SIGKILL |
| Cross-repo isolation | Untested | Independent sockets |

### Merged to trifecta_dope main

Branch `feat/wo8-lsp-hover-completion` merged 2026-04-20.
5 commits pushed to origin/main.
