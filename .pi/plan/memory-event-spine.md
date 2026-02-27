# Plan: Memory Event Spine + Hook Integration

**Fecha**: 2026-02-27  
**Estado**: APROBADO - En ejecución  
**Complejidad**: MEDIUM  
**Estimación**: 11-16 horas

---

## Disclaimer Importante

- **FTS5 ≠ Embeddings**: Este sistema usa búsqueda de texto completo (FTS5), NO búsqueda semántica por embeddings.
- **Idempotency dedup lives in DB**: La deduplicación se hace en la base de datos, no en lógica de aplicación.
- **Canonical queries**: El contract de metadata está diseñado para soportar consultas específicas (ver sección 8).

---

## 1) Objetivo

Transformar `memory` de **bitácora pasiva** a **índice activo del sistema**, cerrando la brecha entre:
- Runtime de agentes (tmux-fork)
- Persistencia de observaciones (memory.db)

---

## 2) Decisiones Cerradas

### 2.1 Granularidad del Memory Hook
- **Solo mensajes "importantes"** (selectivo)
- Policy por defecto (hardcoded) + override configurable por workspace
- Criterio por defecto:
  - `important:true` **Y**
  - `message_type ∈ {COMMAND, RESULT, ERROR}`
  - (opcional) `origin ∈ {orchestrator, workflow}`

### 2.2 Retención (TTL) y Cleanup
- **Telemetry**: TTL corto (30-90 días) + cleanup automático
- **Observations**: TTL largo (180-365 días) o manual, con pruning opcional por `event_type` y tamaño
- Usar `CleanupService` existente como mecanismo único

### 2.3 Idempotencia (retry/restart)
- Dedup **en el repositorio / DB**, no en lógica de aplicación
- Estrategia: `idempotency_key` **unique** con `INSERT OR IGNORE` / manejo de `IntegrityError`

### 2.4 Consultas Canónicas (primer set)
- Últimos eventos de `agent_id` (limit + time window)
- Eventos por `session_name` (timeline)
- Fallos por `run_id` / `task_id` (últimos N)
- Ships a main (mode, success/fail, forced)
- `agent_spawned` (quién, pid, session, worktree)

---

## 3) Ajustes Críticos

### A) Contract: Núcleo estable validado
Implementar `MemoryEventMetadata` (Pydantic/TypedDict) con **required keys**:
- `event_type`, `run_id`, `task_id`, `agent_id`, `session_name`, `timestamp_ms`, `mode`, `idempotency_key`
- `extra: dict` para extensibilidad

### B) DB: Punto único de dedup
**Decisión**: Nueva columna `idempotency_key TEXT` en `observations` + `UNIQUE INDEX`

### C) Terminología
En docs/README/plan: siempre "búsqueda de texto completo (FTS5)", NO "semántica"

---

## 4) Fases de Implementación

### FASE 1: Fix Telemetría + Event Contract + Dedup DB
**Estado**: COMPLETADA ✅  
**Duración real**: ~3 horas  
**Prioridad**: HIGH (bloqueante)

**Checklist**:
- [x] Auditar `TelemetryRepositoryImpl` - validar conexión independiente
- [x] Asegurar init explícito del contenedor en CLI y API
- [x] Implementar `MemoryEventMetadata` (Pydantic model)
- [x] Crear migración: agregar columna `idempotency_key` + UNIQUE INDEX
- [x] Implementar `ObservationRepository.save_event()` idempotente
- [x] Agregar `MemoryService.save_event()` con documentación
- [x] Actualizar queries SELECT para incluir `idempotency_key`
- [x] Tests unitarios del contract (16 tests)
- [x] Smoke test de idempotencia validado

**Archivos creados/modificados**:
- `src/application/services/memory/event_metadata.py` (nuevo)
- `src/infrastructure/persistence/migrations/008_add_idempotency_key.sql` (nuevo)
- `src/domain/entities/observation.py` (agregado idempotency_key)
- `src/infrastructure/persistence/repositories/observation_repository.py` (save_event, get_by_idempotency_key)
- `src/application/services/memory_service.py` (save_event)
- `tests/unit/application/services/memory/test_event_metadata.py` (nuevo)

**Criterio de aceptación**: ✅
- Telemetría funcional (no más no-op) - Pendiente validación en uso real
- Contract de metadata validado - 16 tests pasando
- Dedup funciona en DB - Smoke test validado

---

### FASE 2: Event Spine (WorkflowExecutor)
**Estado**: PENDIENTE  
**Duración**: 4-6 horas  
**Prioridad**: HIGH  
**Depende de**: FASE 1

**Checklist**:
- [ ] Modificar `WorkflowExecutor.execute_plan()` para emitir:
  - `agent_spawned` con `session_name`, `pid`, `agent_id`
  - `task_started` / `task_completed` / `task_failed`
- [ ] Actualizar `_record_ship_event()` para usar contract de FASE 1
- [ ] Agregar `idempotency_key: run_id:task_id:event_type:seq`
- [ ] Validar sincronización con `execute-state.json`
- [ ] Tests de integración

**Criterio de aceptación**:
- `memory search "agent_spawned"` devuelve resultados con metadata completa
- No hay duplicados en reinicios

---

### FASE 3: Memory Hook (AgentMessenger)
**Estado**: PENDIENTE  
**Duración**: 3-4 horas  
**Prioridad**: MEDIUM  
**Depende de**: FASE 2  
**Toggle**: OFF por defecto

**Checklist**:
- [ ] Crear `MemoryHookService` con policy de filtrado
- [ ] Integrar hook en `AgentMessenger.send()` y `broadcast()`
- [ ] Implementar dedup por `message.id`
- [ ] Agregar toggle de activación (config por workspace)
- [ ] Tests unitarios e integración

**Criterio de aceptación**:
- Mensajes importantes aparecen en `memory search`
- Mensajes normales NO generan observaciones
- Toggle funciona correctamente

---

### FASE 4: Consultas y UX
**Estado**: PENDIENTE  
**Duración**: 2-3 horas  
**Prioridad**: LOW  
**Depende de**: FASE 2

**Checklist**:
- [ ] Agregar comando `memory query --agent <id> --limit 5`
- [ ] Agregar comando `memory summary --session <id>`
- [ ] Mejorar output de `memory stats` con conteos por tipo
- [ ] Documentar queries canónicas

**Criterio de aceptación**:
- Queries comunes funcionan con flags simples
- Output legible y útil

---

## 5) Archivos a Modificar

### Nuevos archivos
- `src/application/services/memory/event_metadata.py` (contract)
- `src/application/services/memory/memory_hook_service.py` (hook)
- `src/infrastructure/persistence/migrations/006_add_idempotency_key.sql`

### Modificaciones
- `src/infrastructure/persistence/container.py` (init telemetría)
- `src/infrastructure/persistence/repositories/observation_repository.py` (save_event)
- `src/application/services/workflow/executor.py` (event spine)
- `src/application/services/messaging/agent_messenger.py` (hook)
- `src/interfaces/cli/commands/workflow.py` (usar contract)
- `src/interfaces/cli/commands/memory.py` (nuevos comandos)

### Tests
- `tests/unit/application/services/memory/test_event_metadata.py`
- `tests/unit/application/services/memory/test_memory_hook_service.py`
- `tests/integration/test_memory_event_spine.py`

---

## 6) Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Ruido excesivo en memory.db | Media | Medio | Policy estricta + toggle OFF |
| Breaking change en CLI | Baja | Alto | Retrocompatibilidad, flags opcionales |
| Duplicados en reinicios | Media | Bajo | Idempotency keys + dedup en DB |
| Performance degrada | Baja | Medio | TTL + cleanup, índices existentes |
| Telemetría sigue en 0 | Baja | Alto | Validar en FASE 1 |

---

## 7) Toggles (Política Final)

- **Event Spine**: ON por defecto (esqueleto del sistema)
- **Memory Hook**: OFF por defecto + config por workspace

---

## 8) Contract de Metadata (Schema)

```python
class MemoryEventMetadata(BaseModel):
    # Required keys (núcleo estable)
    event_type: str           # agent_spawned, task_started, ship_completed, etc.
    run_id: str               # UUID del run actual
    task_id: str              # ID de la tarea (WO-XXXX o similar)
    agent_id: str             # ID del agente (session:window)
    session_name: str         # Nombre de sesión tmux
    timestamp_ms: int         # Unix timestamp en ms
    mode: str                 # worktree | inplace | checkout
    idempotency_key: str      # run_id:task_id:event_type:seq
    
    # Extensibilidad
    extra: dict = Field(default_factory=dict)
    
    model_config = {"extra": "allow"}
```

---

## 9) Validación de Progreso

### Al final de FASE 1:
```bash
# Telemetría funciona
memory stats

# Contract validado
memory save "test" --metadata '{"event_type":"test","run_id":"r1","task_id":"t1","agent_id":"a1","session_name":"s1","timestamp_ms":123,"mode":"test","idempotency_key":"r1:t1:test:1"}'

# Dedup funciona (no duplica)
memory save "test" --metadata '{"event_type":"test","run_id":"r1","task_id":"t1","agent_id":"a1","session_name":"s1","timestamp_ms":123,"mode":"test","idempotency_key":"r1:t1:test:1"}'
```

### Al final de FASE 2:
```bash
memory workflow execute "test task"
memory search "agent_spawned"
```

### Al final de FASE 3:
```bash
# (enviar mensaje importante)
memory search "important:true"
```

---

## 10) Historial de Cambios

- **2026-02-27**: Plan aprobado con decisiones cerradas
- **2026-02-27**: Inicio FASE 1
