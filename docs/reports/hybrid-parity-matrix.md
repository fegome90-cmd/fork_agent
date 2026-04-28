# Hybrid Parity Matrix

> RC-3 audit: command → direct path → MCP path → fallback → receipt

## Environment Variables

| Variable              | Purpose                                                    |
| --------------------- | ---------------------------------------------------------- |
| `FORK_HYBRID=1`       | Enable hybrid dispatch for CLI commands                    |
| `FORK_MCP_DISABLED=1` | Force direct mode even when hybrid is enabled              |
| `FORK_MCP_REQUIRE=1`  | Fail if MCP server unavailable or call fails (no fallback) |

## Dispatch Flow

```text
CLI command
  ├─ FORK_HYBRID=1? → HybridDispatcher.dispatch_X()
  │    ├─ discover MCP server → found?
  │    │    ├─ yes → MCP call → success? → return (mode=mcp)
  │    │    │                     └─ fail → FORK_MCP_REQUIRE=1? → raise
  │    │    │                               └─ default → fallback (mode=direct_fallback)
  │    │    └─ no → FORK_MCP_REQUIRE=1? → raise
  │    │              └─ default → direct service (mode=direct)
  │    └─ receipt written to ~/.local/share/fork/.hybrid-receipts.jsonl
  └─ default → direct service call (no hybrid)
```text

## Command Matrix

| Command             | CLI File      | Dispatch Method              | MCP Tool                 | Direct Path                              | Receipt Mode                   |
| ------------------- | ------------- | ---------------------------- | ------------------------ | ---------------------------------------- | ------------------------------ |
| `memory save`       | `save.py`     | `dispatch_save`              | `memory_save`            | `memory_service.save()`                  | mcp / direct / direct_fallback |
| `memory search`     | `search.py`   | `dispatch_search`            | `memory_search`          | `memory_service.search()`                | mcp / direct / direct_fallback |
| `memory get`        | `get.py`      | `dispatch_get`               | `memory_get`             | `memory_service.get_by_id()`             | mcp / direct / direct_fallback |
| `memory list`       | `list.py`     | `dispatch_list`              | `memory_list`            | `memory_service.get_recent()`            | mcp / direct / direct_fallback |
| `memory delete`     | `delete.py`   | `dispatch_delete`            | `memory_delete`          | `memory_service.delete()`                | mcp / direct / direct_fallback |
| `memory update`     | `update.py`   | `dispatch_update`            | `memory_update`          | `memory_service.update()`                | mcp / direct / direct_fallback |
| `memory context`    | `context.py`  | `dispatch_context`           | `memory_context`         | `memory_service.get_recent()`            | mcp / direct / direct_fallback |
| `memory retrieve`   | `retrieve.py` | `dispatch_retrieve`          | `memory_retrieve`        | `EnhancedRetrievalSearchService`         | mcp / direct / direct_fallback |
| `memory stats`      | `stats.py`    | `dispatch_stats`             | `memory_stats`           | `get_health_check_service()`             | mcp / direct / direct_fallback |
| `memory merge`      | `project.py`  | `dispatch_project_merge`     | `memory_merge_projects`  | `memory_service.merge_projects()`        | mcp / direct / direct_fallback |
| `session start`     | `session.py`  | `dispatch_session_start`     | `memory_session_start`   | `get_session_service().start_session()`  | mcp / direct / direct_fallback |
| `session end`       | `session.py`  | `dispatch_session_end`       | `memory_session_end`     | `get_session_service().end_session()`    | mcp / direct / direct_fallback |
| `message send`      | `message.py`  | `dispatch_message_send`      | `fork_message_send`      | `AgentMessenger.send()`                  | mcp / direct / direct_fallback |
| `message receive`   | `message.py`  | `dispatch_message_receive`   | `fork_message_receive`   | `AgentMessenger.get_messages()`          | mcp / direct / direct_fallback |
| `message broadcast` | `message.py`  | `dispatch_message_broadcast` | `fork_message_broadcast` | `AgentMessenger.broadcast()`             | mcp / direct / direct_fallback |
| `message history`   | `message.py`  | `dispatch_message_history`   | `fork_message_history`   | `AgentMessenger.get_history()`           | mcp / direct / direct_fallback |
| `message cleanup`   | `message.py`  | `dispatch_message_cleanup`   | `fork_message_cleanup`   | `AgentMessenger.store.cleanup_expired()` | mcp / direct / direct_fallback |

## MCP-Only Tools (no CLI hybrid dispatch)

| MCP Tool                   | Purpose                                    |
| -------------------------- | ------------------------------------------ |
| `memory_session_summary`   | Session summaries — MCP consumers only     |
| `memory_suggest_topic_key` | Topic key suggestions — MCP consumers only |
| `memory_save_prompt`       | Prompt saving — MCP consumers only         |
| `memory_capture_passive`   | Passive capture — MCP consumers only       |

## Receipt Format

```json
{"mode":"mcp_client","command":"save","latency_ms":28,"reason":null,"server_pid":12345,"timestamp":1714250400.0}
{"mode":"direct","command":"save","latency_ms":5,"reason":"no_server","server_pid":null,"timestamp":1714250401.0}
{"mode":"direct_fallback","command":"save","latency_ms":35,"reason":"protocol_error","server_pid":12345,"timestamp":1714250402.0}
```text

## Known Gaps

1. **No integration tests**: All hybrid tests use mocked MCP server. No real HTTP round-trip.
2. **`dispatch_timeline`**: Defined in HybridDispatcher but no CLI command calls it.
3. **Receipt growth**: `~/.local/share/fork/.hybrid-receipts.jsonl` grows unbounded — no rotation.
4. **MCP-only tools**: 4 tools have no CLI counterpart — by design, not a gap.
