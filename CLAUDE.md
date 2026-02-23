# Fork Agent

CLI tool for AI agent orchestration with memory, workflow, and hooks.

## Project Info

- **Type**: Python CLI (Typer)
- **Entry**: `memory` command → `src.interfaces.cli.main:app`
- **Python**: 3.11+
- **DB**: SQLite (`data/memory.db`)

## PM2 Services

| Name | Type | Description |
|------|------|-------------|
| fork-agent-cli | CLI | Main memory CLI |
| fork-agent-api | API | REST API (future) |

**Claude Commands:**
- /pm2-all - Start all + monit
- /pm2-all-stop - Stop all
- /pm2-all-restart - Restart all
- /pm2-fork-agent-cli - Start CLI + logs
- /pm2-fork-agent-cli-stop - Stop CLI
- /pm2-fork-agent-cli-restart - Restart CLI
- /pm2-logs - View logs
- /pm2-status - View status

**Terminal Commands:**
```bash
# First time (with config file)
pm2 start ecosystem.config.cjs && pm2 save

# After first time (simplified)
pm2 start all          # Start all
pm2 stop all           # Stop all
pm2 restart all        # Restart all
pm2 start fork-agent-cli       # Start single
pm2 stop fork-agent-cli        # Stop single
pm2 logs               # View logs
pm2 monit              # Monitor panel
pm2 resurrect          # Restore saved processes
```

## Commands

```bash
memory save "text"     # Save observation
memory search "query"  # Search
memory list           # List all
memory get <id>        # Get by ID
memory delete <id>    # Delete
memory workflow outline "task"   # Create plan
memory workflow execute          # Execute plan
memory workflow verify            # Verify (tests)
memory workflow ship             # Ship (requires verify)
memory workflow status           # Status
memory schedule add "cmd" 60    # Schedule task
memory schedule list            # List tasks
```

## API

REST API docs: `docs/pm2-fork-agent-api.md`

Endpoints:
- `GET /api/v1/processes` - List PM2 processes
- `POST /api/v1/agents/sessions` - Start agent session
- `POST /api/v1/workflow/outline` - Create plan
- `GET /api/v1/health` - Health check
