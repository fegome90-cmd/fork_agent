# Sync Pipeline — Functional Test Report
> Date: 2026-04-17
> Baseline: Engram `engram sync` / `engram sync --import` documented behavior

## Test Environment
- DB: 261 observations, 107 mutations in journal
- Sync dir: data/sync/ with git repo, 4 commits

## Test Matrix

| # | Test | Result | Notes |
|---|------|--------|-------|
| T1 | `sync status` | **FIXED** | Mutation count now tracked correctly |
| T2 | `sync export` (full) | **PASS** | 261 obs → 3 chunks + manifest with SHA256 |
| T3 | `sync import` (full into fresh DB) | **PASS** | 261 imported, 0 ghost mutations |
| T4 | `sync push` (incremental + git) | **PASS** | Exports mutations, commits to git |
| T5 | `sync push` to non-bare remote | **FIXED** | Now returns False with warning log on push failure |
| T6 | `sync pull` from empty remote | **PASS** | Returns "No new chunks" |
| T7 | `sync log` | **PASS** | Shows mutation journal |
| T8 | Full roundtrip (push → clone → import) | **FIXED** | Explicit type validation with ALLOWED_TYPES check |

## Bugs Found

### BUG-1 [FIXED]: mutation_count never updated (LOW)
- **Symptom:** `sync status` shows `Mutation count: 0` despite 107 mutations in table
- **Root cause:** `sync_status.mutation_count` column is never incremented by `record_mutation()`
- **File:** `src/infrastructure/persistence/repositories/sync_repository.py`
- **Fix:** Add `UPDATE sync_status SET mutation_count = mutation_count + 1` in `record_mutation()`
- **Impact:** Display only, no data loss

### BUG-2 [FIXED]: git push silently fails on non-bare repos (MEDIUM)
- **Symptom:** CLI reports "Push successful" but remote is empty
- **Root cause:** `_run_git()` uses `subprocess.run` without `check=True`, so `CalledProcessError` is never raised
- **File:** `src/infrastructure/sync/git_sync.py:77`
- **Fix:** Check `result.returncode != 0` after `_run_git("push", ...)`
```python
result = self._run_git("push", "origin", "main")
if result.returncode != 0:
    logger.warning("Push failed: %s %s", result.stdout, result.stderr)
    return False
return True
```
- **Impact:** False positive on push status

### BUG-3 [FIXED]: metadata.type fallback creates invalid Observation (HIGH)
- **Symptom:** `get_all()` crashes with ValueError on imported data
- **Root cause:** `_row_to_observation` uses `or` fallback: `type_ = db_type or metadata_dict.get("type")`. When db_type is NULL and metadata has a `"type"` key with non-standard value, validation fails.
- **File:** `src/infrastructure/persistence/repositories/observation_repository.py:481`
- **Fix:** Use explicit fallback with validation:
```python
type_ = row["type"] if "type" in column_names else None
if type_ is None and metadata_dict:
    meta_type = metadata_dict.get("type")
    if meta_type and meta_type in self._ALLOWED_TYPES:
        type_ = meta_type
```
- **Impact:** Import roundtrip can crash on observations with non-standard metadata types

## Comparison: Engram Flow vs Ours

### Engram: `engram sync`
1. Auto-detects project from git remote ✓
2. Exports to `.engram/` in repo root ✓ (ours: `data/sync/`)
3. Chunked JSONL + manifest ✓
4. Committed to git ✓
5. Shared via `git push` ✓

### Ours: `memory sync push`
1. No auto-detection (manual `--project`) — **GAP** (detect_project_from_remote added but not wired)
2. Exports to `data/sync/` ✓
3. Chunked JSONL.gz + manifest ✓
4. Committed to git ✓
5. Shared via `git push` ✓ (but silent failures on non-bare repos)

### Engram: `engram sync --import`
1. Reads `.engram/` from cloned repo ✓
2. Validates checksums ✓ (Engram docs don't specify, but we added it)
3. Deduplicates by chunk_id ✓
4. Project consolidation ✓ — **GAP** (we don't have this)

### Ours: `memory sync pull`
1. `git pull --rebase` from remote ✓
2. Validates checksums ✓ (newly added)
3. Deduplicates by chunk_id ✓
4. No project consolidation — **GAP**

## Remaining Gaps vs Engram

| Gap | Priority | Status |
|-----|----------|--------|
| Wire `detect_project_from_remote` into save commands | P1 | Function exists, not wired |
| Fix git push silent failure | P1 | BUG-2 |
| Fix metadata.type fallback | P1 | BUG-3 |
| Fix mutation_count display | P2 | BUG-1 |
| Project consolidation command | P2 | Not implemented |
| Sync dir convention (`.engram/` style) | P3 | Currently `data/sync/` |
| MCP server for sync | P3 | Not implemented |
