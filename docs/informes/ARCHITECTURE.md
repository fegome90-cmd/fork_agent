# fork_agent - Architecture Reference

> **Generated:** 2026-02-23 | **Commit:** current | **Auditor:** Sisyphus

---

## 1. System Overview

**fork_agent** is an agentic orchestration platform that coordinates multiple AI agents via tmux, with persistent memory, event-driven hooks, and disciplined workflow gates.

### Core Capabilities

| Capability | Implementation | Location |
|------------|----------------|----------|
| Agent Orchestration | TmuxOrchestrator + AgentManager | `src/infrastructure/tmux_orchestrator/` |
| Memory Persistence | SQLite + WAL | `src/infrastructure/persistence/` |
| Event Hooks | RuleLoader + ShellActionRunner | `src/infrastructure/orchestration/` |
| Workflow Gates | State machines | `src/application/services/workflow/` |
| Resilience | CircuitBreaker + Retry + DLQ | `src/infrastructure/tmux_orchestrator/` |

---

## 2. Layer Architecture (DDD)

```
┌─────────────────────────────────────────────────────────────────┐
│                      INTERFACES LAYER                           │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │ CLI (Typer)         │  │ REST API (FastAPI)              │  │
│  │ src/interfaces/cli/ │  │ src/interfaces/api/             │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                           │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐  │
│  │ MemoryService│ │ HookService  │ │ AgentManager           │  │
│  │ SchedulerSvc │ │ WorkflowState│ │ IPCBridge              │  │
│  └──────────────┘ └──────────────┘ └────────────────────────┘  │
│                                                                 │
│  Use Cases: save_observation, search, fork_terminal, etc.      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DOMAIN LAYER                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐  │
│  │ Observation     │ │ Message         │ │ Rule             │  │
│  │ ScheduledTask   │ │ Terminal        │ │ Task             │  │
│  └─────────────────┘ └─────────────────┘ └──────────────────┘  │
│                                                                 │
│  Ports (Protocols): IObservationRepository, IEventDispatcher   │
│  Exceptions: ObservationNotFoundError, RepositoryError         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ tmux_orchestrator/                                       │   │
│  │ - TmuxOrchestrator (session mgmt)                       │   │
│  │ - TmuxCircuitBreaker (failure_threshold=3, recovery=30s)│   │
│  │ - ExponentialBackoff (base=1s, max=10s)                 │   │
│  │ - DeadLetterQueue (max_size=1000)                       │   │
│  │ - PrometheusMetrics (spawn, latency, failures)          │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ persistence/                                             │   │
│  │ - DatabaseConnection (SQLite + WAL, thread-local)       │   │
│  │ - ObservationRepository (CRUD + FTS5 search)            │   │
│  │ - ScheduledTaskRepository                                │   │
│  │ - MessageStore (inter-agent communication)              │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ orchestration/                                           │   │
│  │ - RuleLoader (hooks.json → list[Rule])                  │   │
│  │ - ShellActionRunner (subprocess + env sanitization)     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Components

### 3.1 TmuxOrchestrator
**File:** `src/infrastructure/tmux_orchestrator/__init__.py` (L37-240)

```python
class TmuxOrchestrator:
    """Orchestrates multiple OpenCode agent sessions via tmux."""
    
    # Key methods:
    get_sessions() -> list[TmuxSession]      # List active sessions
    capture_content(session, window, lines)  # Read output
    send_message(session, window, message)   # Send command
    create_session(name, working_dir)        # Spawn agent
    kill_session(session)                    # Terminate
```

### 3.2 CircuitBreaker
**File:** `src/infrastructure/tmux_orchestrator/circuit_breaker.py` (L18-80)

```python
class TmuxCircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,    # Opens after 3 failures
        recovery_timeout: int = 30,    # 30s before HALF_OPEN
        half_open_max_calls: int = 2,  # Allow 2 test calls in HALF_OPEN
    )
```

**States:** CLOSED → OPEN → HALF_OPEN → CLOSED

### 3.3 Retry with Backoff
**File:** `src/infrastructure/tmux_orchestrator/retry.py` (L49-127)

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0

# Delay sequence: 1s → 2s → 4s → 8s → 10s (capped)
```

### 3.4 DeadLetterQueue
**File:** `src/infrastructure/tmux_orchestrator/dead_letter_queue.py` (L26-148)

```python
class DeadLetterQueue:
    def __init__(self, max_size: int = 1000, persist_path: Path | None = None)
    
    def add(session, window, message, error, attempts)  # Enqueue failed message
    def get(timeout=1.0) -> DeadLetterItem | None       # Dequeue
    def persist(path)                                    # Save to JSON
    def load(path) -> int                                # Load from JSON
    def requeue(item)                                    # Retry later
```

### 3.5 DatabaseConnection
**File:** `src/infrastructure/persistence/database.py` (L61-170)

```python
class DatabaseConnection:
    """Thread-safe SQLite using thread-local storage."""
    
    # PRAGMA settings:
    PRAGMA journal_mode=WAL        # Write-Ahead Logging
    PRAGMA busy_timeout=5000       # 5s wait on lock
    PRAGMA foreign_keys=ON         # Enforce FK constraints
    
    # Connection model: thread-local caching for file-backed, 
    # new connection per context for :memory:
```

---

## 4. Database Schemas

### 4.1 observations table
**File:** Migrations (not found as .sql files, schema in code)

```sql
CREATE TABLE observations (
    id TEXT PRIMARY KEY,           -- UUID
    timestamp INTEGER NOT NULL,    -- Unix ms
    content TEXT NOT NULL,
    metadata TEXT                   -- JSON
);

-- FTS5 virtual table for search
CREATE VIRTUAL TABLE observations_fts USING fts5(
    content,
    content='observations',
    content_rowid='rowid'
);
```

### 4.2 messages table (inter-agent)
**File:** `src/infrastructure/persistence/message_store.py` (L46-66)

```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    message_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    correlation_id TEXT,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_messages_to_agent ON messages(to_agent, created_at DESC);
CREATE INDEX idx_messages_from_agent ON messages(from_agent, created_at DESC);
CREATE INDEX idx_messages_correlation ON messages(correlation_id);
CREATE INDEX idx_messages_expires_at ON messages(expires_at);
```

### 4.3 scheduled_tasks table
**Location:** Referenced in `test_scheduled_task_repository.py`

---

## 5. Workflow State Machines

### 5.1 Phases
**File:** `src/application/services/workflow/state.py` (L12-21)

```python
class WorkflowPhase(str, Enum):
    PLANNING = "planning"
    OUTLINED = "outlined"
    EXECUTING = "executing"
    EXECUTED = "executed"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    SHIPPING = "shipping"
    SHIPPED = "shipped"
```

### 5.2 State Files

| File | Dataclass | Key Fields |
|------|-----------|------------|
| `.claude/plan-state.json` | PlanState | session_id, phase, tasks[], plan_file |
| `.claude/execute-state.json` | ExecuteState | session_id, phase, tasks[], current_task_index |
| `.claude/verify-state.json` | VerifyState | session_id, phase, unlock_ship, test_results, evidence |

### 5.3 Gate Logic
**File:** `src/interfaces/cli/commands/workflow.py`

```python
# outline: No prerequisites
# execute: Requires plan-state.json exists (L87-88)
# verify: Requires plan-state.json + execute-state.json (L111-112)
# ship: Requires verify-state.json with unlock_ship=True (L133-138)
```

---

## 6. Hooks System

### 6.1 Configuration
**File:** `.hooks/hooks.json`

```json
{
  "version": "1.0",
  "hooks": {
    "SessionStart": [{"matcher": ".*", "hooks": [...]}],
    "SubagentStart": [{"matcher": ".*", "hooks": [...]}],
    "SubagentStop": [{"matcher": ".*", "hooks": [...]}],
    "PreToolUse": [{"matcher": "Bash.*git.*", "hooks": [...]}]
  }
}
```

### 6.2 Event Flow
```
Event → RuleLoader.load() → list[Rule] → EventDispatcher.dispatch()
     → RegexMatcherSpec.matches(event) → ShellActionRunner.run(action)
```

### 6.3 Security
**File:** `src/infrastructure/orchestration/shell_action_runner.py` (L12-46)

```python
DANGEROUS_ENV_VARS = {
    "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT", "LD_DEBUG",
    "BASH_ENV", "ENV", "CDPATH", "GLOBIGNORE", "BASH_FUNC_*",
    "IFS", "MAIL", "MAILPATH", "OPTIND", "PS1", "PS2", "FIGNORE"
}

SAFE_DEFAULT_ENV_VARS = {
    "HOME", "USER", "LOGNAME", "PATH", "SHELL", "TERM",
    "LANG", "LC_ALL", "PWD", "SHLVL"
}
```

---

## 7. Metrics

### 7.1 Prometheus Metrics
**File:** `src/infrastructure/tmux_orchestrator/metrics.py` (L53-85)

```prometheus
# TYPE agent_spawn_total counter
agent_spawn_total 42

# TYPE agent_spawn_failures_total counter
agent_spawn_failures_total 3

# TYPE ipc_message_latency_seconds gauge
ipc_message_latency_seconds 0.045

# TYPE ipc_message_failures_total counter
ipc_message_failures_total 1

# TYPE tmux_session_count gauge
tmux_session_count 4
```

---

## 8. Integration Map

```
┌──────────────────────────────────────────────────────────────┐
│                      User / CLI                              │
│                         │                                    │
│  memory save/search/list/workflow                            │
│                         ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    HookService                          ││
│  │  SessionStart → workspace-init.sh                      ││
│  │  SubagentStart → tmux-session-per-agent.sh             ││
│  │  SubagentStop → memory-trace-writer.sh                 ││
│  │  PreToolUse → git-branch-guard.sh                      ││
│  └─────────────────────────────────────────────────────────┘│
│                         │                                    │
│                         ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                  AgentManager                           ││
│  │  spawn_agent() → TmuxAgent.spawn()                     ││
│  │  send_input() → tmux send-keys                         ││
│  │  CircuitBreaker protects all operations                ││
│  └─────────────────────────────────────────────────────────┘│
│                         │                                    │
│                         ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                  Persistence Layer                      ││
│  │  DatabaseConnection (SQLite + WAL)                     ││
│  │  ObservationRepository (CRUD + FTS)                    ││
│  │  MessageStore (inter-agent)                            ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

---

## 9. File Reference

| Component | Path | Lines |
|-----------|------|-------|
| TmuxOrchestrator | `src/infrastructure/tmux_orchestrator/__init__.py` | 240 |
| CircuitBreaker | `src/infrastructure/tmux_orchestrator/circuit_breaker.py` | 80 |
| Retry/Backoff | `src/infrastructure/tmux_orchestrator/retry.py` | 127 |
| DeadLetterQueue | `src/infrastructure/tmux_orchestrator/dead_letter_queue.py` | 148 |
| Metrics | `src/infrastructure/tmux_orchestrator/metrics.py` | 97 |
| DatabaseConnection | `src/infrastructure/persistence/database.py` | 170 |
| ObservationRepository | `src/infrastructure/persistence/repositories/observation_repository.py` | 248 |
| MessageStore | `src/infrastructure/persistence/message_store.py` | 226 |
| WorkflowState | `src/application/services/workflow/state.py` | 223 |
| WorkflowCommands | `src/interfaces/cli/commands/workflow.py` | 165 |
| HookService | `src/application/services/orchestration/hook_service.py` | 38 |
| RuleLoader | `src/infrastructure/orchestration/rule_loader.py` | 57 |
| ShellActionRunner | `src/infrastructure/orchestration/shell_action_runner.py` | 127 |
| AgentManager | `src/application/services/agent/agent_manager.py` | 380 |

---

*Document generated by architecture audit - 2026-02-23*
