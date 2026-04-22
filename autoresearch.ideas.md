# autoresearch.ideas.md — CLI Startup Optimization

## Done
1. **Lazy dependencies.py** — Removed 12 unused re-exports, added `__getattr__` for heavy ones. DI no longer loaded at import time. All commands -35-42%.
2. **Fast workspace detection** — `_detect_workspace_fast()` bypasses DI container. `detect_memory_db_path` 170ms → 15ms (actual call). DI never loaded for any CLI command.

## Remaining breakdown (save ≈ 200ms)
| Component | Time | Optimizable? |
|-----------|------|-------------|
| Python + uv startup | ~30ms | No (interpreter overhead) |
| typer | ~22ms | No (framework) |
| container.py imports | ~56ms | Maybe — could lazy-import Database/migrations |
| GitCommandExecutor (workspace detect) | ~15ms | No (git subprocess) |
| DB connect + migrations | ~10ms | Maybe — could cache connection |
| actual save operation | ~1ms | No (already fast) |

## Future ideas (diminishing returns)
- Lazy-import Database/migrations in container.py (save ~30ms)
- Cache DB connection across invocations (needs daemon/pipe)
- Merge typer subcommands into single module (reduce import count)
EOF