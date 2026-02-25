# Database Optimization Plan - IMPLEMENTED

**Goal:** Optimize `memory.db` based on technical analysis

---

## Tasks Completed

### ✅ 1. TTL/Cleanup Policy
- Created: `src/application/services/cleanup_service.py`
- CLI: `memory cleanup --days 90 --dry-run`
- Supports `--vacuum` and `--optimize-ft` flags

### ✅ 2. Health Checks
- Created: `src/infrastructure/persistence/health_check.py`
- CLI: `memory health`
- Checks: integrity, FTS sync, stats
- Supports `--fix` flag to repair FTS

### ⏸️ 3. Telemetry Decision
- Deferred - requires significant implementation work
- Can be revisited later

### ✅ 4. Pagination
- Added `--offset` to list command
- Fixed limit to use SQL LIMIT instead of Python slice
- Now: `memory list --limit 20 --offset 0`

### ✅ 5. Query Logging
- Created: `src/infrastructure/persistence/query_logger.py`
- CLI: `memory stats --slow-queries`
- Created: `memory clear-slow-queries`

---

## New CLI Commands

| Command | Description |
|---------|-------------|
| `memory cleanup --days 90` | Preview old observations to delete |
| `memory cleanup --days 90 --no-dry-run` | Actually delete old observations |
| `memory health` | Check database health |
| `memory stats` | Show database statistics |
| `memory list --limit 10 --offset 0` | List with pagination |

---

## Files Created/Modified

### Created
- `src/application/services/cleanup_service.py`
- `src/infrastructure/persistence/health_check.py`
- `src/infrastructure/persistence/query_logger.py`
- `src/interfaces/cli/commands/cleanup.py`
- `src/interfaces/cli/commands/health.py`
- `src/interfaces/cli/commands/stats.py`

### Modified
- `src/infrastructure/persistence/container.py` - Added cleanup_service, health_check_service
- `src/interfaces/cli/dependencies.py` - Added getters
- `src/interfaces/cli/main.py` - Registered new commands
- `src/application/services/memory_service.py` - Fixed pagination
- `src/interfaces/cli/commands/list.py` - Added offset option

---

## Skipped

- Index on observations.id (redundant - SQLite auto-indexes PK)
