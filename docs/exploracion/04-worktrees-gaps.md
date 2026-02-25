# Worktrees System - Gap Analysis

> **Generated**: 2026-02-25 | **Scope**: Git worktree-based workspace management

## Executive Summary

Las **operaciones core de worktree están implementadas** (GitCommandExecutor, WorkspaceManager, CLI commands). Sin embargo, **NO hay automatización** para crear worktrees al lanzar agentes, **NO hay aislamiento de memoria** por worktree, y el sistema `work_O` documentado en brain_dope **nunca fue implementado**.

---

## What IS Implemented

### Git Worktree Core Operations

| Feature | Location | Status |
|---------|----------|--------|
| `worktree_add()` | `git_command_executor.py` | ✅ FULL |
| `worktree_remove()` | `git_command_executor.py` | ✅ FULL |
| `worktree_list()` | `git_command_executor.py` | ✅ FULL |
| `worktree_is_valid()` | `git_command_executor.py` | ✅ FULL |

### Workspace Management (`src/application/services/workspace/`)

| Feature | Status | Descripción |
|---------|--------|-------------|
| `WorkspaceManager` | ✅ FULL | Create, remove, list, detect, start workspaces |
| `LayoutType` enum | ✅ FULL | NESTED, OUTER_NESTED, SIBLING |
| `WorkspaceDetector` | ✅ FULL | Detecta worktree desde cualquier path |
| `HookRunner` | ✅ FULL | Setup/teardown hooks en worktree create |
| `Workspace` entity | ✅ FULL | name, path, branch, layout, state |

### CLI Commands (`src/interfaces/cli/workspace_commands.py`)

| Comando | Status | Descripción |
|---------|--------|-------------|
| `memory workspace create` | ✅ FULL | Crea worktree + branch |
| `memory workspace list` | ✅ FULL | Lista workspaces |
| `memory workspace remove` | ✅ FULL | Elimina worktree |
| `memory workspace enter` | ✅ FULL | Entra a workspace (puede spawn tmux) |
| `memory workspace detect` | ✅ FULL | Detecta workspace actual |
| `memory workspace config` | ✅ FULL | Muestra/actualiza config |

### Workflow State Schema

| Field | Status | Uso |
|-------|--------|-----|
| `Task.worktree_path` | ✅ Schema exists | ❌ NEVER POPULATED |

---

## What IS NOT Implemented

### Agent Session ↔ Worktree Binding

| Gap | Severity | Evidence |
|-----|----------|----------|
| No auto-creation on agent spawn | CRITICAL | Worktrees deben ser manuales |
| No task → worktree mapping | CRITICAL | `worktree_path` nunca se popula |
| No tracking which agent in which worktree | CRITICAL | Sin registro |

### Memory Isolation Per Worktree

| Gap | Severity | Evidence |
|-----|----------|----------|
| Single SQLite DB | HIGH | `container.py` usa path fijo |
| No workspace-aware DB path | HIGH | No hay `db_path` por workspace |
| Shared observations | HIGH | Todos los worktrees ven mismas observaciones |

### Tmux + Worktree Orchestration

| Gap | Severity | Evidence |
|-----|----------|----------|
| No tmux+worktree combo | HIGH | workspace enter puede spawn tmux pero no automático |
| No workflow automation | HIGH | workflow execute no crea worktrees |

### Workflow Integration

| Gap | Severity | Evidence |
|-----|----------|----------|
| `--cleanup` flag is dead code | MEDIUM | workflow.py:131 no limpia worktrees |
| No orphan worktree detection | MEDIUM | Sin limpieza automática |

---

## work_O System (Documented but NOT Implemented)

From `docs/investigacion/brain_dope_work_O.md`:

| Feature | Documentado | Implementado | Status |
|---------|-------------|--------------|--------|
| `take_wo` | ✅ Crea branch + worktree | ❌ Solo metadata | ❌ MISSING |
| `finish_wo` | ✅ Cleanup worktree | ❌ No limpia | ❌ MISSING |
| Locking system | ✅ Con stale detection | ❌ | ❌ MISSING |
| Checkpoint system | ✅ | ❌ | ❌ MISSING |
| Artifact generation | ✅ Para handoff | ❌ | ❌ MISSING |

**CRITICAL**: Sistema completo documentado pero nunca construido.

---

## Naming Inconsistency

| Docs | Code | Status |
|------|------|--------|
| `.wt/WO-XXXX` | `.worktrees/{wo_id.lower()}` | INCONSISTENT |

---

## Integration Matrix

| Feature | Git Ops | CLI | Workflow | Tmux | Memory |
|---------|---------|-----|----------|------|--------|
| Create worktree | ✅ | ✅ | ❌ | ❌ | ❌ |
| List worktrees | ✅ | ✅ | ❌ | ❌ | ❌ |
| Remove worktree | ✅ | ✅ | ❌ | ❌ | ❌ |
| Auto-create per agent | ❌ | ❌ | ❌ | ❌ | ❌ |
| Memory isolation | ❌ | ❌ | ❌ | ❌ | ❌ |
| Tmux session binding | ❌ | ⚠️ (manual) | ❌ | ❌ | ❌ |

---

## Specific Gaps

### 1. Task.worktree_path Never Populated
```python
# state.py tiene el field:
@dataclass(frozen=True)
class Task:
    worktree_path: str | None = None  # Schema existe

# Pero workflow.py NUNCA lo popula:
task = Task(
    id=task_id,
    slug=slugify(task_description),
    description=task_description,
    # worktree_path no se asigna
)
```

### 2. Workflow --cleanup is Dead Code
```python
# workflow.py:131
def ship(
    cleanup: bool = typer.Option(True, "--cleanup/--no-cleanup"),
) -> None:
    # cleanup is never used!
    # DEBERÍA: if cleanup: clean_worktrees_for_plan(plan_id)
```

### 3. No Workspace-Aware Container
```python
# container.py usa path fijo:
def get_observation_repository(db_path: Path = Path("data/memory.db")):
    # DEBERÍA: db_path = workspace.get_db_path() if workspace else default
```

---

## Recommendations

### Tier 1 - Critical
1. **Auto-create worktrees on agent spawn**: Cuando se lanza un agente, crear worktree automáticamente
2. **Populate Task.worktree_path**: En workflow execute, asignar worktree a cada task

### Tier 2 - Important
3. **Memory isolation per worktree**: DB path diferente por workspace
4. **Implement --cleanup**: Limpiar worktrees al finalizar workflow

### Tier 3 - Enhancement
5. **Build work_O system**: Implementar lo documentado en brain_dope_work_O.md
6. **Orphan detection**: Detectar worktrees huérfanos
7. **Naming standardization**: Unificar convención `.wt` vs `.worktrees`

---

## Files Involved

| Archivo | Propósito |
|---------|-----------|
| `src/infrastructure/platform/git/git_command_executor.py` | Git operations |
| `src/application/services/workspace/workspace_manager.py` | Workspace orchestration |
| `src/application/services/workspace/entities.py` | LayoutType, Workspace, WorktreeState |
| `src/application/services/workspace/workspace_detector.py` | Detection |
| `src/interfaces/cli/workspace_commands.py` | CLI commands |
| `src/application/services/workflow/state.py` | Task.worktree_path (unused) |
| `src/infrastructure/persistence/container.py` | DI (no workspace-aware) |
| `docs/investigacion/brain_dope_work_O.md` | work_O documentation |
