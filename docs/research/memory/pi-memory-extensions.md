# Pi Memory Extensions — Architecture

## Overview

Three TypeScript extensions form the memory system. They run inside Pi's agent loop via `jiti` (no compilation needed). All hooks are fire-and-forget (try/catch, never throw).

## Extension Load Order

Pi loads alphabetically:
1. `compact-memory-bridge.ts` — proactive search + compact recovery + native tools
2. `context-loader.ts` — context injection (rules, session, MEMORY_PROTOCOL)
3. `passive-capture.ts` — learning extraction from agent responses

No dependency conflicts — sections injected into system prompt don't overlap.

## Event Flow

```
Session Lifecycle:
  session_start ──► context-loader: load rules.md + session.md into cache
                  ──► compact-memory-bridge: load compact/session-summary into cache

Each Turn:
  turn_start ─────► context-loader: refresh cache if TTL expired (5min)
  before_agent_start ► context-loader: inject rules + session + MEMORY_PROTOCOL
                     ► compact-memory-bridge: inject keyword results + recovery cache

Compaction:
  session_before_compact ► compact-memory-bridge: save summary + file-ops to DB
  session_compact ──────► compact-memory-bridge: reload cache from DB

After Agent Response:
  agent_end ──────► passive-capture: extract ## Key Learnings: → save to DB

Shutdown:
  session_shutdown ► context-loader: save session snapshot to DB
```

## Native Tools (registerTool)

| Tool | Parameters | Use Case |
|------|-----------|----------|
| `memory_save` | content, type, what?, why?, where?, learned? | Agent saves observation without shell |
| `memory_search` | query, limit? (default 5) | Agent searches memory without shell |
| `memory_get` | id (UUID) | Agent retrieves full observation by ID |

## Critical Implementation Notes

### Pi Message Content is Structured
`AgentEndEvent.messages[].content` is `[{type: "text", text: "..."}]`, NOT a string.
Extensions MUST handle both formats:
```typescript
if (typeof raw === "string") { text = raw; }
else if (Array.isArray(raw)) {
  text = raw.filter(b => b.type === "text").map(b => b.text).join("\n");
}
```

### Cache Strategy
- `context-loader`: File-based cache with mtime check + 5min TTL
- `compact-memory-bridge`: In-memory cache, populated at session_start, persists across turns (no one-shot clear)

### DB Location
Default: `~/Developer/tmux_fork/data/memory.db` (45K+ observations).
Env override: `FORK_DATABASE_PATH` or `FORK_DIR`.

### Injection Budget
Max ~3750 tokens total (1.9% of 200K window). session.md capped at 100 lines.

## Commands

| Command | Extension | Description |
|---------|-----------|-------------|
| `/compact-memory` | compact-memory-bridge | status, clear, search |
| `/passive-capture` | passive-capture | status, test |
| `/context` | context-loader | status |

## Testing Extensions

```bash
# Compile check
npx esbuild ~/.pi/agent/extensions/<name>.ts --bundle --platform=node \
  --external:@mariozechner/pi-coding-agent --external:@sinclair/typebox --outfile=/dev/null

# Pi smoke test
cd ~/Developer/tmux_fork && pi -p 'reply OK'

# E2E tool test
pi -p 'use memory_save tool to save "e2e-test" with type discovery'
uv run memory search "e2e-test" -l 1
```
