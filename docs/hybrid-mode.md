# CLI→MCP Hybrid Mode

Route CLI commands through a running MCP server for lower latency and shared service access.

## Quick Start

```bash
# 1. Start the MCP server in background
memory mcp start --background

# 2. Enable hybrid mode for any command
FORK_HYBRID=1 memory save "my observation"
FORK_HYBRID=1 memory search "query" -l 10
FORK_HYBRID=1 memory list -l 5

# 3. Stop when done
memory mcp stop
```

## How It Works

Hybrid mode routes CLI commands through a local MCP server when available, falling back to direct service calls transparently.

```
┌──────────────┐     FORK_HYBRID=1      ┌──────────────┐
│  CLI Command  │ ──────────────────────→ │ MCP Server   │
│  (save/list/  │     streamable-http     │ (localhost)   │
│   search/...) │ ←────────────────────── │              │
└──────┬───────┘     result + receipt     └──────┬───────┘
       │                                          │
       │  Fallback (transparent)                  │
       │  when server unavailable                 ▼
       ▼                                   ┌──────────────┐
┌──────────────┐                           │  Service     │
│  Service     │                           │  (same as    │
│  (direct)    │                           │   direct)    │
└──────────────┘                           └──────────────┘
       │                                          │
       └──────────────┬───────────────────────────┘
                      ▼
               ┌──────────────┐
               │    SQLite     │
               │  (memory.db)  │
               └──────────────┘
```

### Dispatch Flow

1. **Guard check**: `FORK_HYBRID=1` env var must be set
2. **Server discovery**: Read `~/.local/share/fork/.mcp-server.json` for port/PID
3. **MCP call**: Send tool call via streamable-http protocol
4. **Fallback**: If server unavailable or call fails, use direct service call
5. **Receipt**: Write dispatch result to `~/.local/share/fork/.hybrid-receipts.jsonl`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FORK_HYBRID` | unset | Set to `1` to enable hybrid dispatch |
| `FORK_MCP_REQUIRE` | unset | Set to `1` to require MCP (raises RuntimeError if unavailable) |
| `FORK_MCP_DISABLED` | unset | Set to `1` to force direct path (escape hatch) |

## Supported Commands

All 18 MCP-routable commands support hybrid dispatch:

**Memory (12):** save, search, list, get, delete, update, context, retrieve, stats, timeline, session start, session end

**Messaging (5):** message send, message receive, message broadcast, message history, message cleanup

**Project (1):** project merge

## Server Lifecycle

```bash
# Start (auto-assigns port)
memory mcp start --background

# Check status
memory mcp status

# Stop (SIGTERM, then SIGKILL if needed)
memory mcp stop
```

### Port File

`~/.local/share/fork/.mcp-server.json`:

```json
{
  "pid": 12345,
  "port": 63700,
  "host": "127.0.0.1",
  "transport": "streamable-http",
  "started_at": "2026-04-23T00:00:00Z",
  "db_path": "/Users/user/.local/share/fork/memory.db"
}
```

Safety features:
- Atomic write (temp file + `os.replace`)
- Double-start guard (rejects if PID is alive)
- Stale PID cleanup (auto-removes if process dead)

## Receipts

Each dispatch writes a receipt to `~/.local/share/fork/.hybrid-receipts.jsonl`:

```json
{"mode": "mcp_client", "command": "save", "latency_ms": 152.3, "reason": null, "server_pid": 12345, "timestamp": 1776916000.0}
{"mode": "direct", "command": "list", "latency_ms": 0.8, "reason": null, "server_pid": null, "timestamp": 1776916001.0}
{"mode": "direct_fallback", "command": "search", "latency_ms": 12.1, "reason": "protocol_error", "server_pid": null, "timestamp": 1776916002.0}
```

| Mode | Meaning |
|------|---------|
| `mcp_client` | Successfully routed through MCP server |
| `direct` | Direct path used (no server or `FORK_MCP_DISABLED=1`) |
| `direct_fallback` | MCP call failed, fell back to direct |

## Strict Mode

For CI/CD or environments where MCP must be available:

```bash
export FORK_MCP_REQUIRE=1
export FORK_HYBRID=1

memory mcp start --background
memory save "CI observation"    # Works via MCP
memory mcp stop

memory save "should fail"       # RuntimeError: no server available
```

## Adding a New Dispatch Method

1. **Add dispatch method** in `src/interfaces/cli/hybrid.py`:

```python
def dispatch_mycommand(self, **kwargs: Any) -> tuple[Result, DispatchReceipt]:
    start = time.monotonic()
    client = self._get_mcp_client()
    if client is not None:
        try:
            result = client.call_tool_sync("my_mcp_tool", kwargs)
            receipt = self._mcp_receipt(start, "mycommand")
            _write_receipt(receipt)
            return result, receipt
        except Exception as e:
            self._on_mcp_error(e)
    # Fallback: direct service call
    result = self._service.my_command(**kwargs)
    receipt = self._direct_receipt(start, "mycommand", client)
    _write_receipt(receipt)
    return result, receipt
```

2. **Wire the guard** in the command file:

```python
if os.environ.get("FORK_HYBRID") == "1":
    from src.interfaces.cli.hybrid import HybridDispatcher
    dispatcher = HybridDispatcher(ctx.obj)
    result, _receipt = dispatcher.dispatch_mycommand(param=value)
    return
```

3. **Add tests** in `tests/unit/interfaces/cli/test_hybrid.py` (mcp success + fallback).

## Known Limitations

- **Session reuse**: MCP sessions are cached per-process only. Each CLI invocation creates a new session (~150ms overhead). Cross-process pooling requires shell mode (not yet available).
- **Project detection**: MCP server uses CWD basename for project auto-detection. If CLI uses git remote (`fork_agent`) but CWD differs (`tmux_fork`), results may diverge. Pass `--project` explicitly to avoid this.
- **Watch mode**: `receive_messages --watch` always uses direct path (polling not suitable for MCP).
- **asyncio.run() bridge**: CLI is synchronous, MCP SDK is async. Each MCP call wraps in `asyncio.run()`. This fails if called from within an existing event loop.
