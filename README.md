# fork_agent

Persistent memory, MCP server, and orchestration tools for AI coding agents.

SQLite-backed observation store with FTS5 search, 16-tool MCP server,
interactive TUI, Obsidian export/import, and git-based sync.
Python 3.11+ | MIT License

---

## Features

- **Memory Store** -- SQLite with FTS5 full-text search, short-ID prefix matching
- **MCP Server** -- 16 tools over stdio, SSE, and streamable-http
- **CLI** -- save, search, retrieve, list, get, update, delete, compact, sync, export, import, sessions, workflow, scheduling
- **TUI** -- Textual-based browser with list, search, detail, save, and stats screens
- **Obsidian** -- export/import with YAML frontmatter, dedup, path traversal protection
- **Git Sync** -- chunk-based export/import to git remote for cross-machine persistence
- **Compact** -- session summary save and context recovery after context-window resets
- **Hooks** -- event-driven shell hooks (session, subagent lifecycle, git branch guard)

---

## Quick Start

```bash
uv tool install .                                    # Install
memory save "Refactored auth middleware" --type decision  # Save
memory search "auth middleware"                       # Search
memory health                                         # Verify
```

---

## Installation

### uv tool (recommended)

```bash
uv tool install .
```

Installs `memory`, `memory-mcp`, `fork`, and `fork-api` globally.

### pip

```bash
pip install fork_agent
```

### From source

```bash
git clone https://github.com/felipe-gonzalez/tmux_fork.git
cd tmux_fork
uv sync --all-extras
uv run memory --help
```

---

## CLI Reference

### Core Memory

| Command | Description |
|---------|-------------|
| `memory save "content"` | Save an observation |
| `memory search "query"` | FTS5 full-text search |
| `memory retrieve "query"` | Enhanced multi-signal retrieval |
| `memory list` | List recent observations |
| `memory get <id>` | Get by full or short ID prefix |
| `memory delete <id>` | Delete observation |
| `memory update <id> "new content"` | Update observation |
| `memory context` | Recent session summaries |
| `memory stats` | Database statistics |
| `memory health` | Health check |

### Save options

```bash
memory save "Fixed race condition in session handler" \
  --type bugfix --project my-api \
  --topic-key "auth/session-race" --title "Fix session race condition"
```

### Search and Query

```bash
memory search "database migration" --type bugfix --limit 10
memory retrieve "how to handle concurrent writes" --project my-api
memory query --type decision --project my-api --after 2026-01-01
```

### Sessions

```bash
memory session start --project my-api --goal "Refactor auth flow"
memory session end
memory session list
```

### Compact (context-window recovery)

```bash
memory compact save-summary --session-id abc123
memory compact recover
```

### Export and Import

```bash
memory export obsidian -o ./my-vault --project my-api     # Obsidian export
memory import obsidian -i ./my-vault --skip-duplicates   # Obsidian import
memory sync export --project my-api                        # Git sync export
memory sync import                                         # Git sync import
memory sync status                                        # Sync status
```

### Project Management

```bash
memory project merge --from old-project --to canonical-project --dry-run
```

### Workflow (gated phases)

```bash
memory workflow outline "Implement user authentication"
memory workflow execute
memory workflow verify
memory workflow ship
memory workflow status
```

### Scheduling

```bash
memory schedule add "run tests" 3600
memory schedule list
memory schedule show <id>
memory schedule cancel <id>
```

### Messaging (inter-agent IPC)

Persistent message bus for coordinating multiple AI agents via SQLite.
Messages survive tmux failures and pane restarts.
Each message is stored with a type, sender, target, and timestamp.
Agents poll for new messages or use the `--watch` flag for live message delivery.

#### CLI Commands

```bash
fork message send <target> <payload> [--from-agent ID] [--type TYPE]
fork message receive <agent_id> [--limit N] [--watch] [--mark-read] [--json]
fork message broadcast <payload> [--from-agent ID]
fork message history <agent_id> [--limit N]
fork message cleanup [--max-age SECONDS]
```

#### Message Types

| Type | Purpose |
|------|---------|
| `COMMAND` | Task assignment or request from orchestrator to worker |
| `REPLY` | Response to a command, includes success/failure status |
| `HANDOFF` | Session handoff notification between agent shifts |
| `PROGRESS` | Agent reports progress or task completion |
| `FILE_TOUCHED` | Agent claims a file for editing (conflict avoidance) |
| `OBSERVATION` | Agent shares a discovery, finding, or insight |

#### Architecture

- **SQLite** is the authoritative transport (messages persist even when tmux fails)
- **tmux pane options** (`@last_fork_msg`) are a notification side-channel for real-time alerts
- **v2 protocol**: temp files with short prefix (`# F:{id8}`) to avoid tmux line limits
- **TTL**: 24h default, 5000 message hard cap per agent
- **MessageRepository Protocol** for dependency inversion and testability
- **EventCategory.MESSAGE** telemetry with Prometheus counter for message throughput

#### Workflow Integration

The messaging system integrates with the workflow engine to automatically
send progress messages during execution and verification replies on completion.

```bash
memory workflow execute --messaging    # enables PROGRESS messages to orchestrator
memory workflow verify --messaging     # sends REPLY with verification results
```

#### POC Results

- Round-trip test: 11/11 message tests pass
- Live agent test: 16 messages exchanged between 2 agents, 6 file discoveries delivered
- Latency: ~30s from send to receive (acceptable for orchestration)
- Message delivery confirmed even after tmux pane restart

---

## MCP Server

Expose memory as 16 MCP tools to any compatible client.

### Configuration

Add to your client config:

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp"
    }
  }
}
```

### Client-specific paths

| Client | Config path |
|--------|------------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Cursor | `.cursor/mcp.json` (project root) |
| n8n | MCP bridge config |

### Transports

```bash
memory-mcp                                    # stdio (default)
memory-mcp --transport sse --port 8080        # SSE
memory-mcp --transport streamable-http --port 8080  # Streamable HTTP
```

### Custom database path

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp",
      "args": ["--db", "/path/to/memory.db"]
    }
  }
}
```

### Available tools

`memory_save`, `memory_search`, `memory_get`, `memory_list`, `memory_update`,
`memory_delete`, `memory_context`, `memory_stats`, `memory_timeline`,
`memory_session_start`, `memory_session_end`, `memory_session_summary`,
`memory_suggest_topic_key`, `memory_save_prompt`, `memory_capture_passive`,
`memory_merge_projects`. See [docs/mcp-setup.md](docs/mcp-setup.md).

---

## TUI

```bash
memory tui
memory tui --db /path/to/custom.db
```

| Key | Action | Key | Action |
|-----|--------|-----|--------|
| `s` `/` | Search | `a` | Save |
| `S` | Stats | `d` | Detail |
| `q` | Quit | | |

5 screens: List, Search, Detail, Save, Stats.

---

## Architecture

DDD / Ports and Adapters with dependency injection.

```
src/
  domain/           Entities (frozen dataclasses), Protocol ports
  application/      Services, use cases, orchestration, workflow
  infrastructure/   SQLite repositories, migrations, DI container
  interfaces/
    cli/commands/   Typer CLI
    tui/screens/    Textual TUI (5 screens)
    api/            FastAPI REST
    mcp/            MCP server (16 tools, 3 transports)
```

```
CLI / TUI / MCP / API --> application/services --> domain/ports --> infrastructure/persistence
```

---

## Configuration

| Setting | Default | Override |
|---------|---------|----------|
| Database path | `~/.local/share/fork/memory.db` | `--db` flag or `FORK_MEMORY_DB` env |
| API key | None | `API_KEY` env var |

Default path follows XDG Base Directory specification (`XDG_DATA_HOME`).

---

## Development

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type-check
uv run mypy src/

# Run all checks
uv run pre-commit run --all-files
```

---

## Documentation

- [docs/mcp-setup.md](docs/mcp-setup.md) -- MCP server setup for all clients
- [docs/engram-parity-roadmap.md](docs/engram-parity-roadmap.md) -- Feature parity roadmap
- [AGENTS.md](AGENTS.md) -- Agent development guide

## License

MIT
