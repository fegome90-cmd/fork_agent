# Memory System — Changelog

All notable changes to the pi agent memory system. This file tracks modifications to the bridge extension (`00-compact-memory-bridge.ts`), the memory CLI (`memory`), and the unified SQLite database.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.2.0] — 2026-04-24 — RC-2: Reliability Close-Out

### Added
- `safeAsyncSave()` wrapper for fire-and-forget saves with tracking (`pendingSaves`, `failedSaves`, `lastError`, `lastSaveAt`).
- `pendingSaves` / `failedSaves` counters: increment on dispatch, decrement on settle, capture errors.
- `lastError` string: captures last save failure message (truncated to 200 chars).
- `lastSaveAt` timestamp: tracks last save completion time.
- Flush in `session_shutdown`: polls `pendingSaves` with 2s timeout, 100ms interval. Logs if saves remain pending.
- Diagnostic log on shutdown: `console.log([memory-bridge] shutdown: pending=N failed=N lastError="..." lastSave=...)`.
- State reset of all RC-2 variables in `session_shutdown`.
- Automatic `trifecta ctx sync` on `session_shutdown` (fire-and-forget, 10s timeout, non-blocking). Uses `currentProjectPath` resolved from session context.
- `currentProjectPath` variable: stores actual cwd from `session_start` for trifecta sync.

### Changed
- `agent_end` handler: replaced bare `Promise.all().catch(() => {})` with per-promise `safeAsyncSave()` calls. Each save now independently tracked.

### Performance
- No regression: `before_agent_start` p95=309.2ms (target ≤350ms). Measured with 30 iterations, actual parallel wall-clock.

---

## [0.1.0] — 2026-04-24 — RC-1: Lifecycle Implementation

### Added
- **Module state variables**: `currentProject`, `currentSessionId`, `turnCount`, `lastAutoSave`, `recentFileOps` (Sets for read/written/edited).
- **`detectProject()`** helper: resolves project name from git remote URL or cwd basename.
- **`extractText()`** helper: extracts plain text from assistant/user message objects (handles content arrays, text blocks, tool results).
- **`extractSections()`** helper: splits markdown by `## ` headings, classifies into types (learning, decision, discovery, pattern, bugfix, config).
- **`sanitizeFts5()`** helper: replaces hyphens with spaces, strips AND/OR/NOT operators from FTS5 query strings.
- **`session_start` handler**: project detection + memory session registration + cache warm with compact summaries.
- **`session_shutdown` handler**: memory session end + full state reset.
- **`before_agent_start` handler** (updated): prompt save (strips YAML preamble, truncates 300 chars) + keyword retrieve + cache warm — all via `Promise.all` for parallel execution.
- **`agent_end` handler**: section extraction from last assistant message + task summary generation (if ≥2 turns and file edits exist) + `Promise.all` for parallel saves. Rate-limited to 30s cooldown.
- **`tool_result` handler**: tracks file operations (edit/write/read) into `recentFileOps` Sets.
- **`turn_end` handler**: increments `turnCount`.
- **Cache staleness guard**: cache warm only fires if empty or stale >120s.
- **`body.length > 10` guard** in `extractSections`: prevents spurious short-body fallbacks.

### Changed
- `mem()` wrapper: applies `sanitizeFts5()` to search/retrieve query arguments automatically.
- `AGENTS.md`: updated Memory section with lifecycle documentation, save format, topic key namespace.

### Fixed
- **BUG #1**: Prompt save captured full YAML preamble from skill content. Fixed: strip YAML, truncate to 300 chars.
- **BUG #3**: Section extraction regex failed on empty sections and non-bullet text. Fixed: replaced with `split-by-heading` approach (`text.split(/(?=^## )/gm)`).
- **BUG #4**: Same root cause as #3. Fixed by same approach.
- **BUG #5**: FTS5 hyphen crash (`memory search "split-brain"` → `sqlite3.OperationalError`). Fixed: `sanitizeFts5()` replaces hyphens with spaces.
- **BUG #6**: Short body fallback in `extractSections` produced garbage. Fixed: `body.length > 10` guard.

### Removed
- **`passive-capture.ts`**: deleted. Was a 131-line extension that wrote to legacy DB (`~/Developer/tmux_fork/data/memory.db`), only extracted `## Key Learnings:` sections, and operated independently of the bridge. Backup at `/tmp/memory-migration/passive-capture.ts.backup`.

### Performance
- `before_agent_start`: 909ms → 309ms p95 (66% reduction via `Promise.all`).
- `agent_end`: 761ms → 293ms wall-clock p95 (61% reduction via `Promise.all`). Fire-and-forget makes blocking ~0ms.
- `session_start`: ~280ms p95 (acceptable — once per session).
- `session_shutdown`: ~300ms p95 (acceptable — once per session).
- Scale test: 6524 observations → no performance regression vs 1513.

### Database
- **Split-brain resolved**: migrated 742 observations from legacy DB (`~/Developer/tmux_fork/data/memory.db`) to official DB (`~/.local/share/fork/memory.db`) via SQLite `ATTACH + INSERT OR IGNORE`. Legacy DB now inert (744 obs, no code path writes to it).
- Official DB: 1513→1542 observations, FTS synced, WAL mode.

---

## Known Issues (CLI-level)

These bugs exist in the `memory` CLI tool, not in the bridge extension.

| # | Severity | Description |
|---|----------|-------------|
| 2 | MEDIUM | `memory save` has no `--session-id` flag. Observations cannot be linked to sessions. |
| 5 | LOW | `memory prompt search` with hyphens can crash FTS5 (partially mitigated by `sanitizeFts5` in bridge, but CLI-side fix needed). |

---

## File Reference

| File | Path | Role |
|------|------|------|
| Bridge | `~/.pi/agent/extensions/00-compact-memory-bridge.ts` | Main extension: 8 handlers, 4 tools, 1 command |
| AGENTS.md | `~/.pi/agent/AGENTS.md` | Agent instructions with memory lifecycle docs |
| Official DB | `~/.local/share/fork/memory.db` | Unified SQLite + FTS5 |
| Legacy DB | `~/Developer/tmux_fork/data/memory.db` | Inert, no code path writes to it |
| Deleted | `~/.pi/agent/extensions/passive-capture.ts` | Removed in 0.1.0 |
