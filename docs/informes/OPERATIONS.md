# fork_agent - Operations Manual

> **Generated:** 2026-02-23 | **Auditor:** Sisyphus

---

## 1. CLI Commands Reference

### 1.1 Entry Point
```bash
memory <command> [options]
```

**Entry point:** `src.interfaces.cli.main:app` (pyproject.toml)

---

### 1.2 Memory Commands

| Command | Description | Example |
|---------|-------------|---------|
| `memory save <content>` | Save observation | `memory save "nota importante"` |
| `memory search <query>` | Full-text search | `memory search "auth"` |
| `memory list` | List all observations | `memory list` |
| `memory get <id>` | Get by ID | `memory get obs-123` |
| `memory delete <id>` | Delete observation | `memory delete obs-123` |

### 1.3 Workflow Commands (Gates)

```bash
# Phase 1: Outline (planning)
memory workflow outline "Implementar autenticación OAuth"
# Creates: .claude/plan-state.json, .claude/plans/plan.md

# Phase 2: Execute
memory workflow execute
# Creates: .claude/execute-state.json

# Phase 3: Verify
memory workflow verify --tests
# Creates: .claude/verify-state.json (unlock_ship=true)

# Phase 4: Ship
memory workflow ship --branch main
# Requires: verify-state.json with unlock_ship=true

# Status check
memory workflow status
```

**Gate Dependencies:**
```
outline → execute → verify → ship
  │         │         │         │
  └─────────┴─────────┴─────────┘
    Each phase requires previous state file
```

### 1.4 Schedule Commands

| Command | Description | Example |
|---------|-------------|---------|
| `memory schedule add <cmd> <interval>` | Schedule task | `memory schedule add "echo hello" 60` |
| `memory schedule list` | List scheduled | `memory schedule list` |
| `memory schedule show <id>` | Show details | `memory schedule show task-1` |
| `memory schedule cancel <id>` | Cancel task | `memory schedule cancel task-1` |

### 1.5 Workspace Commands

| Command | Description | Example |
|---------|-------------|---------|
| `memory workspace create <name>` | Create workspace | `memory workspace create myproj` |
| `memory workspace list` | List workspaces | `memory workspace list` |
| `memory workspace enter <name>` | Switch workspace | `memory workspace enter myproj` |
| `memory workspace detect` | Detect current | `memory workspace detect` |

---

## 2. Workflow Runbook

### 2.1 Standard Development Flow

```bash
# 1. Initialize session
/fork-init "Implementar feature X"

# 2. Create plan
memory workflow outline "Implementar feature X con tests"

# 3. Execute (agents work in tmux sessions)
memory workflow execute

# 4. Verify (run tests, checks)
memory workflow verify --tests

# 5. Check status before ship
memory workflow status

# 6. Ship if unlock_ship=true
memory workflow ship --branch main
```

### 2.2 Checkpoint & Resume

```bash
# Save current session handoff
/fork-checkpoint
# Creates: .claude/sessions/handoff-YYYYMMDD-HHMMSS.md

# Resume from last handoff
/fork-resume

# Prune old sessions (default: 30 days)
/fork-prune-sessions
```

### 2.3 State File Locations

| State File | Created By | Required For |
|------------|------------|--------------|
| `.claude/plan-state.json` | `workflow outline` | `execute` |
| `.claude/execute-state.json` | `workflow execute` | `verify` |
| `.claude/verify-state.json` | `workflow verify` | `ship` |

---

## 3. tmux Session Management

### 3.1 Session Naming Convention

```
fork-{agent_name}-{timestamp}
```

Example: `fork-babyclaude-1-1740321234`

### 3.2 Manual tmux Commands

```bash
# List sessions
tmux ls

# Attach to session
tmux attach -t fork-babyclaude-1-1740321234

# Send command to session
tmux send-keys -t fork-babyclaude-1-1740321234 "ls -la" Enter

# Capture output
tmux capture-pane -t fork-babyclaude-1-1740321234 -p -S -100

# Kill session
tmux kill-session -t fork-babyclaude-1-1740321234
```

### 3.3 Session Lifecycle

```
spawn_agent() → TmuxAgent.spawn()
  │
  ├─ tmux new-session -d -s fork-{name}-{ts}
  ├─ _wait_for_session(timeout=10s)
  └─ AgentStatus.HEALTHY

terminate() → TmuxAgent.terminate()
  │
  ├─ tmux kill-session -t {session}
  └─ AgentStatus.TERMINATED
```

---

## 4. Hooks Configuration

### 4.1 hooks.json Structure

**Location:** `.hooks/hooks.json`

```json
{
  "version": "1.0",
  "description": "Hooks de integración para fork_agent",
  "hooks": {
    "SessionStart": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": ".hooks/workspace-init.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": ".hooks/tmux-session-per-agent.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": ".hooks/memory-trace-writer.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash.*git.*",
        "hooks": [
          {
            "type": "command",
            "command": ".hooks/git-branch-guard.sh",
            "timeout": 1
          }
        ]
      }
    ]
  }
}
```

### 4.2 Hook Scripts

| Script | Event | Exit Codes | Purpose |
|--------|-------|------------|---------|
| `workspace-init.sh` | SessionStart | 0=success | Initialize workspace |
| `tmux-session-per-agent.sh` | SubagentStart | 0=success, 1=fail | Create tmux session |
| `memory-trace-writer.sh` | SubagentStop | 0=success | Write trace file |
| `git-branch-guard.sh` | PreToolUse | 0=allow, 2=block | Git safety |

### 4.3 Git Safety Rules

**File:** `.hooks/git-branch-guard.sh`

```
✅ ALLOWED: add, commit, status, diff, log, show, blame, branch, fetch
❌ BLOCKED: checkout, switch, reset, clean, push, pull, rebase, merge, stash, cherry-pick
```

---

## 5. Health Checks & Metrics

### 5.1 Health Check

```python
from src.infrastructure.tmux_orchestrator.health import health

response = health()
# Returns:
{
  "status": "healthy",
  "agents": {
    "babyclaude-1": "healthy",
    "oracle": "healthy"
  },
  "circuit_breakers": {
    "tmux": "closed"
  }
}
```

### 5.2 Metrics Endpoint

```python
from src.infrastructure.tmux_orchestrator.metrics import get_prometheus_metrics

metrics = get_prometheus_metrics()
print(metrics.format_prometheus())
```

**Available Metrics:**

| Metric | Type | Description |
|--------|------|-------------|
| `agent_spawn_total` | counter | Total spawn attempts |
| `agent_spawn_failures_total` | counter | Failed spawns |
| `ipc_message_latency_seconds` | gauge | Avg message latency |
| `ipc_message_failures_total` | counter | Failed messages |
| `tmux_session_count` | gauge | Active sessions |

### 5.3 Dead Letter Queue

```python
from src.infrastructure.tmux_orchestrator.dead_letter_queue import get_dead_letter_queue

dlq = get_dead_letter_queue()

# Check queue size
print(f"DLQ items: {dlq.size()}")

# Get failed items
items = dlq.get_all()
for item in items:
    print(f"Session: {item.session}, Error: {item.error}")

# Persist to disk
dlq.persist(Path(".tmux-orchestrator/dlq.json"))

# Load from disk
dlq.load(Path(".tmux-orchestrator/dlq.json"))
```

---

## 6. Resilience Configuration

### 6.1 Circuit Breaker

**Default Config:**
```python
TmuxCircuitBreaker(
    failure_threshold=3,    # Open after 3 consecutive failures
    recovery_timeout=30,    # 30 seconds before HALF_OPEN
    half_open_max_calls=2   # Allow 2 test calls in recovery
)
```

**State Machine:**
```
CLOSED ──(3 failures)──▶ OPEN
   ▲                       │
   │                       │ (30s timeout)
   │                       ▼
   └──(success)─────── HALF_OPEN
                      (max 2 calls)
```

### 6.2 Retry Configuration

**Default Config:**
```python
RetryConfig(
    max_retries=3,
    base_delay=1.0,        # 1 second initial delay
    max_delay=10.0,        # Cap at 10 seconds
    exponential_base=2.0   # 1s → 2s → 4s → 8s → 10s
)
```

### 6.3 Dead Letter Queue

**Default Config:**
```python
DeadLetterQueue(
    max_size=1000,         # Max items before drop
    persist_path=None      # Optional persistence file
)
```

---

## 7. Fork Generation

### 7.1 Usage

```bash
./scripts/fork-generate.sh <target_agent> [target_dir]

# Examples:
./scripts/fork-generate.sh .claude ../nuevo-proyecto
./scripts/fork-generate.sh .opencode ../otro-proyecto
```

### 7.2 Supported Agents

| Agent | Directory Structure |
|-------|---------------------|
| `.claude` | commands/, skills/, hooks/, sessions/, traces/ |
| `.opencode` | command/, plugin/ |
| `.kilocode` | skills/, rules/, sessions/ |
| `.gemini` | skills/ |

### 7.3 What Gets Copied

**For .claude:**
- Commands: `fork-checkpoint.md`, `fork-resume.md`, `fork-prune-sessions.md`
- Skills: `fork_terminal/`, `fork_agent_session.md`
- Hooks: `*.sh` scripts
- Config: `settings.json`, `settings.local.json`
- State files: `plan-state.json`, `execute-state.json`, `verify-state.json`
- Template: `CLAUDE.md`

---

## 8. Fork Verification (Doctor)

### 8.1 Usage

```bash
./scripts/fork-verify.sh <target_dir> [--strict]

# Examples:
./scripts/fork-verify.sh .claude              # Verify .claude directory
./scripts/fork-verify.sh .                    # Verify project root (detects .claude)
./scripts/fork-verify.sh .claude --strict      # Strict mode (warnings = fail)
```

### 8.2 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | OK (or OK with warnings in non-strict mode) |
| 1 | Warnings in strict mode |
| 2 | Invalid (errors found) |

### 8.3 Validations Performed

**Structure:**
- Required directories exist (commands/, skills/, hooks/, sessions/)

**JSON:**
- `settings.json` / `opencode.json` valid JSON
- State files valid JSON

**Hooks:**
- Referenced hook scripts exist

**Commands:**
- Required commands present (fork-checkpoint.md, fork-resume.md)

**Skills:**
- Skills directory exists and contains items

---

## 9. Troubleshooting

### 8.1 Common Issues

| Issue | Diagnosis | Resolution |
|-------|-----------|------------|
| tmux session not created | `tmux ls` shows nothing | Check tmux installed, permissions |
| Hook timeout | Script hangs | Increase timeout in hooks.json |
| Circuit breaker OPEN | Too many failures | Wait 30s or call `cb.reset()` |
| State file not found | Phase skipped | Run previous workflow phase |
| DLQ full | Max 1000 items | Process items or increase max_size |

### 8.2 Log Locations

| Log | Location |
|-----|----------|
| Application logs | stdout/stderr |
| Hook output | stderr (captured by ShellActionRunner) |
| Traces | `.claude/traces/` |
| Sessions | `.claude/sessions/` |

### 8.3 Debug Commands

```bash
# Check tmux status
tmux ls

# Verify hooks.json
cat .hooks/hooks.json | python -m json.tool

# Check state files
ls -la .claude/*.json

# View circuit breaker state
python -c "
from src.infrastructure.tmux_orchestrator.circuit_breaker import TmuxCircuitBreaker
cb = TmuxCircuitBreaker()
print(f'State: {cb.state}')
"

# View metrics
python -c "
from src.infrastructure.tmux_orchestrator.metrics import get_prometheus_metrics
print(get_prometheus_metrics().format_prometheus())
"
```

---

## 9. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_PROJECT_DIR` | `.` | Project root directory |
| `WORKTREE_PATH` | `$CLAUDE_PROJECT_DIR` | Worktree path for agents |
| `AGENT_NAME` | `unknown` | Agent identifier |
| `HOOKS_DIR` | `.hooks` | Hooks directory |

---

## 10. Quick Reference Card

```bash
# Memory
memory save "note"              # Save
memory search "query"           # Search
memory list                     # List all

# Workflow
memory workflow outline "task"  # Plan
memory workflow execute         # Execute
memory workflow verify          # Verify
memory workflow ship            # Ship
memory workflow status          # Status

# Session Continuity
/fork-checkpoint                # Save handoff
/fork-resume                    # Resume

# tmux
tmux ls                         # List sessions
tmux attach -t <session>        # Attach

# Fork generation
./scripts/fork-generate.sh .claude ../new-project
```

---

*Document generated by operations audit - 2026-02-23*
