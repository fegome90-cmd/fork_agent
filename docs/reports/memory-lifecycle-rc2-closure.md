# Memory Lifecycle RC-2 — Closure Note

**Date**: 2026-04-24
**Status**: CLOSED — daily controlled use
**Authority**: SHA256 `ffb1ed2a0513eb8ebbb2fd1e24bd15f47ad6f57b`

---

## 1. Summary

RC-2 closes the reliability debt introduced by fire-and-forget saves in `agent_end`. No new features were added. The change is limited to observability: every asynchronous save is now tracked, errors are captured, and shutdown performs a bounded flush before resetting state.

**Scope**: 15 lines across 4 locations in a single file.

## 2. Evidence

| Artifact | Value | Verification Command |
|----------|-------|----------------------|
| File | `~/.pi/agent/extensions/00-compact-memory-bridge.ts` | `wc -l` → 1233 |
| SHA256 | `ffb1ed2a0513eb8ebbb2fd1e24bd15f47ad6f57b` | `shasum` |
| before_agent_start p95 | 309.2ms | 30 iterations, parallel wall-clock |
| Official DB | 1542 obs, FTS=1542 | `SELECT count(*) FROM observations` = `SELECT count(*) FROM observations_fts` |
| Legacy DB | 744 obs, unchanged | `SELECT count(*) FROM observations` on legacy path |
| Real session | 10 steps, 32/32 checks PASS | Script at `/tmp/rc2-real-session.py` |
| Verification | 27/27 checks PASS | Script at `/tmp/rc2-verify.py` |

## 3. Acceptance Criteria

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | before_agent_start ≤350ms p95 | **PASS** | 309.2ms (30 iters) |
| 2 | Shutdown flush auditable | **PASS** | `flushDeadline` at L689, diagnostic log at L701 |
| 3 | failedSaves = 0 in normal case | **PASS** | 32/32 session checks, all saves succeeded |
| 4 | DB legacy unchanged | **PASS** | 744 before = 744 after |
| 5 | DB official searchable + FTS synced | **PASS** | 1542 = 1542 |
| 6 | No split-brain | **PASS** | Single DB path, legacy inert |
| 7 | No new functionality | **PASS** | Only reliability tracking added |

## 4. Residual Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | `safeAsyncSave` counters are in-process only — lost on shutdown | LOW | Diagnostic log captures final state before reset. Persistent audit would require console.log bridging or CLI-side counters. |
| 2 | Flush polls at 100ms intervals — may miss completions between polls | LOW | 100ms granularity is sufficient for RC-2. Production could use callback-based flush (`Promise.all` + timeout race). |
| 3 | `memory save` has no `--session-id` flag | MEDIUM | Observations are not linked to sessions. CLI-level fix required, not bridge-level. Documented. |
| 4 | `~/.pi/` config is not git-versioned | LOW | SHA256 serves as immutable reference. A git repo under `~/.pi/` would provide diff history. |

## 5. RC-3 Candidates

These are **not** committed for RC-3. They are documented here for triage.

- **RC-3a**: Add `--session-id` to `memory save` CLI. Link observations to sessions for audit trails.
- **RC-3b**: Callback-based flush in `session_shutdown` (replace polling with `Promise.race([Promise.all(pending), timeout])`).
- **RC-3c**: Persistent `failedSaves` counter — write to DB or file so audit survives process restart.
- **RC-3d**: Git-initialize `~/.pi/` for change tracking across sessions.
- **RC-3e**: Batch-save CLI command for `agent_end` (single process instead of N parallel processes → reduce SQLite contention).

## 6. Explicit Statement

**No further feature work will be done under RC-2.** The SHA256 `ffb1ed2a0513eb8ebbb2fd1e24bd15f47ad6f57b` is the final artifact. Any change to the bridge file after this point requires a new RC label (RC-3 or later) with its own plan, audit, and acceptance gate.

---

*Closure confirmed by: Memory Lifecycle RC-2 validation session (2026-04-24).*
