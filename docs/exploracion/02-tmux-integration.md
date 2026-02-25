# Tmux Integration - Gap Analysis

> **Generated**: 2026-02-25 | **Scope**: Tmux orchestration for AI agent sessions

## Executive Summary

La infraestructura de tmux está **bien implementada** (TmuxOrchestrator, AgentManager, resilience patterns, hooks). Sin embargo, **NO está cableada al CLI principal**. Solo existen comandos "doctor" para diagnóstico. Faltan comandos directos de sesión y la integración con workflow.

---

## What IS Implemented

### Core Infrastructure (`src/infrastructure/tmux_orchestrator/`)

| Componente | Status | Descripción |
|------------|--------|-------------|
| `TmuxOrchestrator` | ✅ FULL | Session/window management, content capture, send messages |
| `circuit_breaker.py` | ✅ FULL | CLOSED/OPEN/HALF_OPEN states, failure threshold |
| `retry.py` | ✅ FULL | Exponential backoff, configurable policies |
| `dead_letter_queue.py` | ✅ FULL | DLQ for failed messages |
| `metrics.py` | ✅ FULL | Prometheus metrics export |
| `health.py` | ✅ FULL | Health check responses |

### Agent Management (`src/application/services/agent/agent_manager.py`)

| Feature | Status | Descripción |
|---------|--------|-------------|
| `TmuxAgent` class | ✅ FULL | spawn, terminate, send_input, get_pid |
| `AgentManager` | ✅ FULL | spawn_agent, terminate_agent, list_agents |
| `reconcile_sessions()` | ✅ FULL | Detecta orphaned vs missing sessions |
| `cleanup_orphans()` | ✅ FULL | Dry-run mode, age filtering |
| `get_health_status()` | ✅ FULL | Orphan count, circuit breaker status |
| Health monitoring thread | ✅ FULL | Background health checks |

### Hook Integration

| Hook | Status | Descripción |
|------|--------|-------------|
| `tmux-session-per-agent.sh` | ✅ IMPLEMENTED | Crea sesión `fork-{agent_name}-{timestamp}` |
| hooks.json config | ✅ CONFIGURED | SubagentStart event trigger |

### Doctor Commands (`src/interfaces/cli/fork.py`)

| Comando | Status | Descripción |
|---------|--------|-------------|
| `fork doctor reconcile` | ✅ FULL | Muestra orphaned/missing sessions |
| `fork doctor cleanup-orphans` | ✅ FULL | Limpia sesiones (dry-run por defecto) |
| `fork doctor status` | ✅ FULL | Health status con orphan count |

---

## What IS NOT Implemented

### Missing CLI Commands

| Comando Documentado | Implementación Real |
|--------------------|---------------------|
| `fork session create` | ❌ NO EXISTE |
| `fork session list` | ❌ NO EXISTE |
| `fork session destroy` | ❌ NO EXISTE |
| `fork session attach` | ❌ NO EXISTE |
| `fork agent create` | ❌ NO EXISTE |
| `fork agent list` | ❌ NO EXISTE |

### Workflow Integration

| Feature | Status | Gap |
|---------|--------|-----|
| `workflow execute` → tmux | ❌ MISSING | No spawn de agentes |
| Session tracking | ❌ MISSING | No state persistence de sesiones |
| Task → Session mapping | ❌ MISSING | No relación tarea-sesión |

### API Routes (`src/interfaces/api/routes/agents.py`)

```python
# Línea 54-57: list_sessions retorna array vacío
return SessionListResponse(data=[])

# Línea 60-66: get_session SIEMPRE retorna 404
raise HTTPException(status_code=404, detail="Session not found")

# Línea 69-74: delete_session vacío (solo loggea)
logger.info(f"Delete session requested: {session_id}")
# Sin implementación real!
```

### Hook Output Not Consumed

El hook `tmux-session-per-agent.sh` output:
```json
{
  "hookSpecificOutput": {
    "sessionName": "fork-babyclaude-1-1771800114",
    "attachCommand": "tmux attach -t fork-babyclaude-1-1771800114"
  }
}
```

**PROBLEMA**: Ningún código lee este output para registrar la sesión con AgentManager.

---

## Integration Matrix

| Feature | Infrastructure | CLI | Workflow | API |
|---------|---------------|-----|----------|-----|
| Create session | ✅ | ❌ | ❌ | ❌ STUB |
| List sessions | ✅ | ⚠️ (doctor) | ❌ | ❌ STUB |
| Destroy session | ✅ | ⚠️ (cleanup) | ❌ | ❌ STUB |
| Attach to session | ✅ | ❌ | ❌ | N/A |
| Send message | ✅ | ❌ | ❌ | ❌ STUB |
| Capture output | ✅ | ❌ | ❌ | ❌ STUB |
| Health monitoring | ✅ | ✅ (doctor) | ❌ | ⚠️ |

---

## Specific Gaps

### 1. No Session CLI Commands
```bash
# NO DISPONIBLE:
fork session create --name my-agent --model claude
fork session list
fork session attach my-agent
fork session destroy my-agent
```

### 2. Hook Output Ignored
```python
# DEBERÍA: Consumir output del hook
def on_subagent_start(event):
    result = run_hook("tmux-session-per-agent.sh")
    session_info = json.loads(result)
    agent_manager.register_session(session_info["sessionName"])
```

### 3. No Named Sessions
- Sesiones usan timestamp: `fork-{agent}-{timestamp}`
- Ephímeras por diseño
- Faltan: named sessions, persistent templates

---

## Recommendations

### Tier 1 - Critical
1. **Agregar session CLI commands**: create/list/destroy/attach
2. **Consumir hook output**: Registrar sesiones en AgentManager

### Tier 2 - Important  
3. **Implementar API routes**: Conectar a AgentManager, no stubs
4. **Workflow integration**: `workflow execute` → spawn tmux sessions

### Tier 3 - Enhancement
5. **Named sessions**: Permitir nombres persistentes
6. **Session templates**: Configuraciones predefinidas

---

## Files Involved

| Archivo | Propósito |
|---------|-----------|
| `src/infrastructure/tmux_orchestrator/__init__.py` | Core orchestrator |
| `src/application/services/agent/agent_manager.py` | Agent lifecycle |
| `src/interfaces/cli/fork.py` | Doctor commands only |
| `src/interfaces/api/routes/agents.py` | API stubs |
| `.hooks/tmux-session-per-agent.sh` | Session creation hook |
