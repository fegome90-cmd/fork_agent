# Workflow System - Gap Analysis

> **Generated**: 2026-02-25 | **Scope**: Agentic Workflow (outline → execute → verify → ship)

## Executive Summary

El sistema de workflow tiene **scaffolding completo** (CLI, state management, tests) pero **la lógica de negocio es STUB**. Los comandos outline/execute/verify/ship solo actualizan archivos JSON sin hacer trabajo real. **No hay integración** con tmux, memory, ni hooks.

---

## Implementation Status

### CLI Commands (`src/interfaces/cli/commands/workflow.py`)

| Comando | Status | Problema |
|---------|--------|----------|
| `outline` | ⚠️ PARTIAL | Crea PlanState pero NO analiza tarea ni genera breakdown de tasks |
| `execute` | ❌ STUB | Crea ExecuteState pero NO ejecuta nada. Flag `--parallel` ignorada |
| `verify` | ❌ STUB | Crea VerifyState pero NO corre tests. Resultados mockeados |
| `ship` | ❌ STUB | Solo imprime mensajes. Flags `--branch` y `--cleanup` ignoradas |
| `status` | ✅ FULL | Muestra estado correctamente |

### State Management (`src/application/services/workflow/state.py`)

| Componente | Status |
|------------|--------|
| `PlanState` | ✅ Implementado con schema versioning |
| `ExecuteState` | ✅ Implementado con schema versioning |
| `VerifyState` | ✅ Implementado con schema versioning |
| `Task` entity | ✅ Implementado con `worktree_path` field (no usado) |
| Migración v0→v1 | ✅ Implementado |

### API Routes (`src/interfaces/api/routes/workflow.py`)

| Endpoint | Status | Problema |
|----------|--------|----------|
| `POST /workflow/outline` | ❌ STUB | Retorna UUID, no hace planning |
| `POST /{plan_id}/execute` | ❌ STUB | Retorna UUID, no ejecuta |
| `POST /{plan_id}/verify` | ❌ STUB | Retorna resultados mock (50/50 tests, 95.2% coverage) |
| `POST /{plan_id}/ship` | ❌ STUB | Retorna status, no hace ship |
| `GET /{plan_id}/status` | ❌ STUB | Siempre retorna "pending" |

---

## Integration Gaps

| Integración | Status | Evidencia |
|-------------|--------|-----------|
| **tmux** | ❌ MISSING | No se crean sesiones tmux en workflow execute |
| **memory service** | ❌ MISSING | Workflow no guarda observations ni usa MemoryService |
| **hooks** | ❌ MISSING | hooks.json no tiene eventos de workflow |
| **telemetry** | ❌ MISSING | `telemetry_service.track_workflow_*` existe pero nunca llamado |

---

## Specific Code Gaps

### 1. `outline` command (líneas 66-76)
```python
# PROBLEMA: Solo escribe markdown estático
plan_content = f"""# Plan: {task_description}
### Tasks
- [ ] {task_description}
"""
# DEBERÍA: Analizar tarea, crear Task objects, generar breakdown
```

### 2. `execute` command (líneas 82-104)
```python
# PROBLEMA: tasks siempre está vacío porque outline no lo popula
exec_state = ExecuteState(
    tasks=plan.tasks,  # plan.tasks = [] siempre!
)
# DEBERÍA: Lanzar agentes en tmux, ejecutar tareas
```

### 3. `verify` command (líneas 120-121)
```python
# PROBLEMA: Resultados mockeados
if run_tests:
    verify_state.test_results = {"passed": True}  # Siempre pasa!
# DEBERÍA: Ejecutar pytest, calcular coverage, hashear archivos
```

### 4. `ship` command (líneas 139-141)
```python
# PROBLEMA: Solo imprime
typer.echo(f"✓ Shipping to {target_branch}")
typer.echo("Workflow complete!")
# DEBERÍA: git commit, git push, cleanup worktrees
```

---

## Missing Hooks

El archivo `.hooks/hooks.json` solo incluye:
- SessionStart
- SubagentStart
- SubagentStop
- PreToolUse (git only)

**Eventos de workflow faltantes:**
- `WorkflowOutlineStart` / `WorkflowOutlineComplete`
- `WorkflowExecuteStart` / `WorkflowExecuteComplete`
- `WorkflowVerifyStart` / `WorkflowVerifyComplete`
- `WorkflowShipStart` / `WorkflowShipComplete`
- `WorkflowPhaseChange`

---

## Recommendations

### Tier 1 - Critical (Implementar primero)
1. **Conectar outline → Task creation**: Analizar descripción y generar lista de Task objects
2. **Conectar execute → Agent spawn**: Usar TmuxOrchestrator para lanzar agentes por tarea

### Tier 2 - Important
3. **Implementar verify real**: Ejecutar `pytest`, calcular coverage real, hashear archivos
4. **Implementar ship real**: git commit/push, cleanup worktrees

### Tier 3 - Enhancement
5. **Agregar workflow hooks**: Dispatch events en cada cambio de fase
6. **Conectar telemetry**: Llamar `track_workflow_*` methods

---

## Files Involved

| Archivo | Propósito |
|---------|-----------|
| `src/interfaces/cli/commands/workflow.py` | CLI commands (STUB) |
| `src/application/services/workflow/state.py` | State management (OK) |
| `src/interfaces/api/routes/workflow.py` | API endpoints (STUB) |
| `tests/unit/interfaces/cli/commands/test_workflow.py` | Unit tests |
