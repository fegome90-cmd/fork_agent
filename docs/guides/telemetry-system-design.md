# Telemetry System Design - fork_agent

> **Author:** Data Science Engineering Team
> **Version:** 1.0.0
> **Date:** 2026-02-25
> **Status:** Design Phase

---

## 1. Executive Summary

Este documento define la arquitectura completa del sistema de telemetría para `fork_agent`. El objetivo es proporcionar visibilidad total sobre:

- **Uso del sistema**: Quién, cuándo, cómo
- **Performance**: Latencia, throughput, errores
- **Comportamiento de agentes**: Ciclo de vida, éxito/fallo
- **Workflow adoption**: Adopción del workflow disciplinado
- **Hook effectiveness**: Efectividad de los hooks de integración

---

## 2. Telemetry Architecture Overview

### 2.1 Design Principles

| Principio | Descripción |
|-----------|-------------|
| **Privacy-First** | No PII, solo métricas anónimas |
| **Low Overhead** | <5ms latencia adicional por evento |
| **Event Sourcing** | Append-only, immutable events |
| **Queryable** | SQL para análisis ad-hoc |
| **Exportable** | Prometheus, JSON, CSV |

### 2.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     TELEMETRY LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Events     │  │   Metrics    │  │   Traces     │          │
│  │  (Counts)    │  │  (Gauges)    │  │ (Distributed)│          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           ▼                                     │
│              ┌────────────────────────┐                        │
│              │   TelemetryService     │                        │
│              │   (Application Layer)  │                        │
│              └────────────┬───────────┘                        │
│                           │                                     │
│              ┌────────────┴───────────┐                        │
│              ▼                        ▼                        │
│    ┌──────────────────┐    ┌──────────────────┐               │
│    │  SQLite Storage  │    │  Prometheus      │               │
│    │  (Local)         │    │  Export (Opt)    │               │
│    └──────────────────┘    └──────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                           ▲
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                     EVENT SOURCES                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │    Hooks    │ │   Memory    │ │   Workflow  │ │   Tmux    │ │
│  │  (4 tipos)  │ │   (CRUD)    │ │  (4 fases)  │ │ (Sessions)│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │   Agents    │ │    CLI      │ │   Traces    │ │   Errors  │ │
│  │  (Spawns)   │ │ (Commands)  │ │  (Spans)    │ │  (System) │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Event Taxonomy

### 3.1 Event Categories

| Categoría | Prefijo | Ejemplos |
|-----------|---------|----------|
| **Session** | `session.` | session.start, session.end |
| **Hook** | `hook.` | hook.fire, hook.success, hook.fail |
| **Agent** | `agent.` | agent.spawn, agent.stop, agent.health |
| **Tmux** | `tmux.` | tmux.session.create, tmux.session.kill |
| **Memory** | `memory.` | memory.save, memory.search, memory.delete |
| **Workflow** | `workflow.` | workflow.outline, workflow.execute, workflow.verify, workflow.ship |
| **CLI** | `cli.` | cli.command, cli.error |
| **Trace** | `trace.` | trace.span.start, trace.span.end |

### 3.2 Complete Event Catalog

#### 3.2.1 Session Events

```yaml
session.start:
  description: "Nueva sesión de fork_agent iniciada"
  attributes:
    - session_id: string (required)
    - workspace_id: string
    - fork_agent_version: string
    - python_version: string
    - platform: string (darwin/linux/windows)
  metrics:
    - counter: session_start_total
  retention: 90 days

session.end:
  description: "Sesión terminada"
  attributes:
    - session_id: string (required)
    - duration_ms: integer
    - reason: string (normal/error/timeout)
  metrics:
    - counter: session_end_total
    - histogram: session_duration_ms
  retention: 90 days
```

#### 3.2.2 Hook Events

```yaml
hook.fire:
  description: "Hook disparado por evento"
  attributes:
    - hook_name: string (required)
    - event_type: string (SessionStart/SubagentStart/SubagentStop/PreToolUse)
    - matcher: string
    - timeout_ms: integer
    - critical: boolean
  metrics:
    - counter: hook_fire_total{event_type, hook_name}
  retention: 30 days

hook.success:
  description: "Hook ejecutado exitosamente"
  attributes:
    - hook_name: string
    - event_type: string
    - duration_ms: integer
    - output_preview: string (truncated to 100 chars)
  metrics:
    - counter: hook_success_total{event_type, hook_name}
    - histogram: hook_duration_ms{event_type, hook_name}
  retention: 30 days

hook.fail:
  description: "Hook falló"
  attributes:
    - hook_name: string
    - event_type: string
    - error_type: string
    - error_message: string (truncated)
    - duration_ms: integer
    - on_failure_policy: string (abort/continue)
  metrics:
    - counter: hook_fail_total{event_type, hook_name, error_type}
  retention: 90 days
```

#### 3.2.3 Agent Events

```yaml
agent.spawn:
  description: "Agente spawnado en tmux"
  attributes:
    - agent_id: string (required)
    - agent_name: string
    - session_name: string (tmux session)
    - tmux_session_id: string
    - working_dir: string
    - parent_session_id: string
  metrics:
    - counter: agent_spawn_total
    - gauge: active_agents
  retention: 30 days

agent.stop:
  description: "Agente terminado"
  attributes:
    - agent_id: string
    - agent_name: string
    - duration_ms: integer
    - status: string (completed/failed/killed)
    - exit_code: integer
    - tasks_completed: integer
  metrics:
    - counter: agent_stop_total{status}
    - histogram: agent_duration_ms
  retention: 30 days

agent.health_check:
  description: "Health check de agente"
  attributes:
    - agent_id: string
    - status: string (healthy/unhealthy/unknown)
    - pid: integer
    - last_heartbeat_ms: integer
  metrics:
    - gauge: agent_health_status{agent_id}
  retention: 7 days
```

#### 3.2.4 Tmux Events

```yaml
tmux.session.create:
  description: "Sesión tmux creada"
  attributes:
    - session_name: string (required)
    - session_type: string (agent/fork/terminal)
    - window_count: integer
    - created_by: string (hook/manual/cli)
  metrics:
    - counter: tmux_session_create_total{session_type}
    - gauge: tmux_session_count
  retention: 30 days

tmux.session.kill:
  description: "Sesión tmux terminada"
  attributes:
    - session_name: string
    - session_type: string
    - duration_ms: integer
    - reason: string (normal/force/cleanup)
  metrics:
    - counter: tmux_session_kill_total{session_type, reason}
  retention: 30 days

tmux.session.list:
  description: "Listado de sesiones tmux"
  attributes:
    - total_sessions: integer
    - agent_sessions: integer
    - fork_sessions: integer
    - other_sessions: integer
  metrics:
    - gauge: tmux_sessions_total
    - gauge: tmux_agent_sessions
    - gauge: tmux_fork_sessions
  retention: 7 days
```

#### 3.2.5 Memory Events

```yaml
memory.save:
  description: "Observación guardada en memoria"
  attributes:
    - observation_id: string
    - content_length: integer
    - has_metadata: boolean
    - session_id: string
  metrics:
    - counter: memory_save_total
    - histogram: memory_content_length
  retention: 30 days

memory.search:
  description: "Búsqueda en memoria"
  attributes:
    - query_length: integer
    - limit: integer
    - results_count: integer
    - duration_ms: integer
    - used_fts: boolean
  metrics:
    - counter: memory_search_total
    - histogram: memory_search_results_count
    - histogram: memory_search_duration_ms
  retention: 30 days

memory.list:
  description: "Listado de observaciones"
  attributes:
    - count: integer
    - limit_used: integer
  metrics:
    - counter: memory_list_total
    - gauge: memory_observations_count
  retention: 7 days

memory.delete:
  description: "Observación eliminada"
  attributes:
    - observation_id: string
    - session_id: string
  metrics:
    - counter: memory_delete_total
  retention: 30 days
```

#### 3.2.6 Workflow Events

```yaml
workflow.outline:
  description: "Plan creado"
  attributes:
    - plan_id: string
    - session_id: string
    - task_count: integer
    - description_length: integer
  metrics:
    - counter: workflow_outline_total
    - histogram: workflow_task_count
  retention: 90 days

workflow.execute:
  description: "Ejecución iniciada"
  attributes:
    - plan_id: string
    - execute_id: string
    - session_id: string
    - task_count: integer
  metrics:
    - counter: workflow_execute_total
  retention: 90 days

workflow.verify:
  description: "Verificación completada"
  attributes:
    - verify_id: string
    - session_id: string
    - tests_passed: integer
    - tests_failed: integer
    - unlock_ship: boolean
    - evidence_count: integer
  metrics:
    - counter: workflow_verify_total{result=pass/fail}
    - gauge: workflow_tests_pass_rate
  retention: 90 days

workflow.ship:
  description: "Shipping completado"
  attributes:
    - session_id: string
    - target_branch: string
    - files_changed: integer
    - duration_total_ms: integer
  metrics:
    - counter: workflow_ship_total
    - histogram: workflow_total_duration_ms
  retention: 90 days

workflow.abort:
  description: "Workflow abortado"
  attributes:
    - session_id: string
    - phase: string (outline/execute/verify/ship)
    - reason: string
  metrics:
    - counter: workflow_abort_total{phase, reason}
  retention: 90 days
```

#### 3.2.7 CLI Events

```yaml
cli.command:
  description: "Comando CLI ejecutado"
  attributes:
    - command_name: string (save/search/list/get/delete/workflow/schedule)
    - subcommand: string (outline/execute/verify/ship)
    - args_count: integer
    - duration_ms: integer
    - exit_code: integer
  metrics:
    - counter: cli_command_total{command, subcommand}
    - histogram: cli_command_duration_ms{command}
  retention: 30 days

cli.error:
  description: "Error en CLI"
  attributes:
    - command_name: string
    - error_type: string
    - error_message: string (truncated)
    - stack_trace_hash: string (for grouping)
  metrics:
    - counter: cli_error_total{command, error_type}
  retention: 90 days
```

#### 3.2.8 Trace Events

```yaml
trace.span.start:
  description: "Span de trace iniciado"
  attributes:
    - trace_id: string
    - span_id: string
    - parent_span_id: string
    - operation_name: string
    - session_id: string
  metrics:
    - counter: trace_span_total
  retention: 30 days

trace.span.end:
  description: "Span de trace terminado"
  attributes:
    - trace_id: string
    - span_id: string
    - duration_ms: integer
    - status: string (ok/error)
    - tags: json (key-value pairs)
  metrics:
    - counter: trace_span_end_total{status}
    - histogram: trace_span_duration_ms
  retention: 30 days
```

---

## 4. Database Schema

### 4.1 telemetry_events Table

```sql
-- Migration 003: Create telemetry_events table
CREATE TABLE telemetry_events (
    -- Primary key
    id TEXT PRIMARY KEY,
    
    -- Event identification
    event_type TEXT NOT NULL,          -- e.g., "hook.fire", "agent.spawn"
    event_category TEXT NOT NULL,       -- session/hook/agent/tmux/memory/workflow/cli/trace
    
    -- Temporal data
    timestamp INTEGER NOT NULL,         -- Unix timestamp (ms)
    received_at INTEGER NOT NULL,       -- When we received it (ms)
    
    -- Context
    session_id TEXT,                    -- fork_agent session
    correlation_id TEXT,                -- For linking related events
    parent_event_id TEXT,               -- For event hierarchies
    
    -- Event data (JSON)
    attributes TEXT NOT NULL,           -- JSON object with event-specific data
    metrics TEXT,                       -- JSON object with metric values
    
    -- Processing metadata
    processed INTEGER DEFAULT 0,        -- 0=pending, 1=processed
    processed_at INTEGER,
    
    -- Retention
    expires_at INTEGER NOT NULL         -- Unix timestamp for TTL
);

-- Indexes for common queries
CREATE INDEX idx_telemetry_events_type ON telemetry_events(event_type);
CREATE INDEX idx_telemetry_events_category ON telemetry_events(event_category);
CREATE INDEX idx_telemetry_events_session ON telemetry_events(session_id);
CREATE INDEX idx_telemetry_events_timestamp ON telemetry_events(timestamp);
CREATE INDEX idx_telemetry_events_expires ON telemetry_events(expires_at);
CREATE INDEX idx_telemetry_events_correlation ON telemetry_events(correlation_id);

-- Composite indexes for analytics
CREATE INDEX idx_telemetry_events_type_timestamp ON telemetry_events(event_type, timestamp);
CREATE INDEX idx_telemetry_events_session_type ON telemetry_events(session_id, event_type);
```

### 4.2 telemetry_metrics Table (Pre-aggregated)

```sql
-- Migration 004: Create telemetry_metrics table (for fast queries)
CREATE TABLE telemetry_metrics (
    id TEXT PRIMARY KEY,
    
    -- Metric identification
    metric_name TEXT NOT NULL,          -- e.g., "hook.fire.count"
    metric_type TEXT NOT NULL,          -- counter/gauge/histogram
    
    -- Labels (for Prometheus-style metrics)
    labels TEXT,                        -- JSON object: {"hook_name": "workspace-init", "event_type": "SessionStart"}
    labels_hash TEXT,                   -- Hash of labels for deduplication
    
    -- Time bucket (for time-series)
    bucket_start INTEGER NOT NULL,      -- Start of time bucket (Unix timestamp)
    bucket_duration INTEGER NOT NULL,   -- Duration of bucket in seconds (60, 3600, 86400)
    
    -- Values
    value_count INTEGER DEFAULT 0,      -- Number of observations
    value_sum REAL DEFAULT 0,           -- Sum of values (for histograms)
    value_min REAL,                     -- Min value
    value_max REAL,                     -- Max value
    value_last REAL,                    -- Last value (for gauges)
    
    -- Metadata
    updated_at INTEGER NOT NULL
);

-- Indexes
CREATE INDEX idx_telemetry_metrics_name ON telemetry_metrics(metric_name);
CREATE INDEX idx_telemetry_metrics_bucket ON telemetry_metrics(bucket_start);
CREATE INDEX idx_telemetry_metrics_name_bucket ON telemetry_metrics(metric_name, bucket_start);
CREATE UNIQUE INDEX idx_telemetry_metrics_unique ON telemetry_metrics(
    metric_name, labels_hash, bucket_start, bucket_duration
);
```

### 4.3 telemetry_sessions Table (Session Summary)

```sql
-- Migration 005: Create telemetry_sessions table
CREATE TABLE telemetry_sessions (
    session_id TEXT PRIMARY KEY,
    
    -- Session metadata
    workspace_id TEXT,
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    duration_ms INTEGER,
    
    -- Aggregated metrics
    hooks_fired INTEGER DEFAULT 0,
    hooks_succeeded INTEGER DEFAULT 0,
    hooks_failed INTEGER DEFAULT 0,
    
    agents_spawned INTEGER DEFAULT 0,
    agents_completed INTEGER DEFAULT 0,
    agents_failed INTEGER DEFAULT 0,
    
    tmux_sessions_created INTEGER DEFAULT 0,
    
    memory_saves INTEGER DEFAULT 0,
    memory_searches INTEGER DEFAULT 0,
    
    workflow_started INTEGER DEFAULT 0,
    workflow_completed INTEGER DEFAULT 0,
    
    cli_commands INTEGER DEFAULT 0,
    cli_errors INTEGER DEFAULT 0,
    
    -- Status
    status TEXT DEFAULT 'active',       -- active/ended/error
    
    -- Metadata
    platform TEXT,
    python_version TEXT,
    fork_agent_version TEXT
);

CREATE INDEX idx_telemetry_sessions_started ON telemetry_sessions(started_at);
CREATE INDEX idx_telemetry_sessions_status ON telemetry_sessions(status);
```

---

## 5. Service Architecture

### 5.1 Domain Layer

```python
# src/domain/entities/telemetry_event.py
@dataclass(frozen=True)
class TelemetryEvent:
    id: str
    event_type: str
    event_category: str
    timestamp: int
    session_id: str | None
    correlation_id: str | None
    attributes: dict[str, Any]
    metrics: dict[str, float] | None
    expires_at: int

# src/domain/ports/telemetry_repository.py
class TelemetryRepository(Protocol):
    def save(self, event: TelemetryEvent) -> None: ...
    def save_batch(self, events: list[TelemetryEvent]) -> None: ...
    def query(
        self,
        event_type: str | None = None,
        session_id: str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 100
    ) -> list[TelemetryEvent]: ...
    def aggregate(
        self,
        metric_name: str,
        labels: dict[str, str],
        bucket_duration: int,
        start_time: int,
        end_time: int
    ) -> list[MetricBucket]: ...
    def cleanup_expired(self) -> int: ...
```

### 5.2 Application Layer

```python
# src/application/services/telemetry/telemetry_service.py
class TelemetryService:
    """Fachada para el sistema de telemetría."""
    
    def __init__(self, repository: TelemetryRepository) -> None:
        self._repository = repository
        self._buffer: list[TelemetryEvent] = []
        self._buffer_size = 100
        self._session_id: str | None = None
    
    def track(
        self,
        event_type: str,
        attributes: dict[str, Any],
        metrics: dict[str, float] | None = None,
        correlation_id: str | None = None
    ) -> str: ...
    
    def track_hook_fire(self, hook_name: str, event_type: str, ...) -> str: ...
    def track_hook_success(self, hook_name: str, duration_ms: int, ...) -> str: ...
    def track_hook_fail(self, hook_name: str, error: Exception, ...) -> str: ...
    def track_agent_spawn(self, agent_id: str, ...) -> str: ...
    def track_agent_stop(self, agent_id: str, duration_ms: int, ...) -> str: ...
    def track_tmux_session_create(self, session_name: str, ...) -> str: ...
    def track_memory_save(self, observation_id: str, ...) -> str: ...
    def track_workflow_outline(self, plan_id: str, ...) -> str: ...
    def track_cli_command(self, command: str, duration_ms: int, ...) -> str: ...
    
    def flush(self) -> None: ...
    def get_session_summary(self, session_id: str) -> SessionSummary: ...
    def get_metrics(
        self,
        metric_name: str,
        labels: dict[str, str],
        period: str  # 1h, 24h, 7d, 30d
    ) -> list[MetricPoint]: ...
    
    def export_prometheus(self) -> str: ...
    def export_json(self, period: str) -> dict: ...
```

### 5.3 Integration with HookService

```python
# src/application/services/orchestration/telemetry_hook_listener.py
class TelemetryHookListener:
    """Listener que captura todos los eventos de hooks para telemetría."""
    
    def __init__(self, telemetry: TelemetryService) -> None:
        self._telemetry = telemetry
    
    def on_hook_fire(self, event: HookFireEvent) -> None:
        self._telemetry.track_hook_fire(
            hook_name=event.hook_name,
            event_type=event.event_type,
            matcher=event.matcher,
            timeout_ms=event.timeout,
            critical=event.critical
        )
    
    def on_hook_success(self, event: HookSuccessEvent) -> None:
        self._telemetry.track_hook_success(
            hook_name=event.hook_name,
            event_type=event.event_type,
            duration_ms=event.duration_ms,
            output_preview=event.output[:100]
        )
    
    def on_hook_fail(self, event: HookFailEvent) -> None:
        self._telemetry.track_hook_fail(
            hook_name=event.hook_name,
            event_type=event.event_type,
            error=event.error,
            duration_ms=event.duration_ms,
            on_failure_policy=event.on_failure
        )
```

---

## 6. CLI Commands

### 6.1 telemetry Command Group

```bash
# Ver estado de telemetría
memory telemetry status

# Ver métricas agregadas
memory telemetry metrics --period 24h
memory telemetry metrics --name hook.fire.count --period 7d

# Ver eventos recientes
memory telemetry events --type hook.fire --limit 50
memory telemetry events --session ses_abc123

# Ver resumen de sesión
memory telemetry session ses_abc123

# Exportar datos
memory telemetry export --format prometheus
memory telemetry export --format json --period 30d --output metrics.json

# Limpiar datos expirados
memory telemetry cleanup --dry-run
memory telemetry cleanup

# Dashboard simple
memory telemetry dashboard
```

### 6.2 Dashboard Output Example

```
╔══════════════════════════════════════════════════════════════╗
║              FORK_AGENT TELEMETRY DASHBOARD                  ║
╠══════════════════════════════════════════════════════════════╣
║ Period: Last 24 hours                                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║ SESSIONS                                                     ║
║ ├── Total sessions: 47                                       ║
║ ├── Avg duration: 12m 34s                                    ║
║ └── Active now: 3                                            ║
║                                                              ║
║ HOOKS                                                        ║
║ ├── Total fired: 312                                         ║
║ ├── Success rate: 98.7%                                      ║
║ ├── Avg latency: 23ms                                        ║
║ └── Top hooks:                                               ║
║     1. workspace-init.sh (156 fires, 100% success)          ║
║     2. tmux-session-per-agent.sh (89 fires, 99% success)    ║
║     3. git-branch-guard.sh (67 fires, 100% success)         ║
║                                                              ║
║ AGENTS                                                       ║
║ ├── Total spawned: 89                                        ║
║ ├── Completed: 82 (92%)                                      ║
║ ├── Failed: 5 (6%)                                           ║
║ ├── Active: 2                                                ║
║ └── Avg duration: 4m 12s                                     ║
║                                                              ║
║ TMUX                                                         ║
║ ├── Sessions created: 94                                     ║
║ ├── Sessions active: 3                                       ║
║ └── Avg session lifetime: 18m 45s                            ║
║                                                              ║
║ MEMORY                                                       ║
║ ├── Observations saved: 234                                  ║
║ ├── Searches performed: 45                                   ║
║ ├── Avg search results: 3.2                                  ║
║ └── Total observations: 8                                    ║
║                                                              ║
║ WORKFLOW                                                     ║
║ ├── Plans created: 12                                        ║
║ ├── Completed cycles: 8 (67%)                                ║
║ ├── Aborted: 2                                               ║
║ └── Avg cycle time: 23m 45s                                  ║
║                                                              ║
║ CLI                                                          ║
║ ├── Commands executed: 567                                   ║
║ ├── Errors: 3 (0.5%)                                         ║
║ └── Top commands:                                            ║
║     1. memory save (234)                                     ║
║     2. memory list (123)                                     ║
║     3. memory workflow status (89)                           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 7. Metrics & KPIs

### 7.1 Key Performance Indicators (KPIs)

| KPI | Fórmula | Target | Alert Threshold |
|-----|---------|--------|-----------------|
| **Hook Success Rate** | `hook.success / hook.fire * 100` | >99% | <95% |
| **Agent Success Rate** | `agent.stop(completed) / agent.spawn * 100` | >90% | <80% |
| **Workflow Completion Rate** | `workflow.ship / workflow.outline * 100` | >80% | <60% |
| **CLI Error Rate** | `cli.error / cli.command * 100` | <1% | >5% |
| **Avg Session Duration** | `avg(session.end.duration_ms)` | 5-30min | >2h |
| **Memory Adoption** | `sessions with memory.save / total sessions` | >50% | <20% |
| **Workflow Adoption** | `sessions with workflow.outline / total sessions` | >30% | <10% |
| **Tmux Efficiency** | `agent.spawn / tmux.session.create` | >0.8 | <0.5 |

### 7.2 Prometheus Metrics Export

```prometheus
# HELP fork_agent_session_total Total sessions started
# TYPE fork_agent_session_total counter
fork_agent_session_total 47

# HELP fork_agent_session_active Currently active sessions
# TYPE fork_agent_session_active gauge
fork_agent_session_active 3

# HELP fork_agent_hook_fire_total Total hooks fired
# TYPE fork_agent_hook_fire_total counter
fork_agent_hook_fire_total{event_type="SessionStart",hook_name="workspace-init.sh"} 156
fork_agent_hook_fire_total{event_type="SubagentStart",hook_name="tmux-session-per-agent.sh"} 89

# HELP fork_agent_hook_success_total Total hooks succeeded
# TYPE fork_agent_hook_success_total counter
fork_agent_hook_success_total{event_type="SessionStart"} 156

# HELP fork_agent_hook_duration_ms Hook execution duration
# TYPE fork_agent_hook_duration_ms histogram
fork_agent_hook_duration_ms_bucket{le="10"} 45
fork_agent_hook_duration_ms_bucket{le="50"} 120
fork_agent_hook_duration_ms_bucket{le="100"} 280
fork_agent_hook_duration_ms_bucket{le="+Inf"} 312
fork_agent_hook_duration_ms_sum 7176
fork_agent_hook_duration_ms_count 312

# HELP fork_agent_agent_spawn_total Total agents spawned
# TYPE fork_agent_agent_spawn_total counter
fork_agent_agent_spawn_total 89

# HELP fork_agent_agent_active Currently active agents
# TYPE fork_agent_agent_active gauge
fork_agent_agent_active 2

# HELP fork_agent_tmux_session_count Current tmux sessions
# TYPE fork_agent_tmux_session_count gauge
fork_agent_tmux_session_count{type="agent"} 2
fork_agent_tmux_session_count{type="fork"} 1

# HELP fork_agent_memory_observations_total Total observations stored
# TYPE fork_agent_memory_observations_total gauge
fork_agent_memory_observations_total 8

# HELP fork_agent_workflow_cycle_total Total workflow cycles
# TYPE fork_agent_workflow_cycle_total counter
fork_agent_workflow_cycle_total{status="completed"} 8
fork_agent_workflow_cycle_total{status="aborted"} 2
```

---

## 8. Retention Policies

| Event Category | Raw Events | Aggregated Metrics |
|----------------|------------|-------------------|
| Session | 90 days | 1 year |
| Hook | 30 days | 90 days |
| Agent | 30 days | 90 days |
| Tmux | 30 days | 90 days |
| Memory | 30 days | 90 days |
| Workflow | 90 days | 1 year |
| CLI | 30 days | 90 days |
| Trace | 7 days | 30 days |
| Error | 90 days | 1 year |

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Create telemetry_events table migration
- [ ] Implement TelemetryEvent entity
- [ ] Implement TelemetryRepository (SQLite)
- [ ] Create TelemetryService basic implementation

### Phase 2: Integration (Week 2)
- [ ] Integrate with HookService
- [ ] Integrate with MemoryService
- [ ] Integrate with WorkflowService
- [ ] Integrate with AgentManager
- [ ] Integrate with TmuxOrchestrator

### Phase 3: CLI & Dashboard (Week 3)
- [ ] Implement `memory telemetry` command group
- [ ] Implement `memory telemetry dashboard`
- [ ] Implement `memory telemetry export`
- [ ] Add Prometheus export endpoint

### Phase 4: Analytics (Week 4)
- [ ] Create telemetry_metrics table
- [ ] Implement metric aggregation
- [ ] Create telemetry_sessions table
- [ ] Implement session summarization
- [ ] Add retention cleanup job

### Phase 5: Polish (Week 5)
- [ ] Performance optimization
- [ ] Buffer and batch writes
- [ ] Error handling improvements
- [ ] Documentation
- [ ] Tests

---

## 10. Questions to Answer

Con este sistema de telemetría podrás responder:

1. **¿Cuántas sesiones de tmux se activaron por sesión?**
   ```sql
   SELECT session_id, COUNT(*) as tmux_sessions
   FROM telemetry_events
   WHERE event_type = 'tmux.session.create'
   GROUP BY session_id;
   ```

2. **¿Cuántos hooks se dispararon?**
   ```sql
   SELECT event_type, COUNT(*) as fires, 
          SUM(CASE WHEN json_extract(attributes, '$.success') THEN 1 ELSE 0 END) as successes
   FROM telemetry_events
   WHERE event_type LIKE 'hook.%'
   GROUP BY event_type;
   ```

3. **¿Cuántas veces se guardó en memory?**
   ```sql
   SELECT COUNT(*) as saves, 
          AVG(json_extract(attributes, '$.content_length')) as avg_content_length
   FROM telemetry_events
   WHERE event_type = 'memory.save';
   ```

4. **¿Cuántas veces los agentes usaron el workflow?**
   ```sql
   SELECT 
     COUNT(DISTINCT session_id) as sessions_with_workflow,
     COUNT(*) as total_workflow_events
   FROM telemetry_events
   WHERE event_type LIKE 'workflow.%';
   ```

---

## 11. Privacy Considerations

- **No PII**: No almacenar información personal
- **Content truncation**: Truncar contenido sensible a 100 chars
- **Hash sensitive data**: Usar hash para stack traces y errores
- **Opt-out**: Permitir desactivar telemetría con env var
- **Local-only**: Por defecto, todo queda en SQLite local

```bash
# Disable telemetry
export FORK_AGENT_TELEMETRY_ENABLED=false
```

---

## 12. Future Enhancements

- [ ] OpenTelemetry integration
- [ ] Remote telemetry export (opt-in)
- [ ] Real-time dashboard (WebSocket)
- [ ] Anomaly detection
- [ ] Predictive analytics
- [ ] Cost attribution per session
