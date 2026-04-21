# MCP Server Setup Guide

Memory server for AI agent integrations via the Model Context Protocol (MCP).

**Protocol:** MCP 2024-11-05 | **Transport:** stdio | **Wire:** JSON-RPC 2.0
**Server:** memory-server

---

## Installation

### pip (recommended)

```bash
pip install fork_agent
```

### uvx (one-off, no global install)

```bash
uvx fork_agent
```

### uv tool (global install)

```bash
uv tool install fork_agent
```

### From source (development)

```bash
git clone https://github.com/felipe-gonzalez/tmux_fork.git
cd tmux_fork
uv sync --all-extras
```

### Verify

```bash
memory --version
memory-mcp --help
```

After installation, `memory`, `memory-mcp`, `fork`, and `fork-api` are available globally.

No build step required.

---

## Quick Start

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp"
    }
  }
}
```

---

## Client Configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp"
    }
  }
}
```

Restart Claude Desktop after editing.

### Cursor

Create or edit `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp"
    }
  }
}
```

### n8n MCP Bridge

In your n8n MCP bridge configuration:

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp"
    }
  }
}
```

### Generic MCP Client

Any MCP-compatible client that supports stdio transport:

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp"
    }
  }
}
```

---

## Custom Database Path

The default database is stored at an XDG-compliant location:
- Linux: `~/.local/share/fork/memory.db`
- macOS: `~/.local/share/fork/memory.db` (respects `XDG_DATA_HOME`)

Override with `--db` / `-d` flag or the `FORK_MEMORY_DB` environment variable:

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp",
      "args": ["--db", "/path/to/custom.db"]
    }
  }
}
```

Or via environment variable:

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp",
      "env": {
        "FORK_MEMORY_DB": "/path/to/custom.db"
      }
    }
  }
}
```

---

## Available Tools (21)

| Tool | Description |
|------|-------------|
| `memory_save` | Save observation (content, type, project, topic_key, metadata, title) |
| `memory_search` | FTS5 full-text search with prefix matching |
| `memory_get` | Get by ID (supports short ID prefix) |
| `memory_list` | List with pagination and type filter |
| `memory_update` | Update existing observation |
| `memory_delete` | Delete observation |
| `memory_context` | Recent session summaries for context recovery |
| `memory_stats` | Database statistics |
| `memory_timeline` | Observations in time range |
| `memory_session_start` | Start session (project, directory, goal) |
| `memory_session_end` | End active session |
| `memory_session_summary` | Save structured session summary |
| `memory_suggest_topic_key` | Suggest stable topic_key from title/type |
| `memory_save_prompt` | Save user prompt for intent tracking |
| `memory_capture_passive` | Extract learnings from text output |
| `memory_merge_projects` | Consolidate projects |

---

## Verifying Installation

Test that the server responds to MCP initialization:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | memory-mcp 2>/dev/null
```

Expected output: a JSON-RPC response with `serverInfo.name: "memory-server"`.

Verify the CLI entry point:

```bash
memory-mcp --help
```

---

## SSE / Streamable HTTP (for remote access)

For n8n or other remote clients that cannot use stdio:

```bash
# SSE transport
memory-mcp --transport sse --port 8080

# Streamable HTTP (recommended by MCP spec)
memory-mcp --transport streamable-http --port 8080
```

n8n config for SSE:
```json
{
  "mcpServers": {
    "memory": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

n8n config for Streamable HTTP:
```json
{
  "mcpServers": {
    "memory": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

---

## Direct Entry Point

The `memory-mcp` console script is the recommended entry point:

```bash
# Default database (XDG-compliant)
memory-mcp

# Custom database
memory-mcp --db /path/to/custom.db
```

### Legacy `uv run` (development only)

For development without global install:

```json
{
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/tmux_fork", "memory", "mcp", "serve"]
    }
  }
}
```
