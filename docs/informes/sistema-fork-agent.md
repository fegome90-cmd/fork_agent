# Informe: Sistema fork_agent

> **Fecha:** 2026-02-23
> **Repositorio:** tmux_fork
> **Propósito:** Documentación completa del sistema de orquestación de agentes, memoria persistente y hooks de automatización.

---

## Resumen Ejecutivo

**fork_agent** es una plataforma agéntica que orquesta múltiples agentes AI mediante tmux, con un sistema de memoria persistente, hooks de automatización event-driven y workflow disciplinado. El objetivo es que el sistema funcione **sin fricción** para el desarrollador.

### Componentes Principales

| Sistema | Propósito | Tecnologías |
|---------|-----------|-------------|
| tmux Orchestrator | Gestión de sesiones de sub-agentes | tmux, subprocess |
| Memory CLI | Persistencia de observaciones y estado | SQLite, Typer |
| Hooks System | Automatización event-driven | Shell scripts, JSON config |
| Workflow | Gates obligatorios (outline→execute→verify→ship) | State machines |
| Resilience | Circuit breaker, retries, DLQ | Python threading |

---

## 1. Sistema de tmux con Sub-Agentes

### 1.1 Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                    TmuxOrchestrator                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  AgentManager                                        │   │
│  │  ├── TmuxAgent (babyclaude-1) → fork-babyclaude-1   │   │
│  │  ├── TmuxAgent (babyclaude-2) → fork-babyclaude-2   │   │
│  │  └── TmuxAgent (oracle)      → fork-oracle-timestamp│   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Resilience Layer                                    │   │
│  │  ├── CircuitBreaker (3 failures → OPEN)             │   │
│  │  ├── ExponentialBackoff (1s → 10s max)              │   │
│  │  ├── DeadLetterQueue (failed messages)              │   │
│  │  └── PrometheusMetrics (spawn, latency, failures)   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Componentes del Orchestrator

Ubicación: `src/infrastructure/tmux_orchestrator/`

| Archivo | Clase/Función | Responsabilidad |
|---------|---------------|-----------------|
| `__init__.py` | `TmuxOrchestrator` | API central para gestionar sesiones, ventanas, mensajes |
| `__init__.py` | `TmuxSession` | Dataclass para representar una sesión tmux |
| `__init__.py` | `TmuxWindow` | Dataclass para representar una ventana tmux |
| `__init__.py` | `create_agent_session()` | Factory para crear agente en tmux |
| `__init__.py` | `send_task_to_agent()` | Enviar tarea a ventana de agente |
| `__init__.py` | `get_agent_output()` | Capturar output de agente |
| `circuit_breaker.py` | `TmuxCircuitBreaker` | Protección contra fallos en cascada |
| `circuit_breaker.py` | `CircuitState` | Enum: CLOSED, OPEN, HALF_OPEN |
| `retry.py` | `retry_with_backoff()` | Reintentos async con backoff exponencial |
| `retry.py` | `retry_sync()` | Reintentos síncronos |
| `retry.py` | `ExponentialBackoff` | Calculador de delays |
| `retry.py` | `RetryConfig` | Configuración de reintentos |
| `retry.py` | `RetryResult` | Resultado de operación con retry |
| `dead_letter_queue.py` | `DeadLetterQueue` | Cola de mensajes fallidos con persistencia |
| `dead_letter_queue.py` | `DeadLetterItem` | Item en la cola DLQ |
| `metrics.py` | `PrometheusMetrics` | Métricas thread-safe estilo Prometheus |
| `metrics.py` | `Metrics` | Dataclass con contadores |
| `health.py` | `HealthResponse` | Response de health check |
| `health.py` | `build_health_response()` | Constructor de health response |
| `json_logging.py` | `JSONFormatter` | Formatter de logs en JSON |
| `json_logging.py` | `setup_json_logging()` | Setup de logging estructurado |

### 1.3 Flujo de Creación de Sub-Agente

```python
# 1. Configurar agente
from src.application.services.agent.agent_manager import AgentConfig, get_agent_manager
from pathlib import Path

config = AgentConfig(
    name="babyclaude-1",
    agent_type="opencode",
    working_dir=Path("/project"),
    timeout_seconds=300,
    max_retries=3
)

# 2. Spawn con validación automática
manager = get_agent_manager()
agent = manager.spawn_agent(config)

# 3. Enviar tarea al agente
agent.send_input("opencode run -m opencode/glm-5-free 'implementar auth'")

# 4. Capturar output
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator
orchestrator = TmuxOrchestrator()
output = orchestrator.capture_content("fork-babyclaude-1-1740321234", 0, lines=100)
```

### 1.4 Integración con Hooks

El hook `tmux-session-per-agent.sh` se dispara en `SubagentStart`:

```bash
# Variables de entorno esperadas
AGENT_NAME="babyclaude-1"
CLAUDE_PROJECT_DIR="/path/to/project"
WORKTREE_PATH="/path/to/worktree"

# Ejecutar hook
.hooks/tmux-session-per-agent.sh

# Output JSON
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "sessionName": "fork-babyclaude-1-1740321234",
    "attachCommand": "tmux attach -t fork-babyclaude-1-1740321234",
    "sendCommand": "tmux send-keys -t fork-babyclaude-1-1740321234",
    "sessionPid": "12345",
    "status": "ready"
  }
}
```

### 1.5 Estados del Circuit Breaker

```
┌─────────┐  failures >= 3   ┌──────────┐
│ CLOSED  │ ────────────────▶│   OPEN   │
└─────────┘                  └──────────┘
     ▲                            │
     │                            │ timeout (30s)
     │                            ▼
     │                       ┌───────────┐
     │  success              │ HALF_OPEN │
     └───────────────────────└───────────┘
                          max_calls=2
```

---

## 2. Sistema de Memoria

### 2.1 Arquitectura DDD

```
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                            │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │   Observation   │  │    ScheduledTask                │  │
│  │  - id: str      │  │  - id: str                      │  │
│  │  - timestamp    │  │  - command: str                 │  │
│  │  - content: str │  │  - interval_seconds: int        │  │
│  │  - metadata     │  │  - next_run: datetime           │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Ports (Protocol)                                       ││
│  │  - IObservationRepository                               ││
│  │  - IScheduledTaskRepository                             ││
│  │  - IEventDispatcher                                     ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  DatabaseConnection (SQLite + WAL)                      ││
│  │  - Thread-safe via thread-local storage                 ││
│  │  - PRAGMA journal_mode=WAL                              ││
│  │  - PRAGMA busy_timeout=5000ms                           ││
│  │  - PRAGMA foreign_keys=ON                               ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Repositories                                           ││
│  │  - ObservationRepository (CRUD observaciones)           ││
│  │  - ScheduledTaskRepository (tareas programadas)         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Entidad Observation

```python
# src/domain/entities/observation.py
@dataclass(frozen=True)
class Observation:
    """Entidad inmutable para almacenar observaciones/memoria."""
    id: str
    timestamp: int          # Unix timestamp en milisegundos
    content: str            # Contenido principal
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        # Validaciones de invariants
        if not self.id:
            raise ValueError("id no puede estar vacío")
        if self.timestamp < 0:
            raise ValueError("timestamp debe ser no negativo")
        if not self.content:
            raise ValueError("content no puede estar vacío")
```

### 2.3 Configuración de Base de Datos

```python
# src/infrastructure/persistence/database.py
@dataclass
class DatabaseConfig:
    db_path: Path
    journal_mode: JournalMode = JournalMode.WAL
    busy_timeout_ms: int = 5000
    foreign_keys: bool = True
```

### 2.4 CLI de Memoria

```bash
# Observaciones
memory save "nota importante"              # Guardar
memory search "query"                      # Buscar
memory list                                # Listar todas
memory get <id>                            # Obtener por ID
memory delete <id>                         # Eliminar

# Schedule (tareas programadas)
memory schedule add "echo hello" 60        # Programar cada 60s
memory schedule list                        # Listar tareas
memory schedule show <id>                  # Ver detalle
memory schedule cancel <id>                # Cancelar

# Workspace
memory workspace create my-workspace       # Crear workspace
memory workspace list                      # Listar workspaces
memory workspace enter my-workspace        # Cambiar workspace
memory workspace detect                    # Detectar workspace actual
```

### 2.5 Workflow Disciplinado

Sistema de **gates obligatorios** que fuerza el flujo:

```
outline → execute → verify → ship
```

| Comando | Archivo de Estado | Dependencia |
|---------|-------------------|-------------|
| `memory workflow outline "tarea"` | `plan-state.json` | Ninguna |
| `memory workflow execute` | `execute-state.json` | Requiere plan-state.json |
| `memory workflow verify` | `verify-state.json` | Requiere execute-state.json |
| `memory workflow ship` | — | Requiere verify con unlock_ship=true |
| `memory workflow status` | — | Lee todos los estados |

#### Estados del Workflow

```python
# src/application/services/workflow/state.py
class WorkflowPhase(str, Enum):
    PLANNING = "planning"
    OUTLINED = "outlined"
    EXECUTING = "executing"
    EXECUTED = "executed"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    SHIPPING = "shipping"
    SHIPPED = "shipped"

@dataclass
class PlanState:
    session_id: str
    status: str = "planning"
    phase: WorkflowPhase = WorkflowPhase.PLANNING
    plan_file: str = ".claude/plans/plan.md"
    tasks: list[Task] = field(default_factory=list)

@dataclass
class ExecuteState:
    session_id: str
    status: str = "idle"
    tasks: list[Task] = field(default_factory=list)
    current_task_index: int = 0

@dataclass
class VerifyState:
    session_id: str
    status: str = "pending"
    unlock_ship: bool = False
    test_results: dict[str, bool] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
```

---

## 3. Sistema de Hooks

### 3.1 Arquitectura Event-Driven

```
┌─────────────────────────────────────────────────────────────┐
│                    HookService                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  RuleLoader                                          │   │
│  │  - Lee .hooks/hooks.json                             │   │
│  │  - Convierte a lista de Rule                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  EventDispatcher                                     │   │
│  │  - dispatch(event) → match rules → run actions      │   │
│  │  - Stateless: cada event se evalúa contra todas     │   │
│  │    las reglas                                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ShellActionRunner                                   │   │
│  │  - Ejecuta scripts shell en .hooks/                  │   │
│  │  - Timeout configurable                              │   │
│  │  - Captura stdout/stderr                             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Eventos Soportados

```python
# src/application/services/orchestration/events.py

@dataclass(frozen=True)
class SessionStartEvent:
    """Disparado al iniciar una nueva sesión."""
    session_id: str = ""

@dataclass(frozen=True)
class SubagentStartEvent:
    """Disparado cuando un sub-agente comienza."""
    agent_name: str

@dataclass(frozen=True)
class SubagentStopEvent:
    """Disparado cuando un sub-agente termina."""
    agent_name: str
    duration_ms: int = 0
    status: str = "completed"

@dataclass(frozen=True)
class ToolPreExecutionEvent:
    """Disparado antes de ejecutar un tool (PreToolUse)."""
    tool_name: str

@dataclass(frozen=True)
class UserCommandEvent:
    """Disparado cuando el usuario invoca un comando CLI."""
    command_name: str
    args: tuple[str, ...] = ()

@dataclass(frozen=True)
class FileWrittenEvent:
    """Disparado cuando se escribe un archivo."""
    path: str
```

### 3.3 Configuración de Hooks

```json
// .hooks/hooks.json
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

### 3.4 Scripts de Hooks

| Script | Evento | Propósito | Output |
|--------|--------|-----------|--------|
| `workspace-init.sh` | SessionStart | Inicializar workspace | workspaceId, traces dir |
| `tmux-session-per-agent.sh` | SubagentStart | Crear sesión tmux aislada | sessionName, attachCommand |
| `memory-trace-writer.sh` | SubagentStop | Escribir trace de ejecución | traceFile, duration |
| `git-branch-guard.sh` | PreToolUse | Bloquear git peligroso | allowed: true/false |

### 3.5 Seguridad Git

```bash
# .hooks/git-branch-guard.sh
# Exit codes:
#   0 = Permitido
#   2 = Bloqueado

# ✅ Permitidos
git add, commit, status, diff, log, show, blame, branch, fetch

# ❌ Bloqueados
git checkout, switch, reset, clean, push, pull, rebase, merge, stash, cherry-pick
```

### 3.6 Uso Programático

```python
from src.application.services.orchestration.hook_service import HookService
from src.application.services.orchestration.events import (
    SessionStartEvent,
    SubagentStartEvent,
    SubagentStopEvent
)

# Crear servicio
service = HookService()  # Usa .hooks/hooks.json por defecto

# Dispatch eventos
service.dispatch(SessionStartEvent(session_id="mi-sesion"))
service.dispatch(SubagentStartEvent(agent_name="babyclaude-1"))
service.dispatch(SubagentStopEvent(agent_name="babyclaude-1", duration_ms=5000))

# Recargar configuración
service.reload()
```

---

## 4. Comparativa de Directorios de Agentes

### 4.1 Estructura Comparada

| Componente | `.claude/` | `.opencode/` | `.kilocode/` | `.gemini/` |
|------------|------------|--------------|--------------|------------|
| **Commands** | ✅ 13 archivos | ✅ 7 archivos | ❌ | ❌ |
| **Skills** | ✅ custom | ❌ (hereda) | ✅ 17 skills | ✅ 37 skills |
| **Hooks** | ✅ Shell + JSON | ✅ TypeScript | ❌ | ❌ |
| **Sessions** | ✅ | ✅ (comparte) | ✅ mínimo | ❌ |
| **State Files** | ✅ plan/execute/verify | ❌ | ❌ | ❌ |
| **Context Memory** | ✅ | ❌ | ❌ | ❌ |
| **Traces** | ✅ | ❌ | ❌ | ❌ |

### 4.2 Skills Compartidas (Superpowers)

Todos los agentes heredan del directorio `skills/` raíz:

- `superpowers-brainstorming`
- `superpowers-dispatching-parallel-agents`
- `superpowers-executing-plans`
- `superpowers-finishing-a-development-branch`
- `superpowers-receiving-code-review`
- `superprises-requesting-code-review`
- `superpowers-subagent-driven-development`
- `superpowers-systematic-debugging`
- `superpowers-test-driven-development`
- `superpowers-using-git-worktrees`
- `superpowers-using-superpowers`
- `superpowers-verification-before-completion`
- `superpowers-writing-plans`
- `superpowers-writing-skills`

### 4.3 Commands de Fork (Compartidos)

| Command | `.claude` | `.opencode` | Propósito |
|---------|-----------|-------------|-----------|
| `fork-checkpoint.md` | ✅ | ✅ | Guardar handoff de sesión |
| `fork-resume.md` | ✅ | ✅ | Continuar desde handoff |
| `fork-prune-sessions.md` | ✅ | ✅ | Limpiar sesiones antiguas |
| `fork-init.md` | ❌ | ✅ | Inicializar sesión fork |

---

## 5. Flujo End-to-End Sin Fricción

### 5.1 Diagrama de Flujo Completo

```
Usuario → /fork-init "Implementar OAuth"
    │
    ├─→ [SessionStart] → workspace-init.sh
    │   └─→ Crea .claude/traces/, .claude/context-memory-id
    │
    ├─→ memory workflow outline "Implementar OAuth"
    │   └─→ Crea .claude/plan-state.json
    │   └─→ Crea .claude/plans/plan.md
    │
    ├─→ memory workflow execute
    │   ├─→ [SubagentStart] → tmux-session-per-agent.sh
    │   │   └─→ Crea fork-{agent}-{timestamp}
    │   │   └─→ Output: sessionName, attachCommand
    │   │
    │   └─→ Agentes trabajan en sesiones tmux aisladas
    │       └─→ TmuxOrchestrator.send_message()
    │       └─→ CircuitBreaker protege contra fallos
    │
    ├─→ memory workflow verify
    │   ├─→ [SubagentStop] → memory-trace-writer.sh
    │   │   └─→ Actualiza .claude/traces/current-trace.json
    │   │
    │   └─→ Crea .claude/verify-state.json (unlock_ship: true)
    │
    └─→ memory workflow ship
        └─→ Shipping completado
```

### 5.2 Puntos de Fricción Identificados y Solucionados

| Fricción | Solución | Implementación |
|----------|----------|----------------|
| Sesiones tmux huérfanas | DeadLetterQueue + cleanup | `dead_letter_queue.py` |
| Fallos en cascada | CircuitBreaker | `circuit_breaker.py` |
| Timeouts sin manejo | Retry con backoff | `retry.py` |
| Estado inconsistente | Gates obligatorios | `workflow/state.py` |
| Git accidental | Allowlist de comandos | `git-branch-guard.sh` |
| Sin observabilidad | PrometheusMetrics | `metrics.py` |
| Logs no estructurados | JSON logging | `json_logging.py` |

---

## 6. Métricas y Observabilidad

### 6.1 Métricas Disponibles

```prometheus
# Agentes
agent_spawn_total 42
agent_spawn_failures_total 3

# IPC (Inter-Process Communication)
ipc_message_latency_seconds 0.045
ipc_message_failures_total 1

# Sesiones tmux
tmux_session_count 4
```

### 6.2 Uso de Métricas

```python
from src.infrastructure.tmux_orchestrator.metrics import get_prometheus_metrics

metrics = get_prometheus_metrics()

# Incrementar spawn
metrics.inc_spawn(success=True)

# Record latency
metrics.record_latency(0.045)

# Set session count
metrics.set_session_count(4)

# Exportar formato Prometheus
print(metrics.format_prometheus())
```

### 6.3 Health Check

```python
from src.infrastructure.tmux_orchestrator.health import health

response = health()
# {
#   "status": "healthy",
#   "agents": {
#     "babyclaude-1": "healthy",
#     "oracle": "healthy"
#   },
#   "circuit_breakers": {
#     "tmux": "closed"
#   }
# }
```

---

## 7. Script de Fork Generation

### 7.1 Uso

```bash
# Generar fork para .claude
./scripts/fork-generate.sh .claude ../nuevo-proyecto

# Generar fork para .opencode
./scripts/fork-generate.sh .opencode ../nuevo-proyecto

# Generar fork para .kilocode
./scripts/fork-generate.sh .kilocode ../nuevo-proyecto

# Generar fork para .gemini
./scripts/fork-generate.sh .gemini ../nuevo-proyecto
```

### 7.2 Output del Script

```
[INFO] Iniciando fork generation...
[INFO] Agente: .claude
[INFO] Destino: ../nuevo-proyecto
[OK] Estructura creada para .claude
[INFO] Copiado command: fork-checkpoint.md
[INFO] Copiado command: fork-resume.md
[INFO] Copiado command: fork-prune-sessions.md
[OK] Creado settings.json con hooks
[OK] Copiada skill fork_terminal
[OK] Creados archivos de estado
[OK] Creado CLAUDE.md

========================================
✅ Fork generado exitosamente
========================================

Agente: .claude
Destino: ../nuevo-proyecto/.claude

Estructura creada:
  .claude/
  ├── commands/     # Comandos fork
  ├── skills/       # Skills custom
  ├── hooks/        # Hooks shell
  ├── sessions/     # Handoffs
  ├── traces/       # Traces
  └── *.json        # Estado y config

Próximos pasos:
  1. cd ../nuevo-proyecto
  2. Revisar .claude/settings.json
  3. Personalizar skills/commands según necesidad
```

---

## 8. Estructura de Archivos del Repositorio

```
tmux_fork/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── observation.py      # Entidad inmutable de memoria
│   │   │   ├── message.py          # Mensajes IPC
│   │   │   ├── rule.py             # Reglas de hooks
│   │   │   ├── terminal.py         # Entidad de terminal
│   │   │   └── scheduled_task.py   # Tareas programadas
│   │   ├── ports/
│   │   │   ├── observation_repository.py
│   │   │   ├── scheduled_task_repository.py
│   │   │   └── event_ports.py
│   │   └── exceptions/
│   │
│   ├── application/
│   │   ├── services/
│   │   │   ├── orchestration/
│   │   │   │   ├── events.py       # Dataclasses de eventos
│   │   │   │   ├── hook_service.py # Servicio de hooks
│   │   │   │   ├── dispatcher.py   # Router de eventos
│   │   │   │   ├── specs.py        # Specifications
│   │   │   │   └── actions.py      # Definiciones de acciones
│   │   │   ├── workflow/
│   │   │   │   └── state.py        # PlanState, ExecuteState, VerifyState
│   │   │   ├── agent/
│   │   │   │   ├── agent_manager.py # Ciclo de vida de agentes
│   │   │   │   └── ipc_bridge.py    # Comunicación inter-agente
│   │   │   ├── messaging/
│   │   │   │   ├── message_protocol.py
│   │   │   │   └── agent_messenger.py
│   │   │   ├── workspace/
│   │   │   │   ├── workspace_manager.py
│   │   │   │   ├── workspace_detector.py
│   │   │   │   └── hook_runner.py
│   │   │   ├── terminal/
│   │   │   │   ├── terminal_spawner.py
│   │   │   │   └── platform_detector.py
│   │   │   ├── memory_service.py
│   │   │   └── scheduler_service.py
│   │   └── use_cases/
│   │       ├── save_observation.py
│   │       ├── get_observation.py
│   │       ├── search_observations.py
│   │       ├── list_observations.py
│   │       ├── delete_observation.py
│   │       └── fork_terminal.py
│   │
│   ├── infrastructure/
│   │   ├── tmux_orchestrator/
│   │   │   ├── __init__.py         # TmuxOrchestrator, helpers
│   │   │   ├── circuit_breaker.py
│   │   │   ├── retry.py
│   │   │   ├── dead_letter_queue.py
│   │   │   ├── metrics.py
│   │   │   ├── health.py
│   │   │   └── json_logging.py
│   │   ├── orchestration/
│   │   │   ├── rule_loader.py
│   │   │   └── shell_action_runner.py
│   │   ├── persistence/
│   │   │   ├── database.py         # SQLite + WAL
│   │   │   ├── container.py        # DI container
│   │   │   ├── migrations.py
│   │   │   ├── message_store.py
│   │   │   └── repositories/
│   │   │       ├── observation_repository.py
│   │   │       └── scheduled_task_repository.py
│   │   ├── config/
│   │   │   ├── config.py
│   │   │   └── workspace_config.py
│   │   └── platform/
│   │       └── git/
│   │           └── git_command_executor.py
│   │
│   └── interfaces/
│       ├── cli/
│       │   ├── main.py              # Entry point (memory)
│       │   ├── fork.py
│       │   ├── messaging_commands.py
│       │   ├── workspace_commands.py
│       │   └── commands/
│       │       ├── save.py
│       │       ├── search.py
│       │       ├── list.py
│       │       ├── get.py
│       │       ├── delete.py
│       │       ├── workflow.py
│       │       └── schedule.py
│       └── api/
│           ├── main.py              # FastAPI app
│           ├── config.py
│           ├── dependencies.py
│           ├── middleware/
│           │   └── rate_limit.py
│           ├── models/
│           └── routes/
│               ├── agents.py
│               ├── memory.py
│               ├── processes.py
│               ├── system.py
│               └── webhooks.py
│
├── .hooks/
│   ├── hooks.json                   # Configuración de hooks
│   ├── workspace-init.sh            # SessionStart
│   ├── tmux-session-per-agent.sh    # SubagentStart
│   ├── memory-trace-writer.sh       # SubagentStop
│   └── git-branch-guard.sh          # PreToolUse
│
├── .claude/
│   ├── commands/                    # Comandos personalizados
│   ├── skills/                      # Skills del proyecto
│   │   ├── fork_agent_session.md
│   │   └── fork_terminal/
│   ├── hooks/                       # Hooks específicos
│   ├── sessions/                    # Handoffs guardados
│   ├── traces/                      # Traces de ejecución
│   ├── context_memory/              # Memoria de contexto
│   ├── plans/                       # Archivos de plan
│   ├── docs/                        # Documentación interna
│   ├── settings.json                # Configuración de hooks
│   ├── settings.local.json          # Config local
│   ├── plan-state.json
│   ├── execute-state.json
│   └── verify-state.json
│
├── .opencode/
│   ├── command/                     # Comandos fork
│   ├── plugin/                      # Plugins TypeScript
│   └── manual_v0.1.md
│
├── scripts/
│   └── fork-generate.sh             # Script de fork generation
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── skills/                          # Skills raíz (heredadas)
│   └── ... (14 superpowers skills)
│
├── docs/
│   ├── informes/
│   ├── monitoring/
│   ├── runbook/
│   └── investigacion/
│
├── pyproject.toml
├── AGENTS.md
├── CLAUDE.md
├── README.md
└── opencode.json
```

---

## 9. Conclusiones

### 9.1 Fortalezas del Sistema

1. **Arquitectura DDD limpia**: Separación clara entre domain, application, infrastructure e interfaces
2. **Resiliencia integrada**: Circuit breaker, retries y DLQ en todas las operaciones críticas
3. **Observabilidad completa**: Métricas Prometheus, health checks y logs estructurados
4. **Automatización event-driven**: Hooks desacoplados con matcher patterns
5. **Workflow disciplinado**: Gates obligatorios que previenen saltos de pasos
6. **Seguridad Git**: Allowlist que previene operaciones destructivas accidentales

### 9.2 Áreas de Mejora Potencial

1. **Tests de integración**: Ampliar cobertura de tests e2e para el flujo completo
2. **Documentación de API**: Agregar OpenAPI/Swagger para la API REST
3. **Métricas de negocio**: Agregar métricas específicas del dominio (tasks completadas, etc.)
4. **Notificaciones**: Sistema de alertas cuando el circuit breaker se abre

### 9.3 Próximos Pasos Recomendados

1. Ejecutar `./scripts/fork-generate.sh` para nuevos proyectos
2. Configurar monitoreo con las métricas Prometheus
3. Documentar flujos de trabajo específicos del equipo
4. Agregar más skills específicas del dominio según necesidad

---

*Documento generado: 2026-02-23*
*Repositorio: tmux_fork*
