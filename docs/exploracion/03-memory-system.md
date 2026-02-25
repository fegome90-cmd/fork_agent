# Memory System - Gap Analysis

> **Generated**: 2026-02-25 | **Scope**: Observation/memory management for AI agents

## Executive Summary

El sistema de memoria tiene **CRUD completo implementado** (save/search/list/get/delete) con FTS5 search. Sin embargo, **NO hay integración** con workflow, hooks, ni worktrees. El feature `cm-save/cm-load` está **documentado pero NO implementado**.

---

## Implementation Status

### Core CRUD Operations

| Feature | CLI | Service | Repository | Status |
|---------|-----|---------|------------|--------|
| Save observation | `memory save` | `MemoryService.save()` | `create()` | ✅ FULL |
| Search observations | `memory search` | `MemoryService.search()` | `search()` FTS5 | ✅ FULL |
| List observations | `memory list` | `MemoryService.get_recent()` | `get_all()` | ✅ FULL |
| Get by ID | `memory get <id>` | `MemoryService.get_by_id()` | `get_by_id()` | ✅ FULL |
| Delete observation | `memory delete <id>` | `MemoryService.delete()` | `delete()` | ✅ FULL |
| **Update observation** | ❌ N/A | ❌ NOT EXPOSED | `update()` exists | ❌ MISSING |
| Get by time range | ❌ N/A | `get_by_time_range()` | `get_by_timestamp_range()` | ⚠️ SERVICE ONLY |

### Domain Entity: Observation

| Field | Status | Notes |
|-------|--------|-------|
| `id` | ✅ | UUID string |
| `timestamp` | ✅ | Unix milliseconds |
| `content` | ✅ | Main text |
| `metadata` | ✅ | Optional dict |
| **context-memory-id** | ❌ MISSING | No field for context linkage |

---

## Integration Gaps

### Workflow Integration

| Feature | Status | Gap |
|---------|--------|-----|
| Workflow saves to memory | ❌ MISSING | `workflow/state.py` no importa MemoryService |
| Auto-save plan to memory | ❌ MISSING | Solo guarda a `.claude/plans/plan.md` |
| Context-memory-id tracking | ❌ MISSING | No implementado en Observation entity |
| Session-context persistence | ❌ MISSING | Sin integración workflow ↔ memory |

### Hooks Integration

| Hook | Current Behavior | Status |
|------|------------------|--------|
| `memory-trace-writer.sh` | Escribe a `.claude/traces/current-trace.json` | ⚠️ FILE, NOT DB |

**PROBLEMA**: El hook escribe traces a archivos JSON, NO a la base de datos de observaciones. No se pueden buscar via `memory search`.

### Workspace/Worktree Integration

| Feature | Status | Gap |
|---------|--------|-----|
| Per-worktree memory | ❌ MISSING | Single SQLite DB |
| Workspace isolation | ❌ MISSING | No DB path por workspace |
| Context per workspace | ❌ MISSING | Compartido globalmente |

---

## cm-save / cm-load (Session Checkpoint)

### Documentado en AGENTS.md:
> "Al finalizar la sesión, SIEMPRE ejecutar en PARALELO:
> /fork-checkpoint
> cm-save <nombre-sesion>"

### Implementación Real:

| Feature | Documentado | Implementado | Status |
|---------|-------------|--------------|--------|
| `/cm-save <name>` | ✅ AGENTS.md | ❌ NO CODE | ❌ MISSING |
| `/cm-load <name>` | ✅ RUNBOOK.md | ❌ NO CODE | ❌ MISSING |
| Context serialization | ✅ Documentado | ❌ NO CODE | ❌ MISSING |
| Context rehydration | ✅ Documentado | ❌ NO CODE | ❌ MISSING |

**Este es un GAP CRÍTICO** - Feature documentado pero sin implementación.

---

## Test Coverage

| Area | Unit Tests | Integration | E2E | Status |
|------|------------|-------------|-----|--------|
| MemoryService | ✅ test_memory_service.py | ❌ | ❌ | ⚠️ COVERED |
| Observation Repository | ✅ test_observation_repository.py | ❌ | ❌ | ⚠️ COVERED |
| CLI Commands | ✅ test_save, test_search, etc. | ❌ | ❌ | ⚠️ COVERED |
| Workflow + Memory | ❌ | ❌ | ❌ | ❌ MISSING |
| Hooks + Memory | ❌ | ❌ | ❌ | ❌ MISSING |

---

## Specific Gaps

### 1. Update Operation Missing
```python
# Repository tiene update():
def update(self, observation: Observation) -> Observation:
    ...

# Pero MemoryService NO lo expone
class MemoryService:
    def save(self, content: str, ...) -> Observation:  # ✅
    def search(self, query: str, ...) -> list[Observation]:  # ✅
    def get_by_id(self, observation_id: str) -> Observation | None:  # ✅
    def delete(self, observation_id: str) -> bool:  # ✅
    # update() - MISSING
```

### 2. Memory Trace Hook → File, Not DB
```bash
# .hooks/memory-trace-writer.sh
# Escribe a: .claude/traces/current-trace.json
# DEBERÍA: Llamar `memory save` o usar MemoryService
```

### 3. No CLI for Time Range Query
```python
# Service tiene el método:
def get_by_time_range(self, start_ms: int, end_ms: int) -> list[Observation]:
    ...

# Pero no hay comando CLI:
# memory list --from 2024-01-01 --to 2024-12-31  # NO EXISTE
```

---

## Recommendations

### Tier 1 - Critical
1. **Implementar cm-save/cm-load**: Serializar contexto completo (memory + workflow state + config)
2. **Conectar memory-trace-writer a DB**: Usar MemoryService, no archivos

### Tier 2 - Important
3. **Workflow → Memory integration**: Guardar observations en cada fase del workflow
4. **Add update operation**: Exponer `update()` via CLI

### Tier 3 - Enhancement
5. **Per-worktree memory isolation**: DB path por workspace
6. **CLI for time range**: `memory list --from --to`

---

## Files Involved

| Archivo | Propósito |
|---------|-----------|
| `src/application/services/memory_service.py` | Core service |
| `src/interfaces/cli/commands/save.py` | CLI save |
| `src/interfaces/cli/commands/search.py` | CLI search |
| `src/interfaces/cli/commands/list.py` | CLI list |
| `src/interfaces/cli/commands/get.py` | CLI get |
| `src/interfaces/cli/commands/delete.py` | CLI delete |
| `src/infrastructure/persistence/repositories/observation_repository.py` | SQLite + FTS5 |
| `.hooks/memory-trace-writer.sh` | Trace hook (file-based) |
| `AGENTS.md` | cm-save/cm-load documentation |
