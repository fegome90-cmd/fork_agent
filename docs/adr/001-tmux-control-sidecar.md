# ADR 001: tmux-control Sidecar API

**Date:** 2026-02-27  
**Status:** Proposed  
**Author:** Felipe Gonzalez  

## Context

The fork_agent needs a secure sidecar API for controlling tmux sessions programmatically. This API will be used by the fork_terminal skill to manage tmux sessions for AI agents.

## Requirements

1. **Security**
   - UDS (Unix Domain Socket) or localhost only - NO 0.0.0.0 binding
   - API key authentication required
   - Command allowlist (whitelist)
   - No shell=True in subprocess calls
   - Request timeouts

2. **Functionality**
   - Create/destroy tmux sessions
   - Send commands to tmux panes
   - Capture pane output
   - List active sessions

3. **Platform**
   - macOS focused (but portable)

## Architecture

```
┌─────────────────────────────────────────┐
│  fork_terminal (skill)                  │
│         │                               │
│         ▼                               │
│  tmux-control API (sidecar)            │
│  - UDS: /var/run/fork-agent/tmux.sock  │
│  - Auth: X-API-Key header               │
│         │                               │
│         ▼                               │
│  subprocess (shell=False)               │
│         │                               │
│         ▼                               │
│  tmux CLI                               │
└─────────────────────────────────────────┘
```

## Implementation

### Files

1. `src/interfaces/tmux_control/main.py` - FastAPI application
2. `docs/adr/001-tmux-control-sidecar.md` - This ADR
3. `scripts/com.fork-agent.tmux-control.plist` - macOS launchd

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /sessions | Create session |
| DELETE | /sessions/{name} | Destroy session |
| POST | /sessions/{name}/send | Send command |
| GET | /sessions/{name}/capture | Capture pane output |
| GET | /sessions | List sessions |

### Security Configuration

```python
# Allowed commands (whitelist)
ALLOWED_COMMANDS = [
    "send-keys",
    "capture-pane",
    "new-session",
    "kill-session",
    "list-sessions",
    "list-panes",
]

# Timeouts
COMMAND_TIMEOUT = 30  # seconds
```

## Alternatives Considered

1. **Direct tmux invocation** - No, requires security layer
2. **tmuxp library** - Overkill, simple CLI wrapper sufficient
3. **HTTP on localhost** - UDS is more secure

## Consequences

- ✅ Secure by default (UDS + API key)
- ✅ Minimal attack surface (command allowlist)
- ✅ Timeout protection
- ⚠️ Requires launchd/systemd for production deployment
