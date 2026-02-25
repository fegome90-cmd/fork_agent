# Integration Matrix - Cross-System Analysis

> **Generated**: 2026-02-25 | **Scope**: Cross-system integration in fork_agent

## Executive Summary

fork_agent tiene **5 subsistemas bien implementados individualmente** pero **NO están integrados entre sí**. Cada uno opera de forma aislada. No existe una capa de orquestación unificada. Los "wiring points" documentados en skills/ no tienen código que los conecte.

---

## Subsystems Overview

| Subsystem | Core Files | Implementation | Integration |
|-----------|------------|----------------|-------------|
| **Workflow** | `workflow/state.py`, `commands/workflow.py` | ⚠️ STUB | ❌ ISOLATED |
| **Tmux** | `tmux_orchestrator/`, `agent_manager.py` | ✅ FULL | ❌ ISOLATED |
| **Memory** | `memory_service.py`, `observation_repository.py` | ✅ FULL | ❌ ISOLATED |
| **Worktrees** | `workspace_manager.py`, `git_command_executor.py` | ✅ FULL | ❌ ISOLATED |
| **Hooks** | `hook_service.py`, `.hooks/` | ⚠️ HEADLESS | ❌ NOT DISPATCHED |

---

## Integration Matrix

| From → To | Workflow | Tmux | Memory | Worktrees | Hooks |
|-----------|----------|------|--------|-----------|-------|
| **Workflow** | — | ❌ | ❌ | ❌ | ❌ |
| **Tmux** | ❌ | — | ❌ | ❌ | ⚠️ (via hooks) |
| **Memory** | ❌ | ❌ | — | ❌ | ❌ |
| **Worktrees** | ❌ | ⚠️ (enter) | ❌ | — | ⚠️ (hooks) |
| **Hooks** | ❌ | ❌ | ❌ | ❌ | — |

Legend:
- ✅ = Fully integrated
- ⚠️ = Partial integration
- ❌ = No integration

---

## Detailed Integration Analysis

### 1. Workflow → Memory

| Expected | Actual | Status |
|----------|--------|--------|
| Save plan as observation | Saves to `.claude/plans/plan.md` | ❌ |
| Track execution history in memory | No MemoryService calls | ❌ |
| Searchable workflow history | Not implemented | ❌ |

**Gap**: `workflow.py` no importa ni usa `MemoryService`.

### 2. Workflow → Tmux

| Expected | Actual | Status |
|----------|--------|--------|
| `execute` spawns tmux sessions | Only updates JSON state | ❌ |
| Task → Session mapping | Not tracked | ❌ |
| Parallel task execution | `--parallel` flag ignored | ❌ |

**Gap**: `TmuxOrchestrator` existe pero no es llamado desde workflow.

### 3. Workflow → Hooks

| Expected | Actual | Status |
|----------|--------|--------|
| Dispatch on phase change | No dispatch calls | ❌ |
| Workflow events in hooks.json | Not configured | ❌ |
| HookService usage | Never imported | ❌ |

**Gap**: `HookService` existe, `hooks.json` existe, pero nunca se conectan.

### 4. Workflow → Worktrees

| Expected | Actual | Status |
|----------|--------|--------|
| Create worktree per task | Manual only | ❌ |
| `Task.worktree_path` populated | Field exists, never used | ❌ |
| Auto-cleanup on ship | `--cleanup` flag is dead code | ❌ |

**Gap**: Schema soporta worktrees, implementación no.

### 5. Tmux → Memory

| Expected | Actual | Status |
|----------|--------|--------|
| Session state in memory | File-based traces | ❌ |
| Agent output stored | Not captured | ❌ |
| Searchable session history | Not implemented | ❌ |

**Gap**: `memory-trace-writer.sh` escribe a archivos, no a DB.

### 6. Worktrees → Memory

| Expected | Actual | Status |
|----------|--------|--------|
| Per-worktree DB | Single SQLite | ❌ |
| Workspace-isolated observations | Shared globally | ❌ |
| Context per workspace | Not implemented | ❌ |

**Gap**: `container.py` usa path fijo, no workspace-aware.

### 7. Hooks → Everything

| Expected | Actual | Status |
|----------|--------|--------|
| Events dispatched on actions | NEVER DISPATCHED | ❌ |
| Hook scripts triggered | Configured but not invoked | ❌ |
| Cross-system coordination | No orchestration | ❌ |

**CRITICAL**: Todo el sistema de hooks es "headless".

---

## Documented vs Implemented

### From `.claude/skills/fork_terminal/`

| Documented Feature | Implemented | Gap |
|--------------------|-------------|-----|
| Tmux session per agent (SubagentStart) | ⚠️ Script exists | Not triggered |
| Memory trace on SubagentStop | ⚠️ Script exists | Writes to file, not DB |
| Workflow state persistence | ⚠️ JSON files | Not in memory system |
| Worktrees per task | ❌ Schema only | Not auto-created |
| Workspace memory isolation | ❌ | Single DB |
| cm-save/cm-load | ❌ Documented | Not implemented |

### From `AGENTS.md`

| Documented Feature | Implemented | Gap |
|--------------------|-------------|-----|
| "Hooks de Integración" | ⚠️ Scripts exist | Events not dispatched |
| "fork_terminal" bifurcación | ⚠️ Partial | Not wired to workflow |
| Session checkpoint procedure | ⚠️ /fork-checkpoint | cm-save missing |

---

## Unified Orchestration Layer

### What's Missing

```
┌───────────────────────────────────────────────────────────────┐
│                    MISSING: Orchestrator                      │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐      │
│   │Workflow │   │  Tmux   │   │ Memory  │   │Worktree │      │
│   │ Service │   │Orchestr.│   │ Service │   │ Manager │      │
│   └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘      │
│        │             │             │             │            │
│        └─────────────┴──────┬──────┴─────────────┘            │
│                             │                                 │
│                    ┌────────▼────────┐                       │
│                    │   Orchestrator  │ ← DOES NOT EXIST       │
│                    │   - Coordinate  │                       │
│                    │   - Wire        │                       │
│                    │   - Dispatch    │                       │
│                    └─────────────────┘                       │
│                             │                                 │
│                    ┌────────▼────────┐                       │
│                    │   HookService   │ ← EXISTS, NOT USED    │
│                    └─────────────────┘                       │
└───────────────────────────────────────────────────────────────┘
```

### Proposed Orchestrator Responsibilities

1. **Coordinate workflow → tmux**: Spawn sessions for tasks
2. **Coordinate workflow → memory**: Save observations on phase change
3. **Coordinate workflow → worktrees**: Create/cleanup per task
4. **Dispatch hooks**: On all state changes
5. **Track cross-system state**: Unified view

---

## Biggest Integration Gaps (Priority Order)

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| 1 | Hook dispatch (wire HookService) | LOW | HIGH |
| 2 | Workflow → Hooks (phase events) | MEDIUM | HIGH |
| 3 | Workflow → Tmux (spawn agents) | MEDIUM | HIGH |
| 4 | Memory isolation per worktree | MEDIUM | MEDIUM |
| 5 | Unified Orchestrator class | HIGH | HIGH |

---

## Recommendations

### Phase 1: Quick Wins (1-2 days)
1. Wire `HookService.dispatch()` to CLI entrypoint
2. Add workflow phase events to hooks.json
3. Dispatch events in workflow.py

### Phase 2: Core Integration (1 week)
4. Connect workflow execute → TmuxOrchestrator
5. Connect workflow → MemoryService for history
6. Populate `Task.worktree_path` in workflow

### Phase 3: Full Orchestration (2 weeks)
7. Build unified `Orchestrator` class
8. Implement workspace-aware memory isolation
9. Build cm-save/cm-load functionality

---

## Files Involved

| Archivo | Propósito |
|---------|-----------|
| `src/application/services/workflow/state.py` | Workflow state |
| `src/interfaces/cli/commands/workflow.py` | Workflow CLI |
| `src/application/services/memory_service.py` | Memory service |
| `src/infrastructure/tmux_orchestrator/__init__.py` | Tmux orchestrator |
| `src/application/services/agent/agent_manager.py` | Agent management |
| `src/application/services/workspace/workspace_manager.py` | Worktree management |
| `src/application/services/orchestration/hook_service.py` | Hook service |
| `src/infrastructure/persistence/container.py` | DI container |
