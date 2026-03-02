# Checklist: memory-refactor

Plan ejecutado: `.pi/checkpoints/memory-refactor-plan.md`

## Completado

### FASE 1: MemoryEventMetadata Contract + Idempotency
- [x] Implementado MemoryEventMetadata con Pydantic (16 tests)
- [x] Migración 008 con idempotency_key UNIQUE INDEX
- [x] ObservationRepository.save_event() idempotente
- [x] Entity Observation actualizada con idempotency_key
- [x] Repositorio con get_by_idempotency_key()
- [x] MemoryService.save_event() documentado
- [x] 35 tests repositorio/servicio + smoke test idempotencia

### FASE 1.5: Telemetría Integration
- [x] MemoryService inyecta TelemetryService (opcional)
- [x] MemoryService.save/search/delete trackean eventos de telemetría
- [x] CLI inicializa sesión de telemetría en callback
- [x] `memory stats --telemetry` muestra conteos de eventos
- [x] `memory telemetry status` respeta --db path
- [x] CLI commands flushean telemetría al finalizar
- [x] 5 tests de integración de telemetría pasando
- [x] Smoke test: `memory save/search` + `telemetry status` muestra eventos

### FASE 2: Event Spine desde WorkflowExecutor (MVP)
- [x] Helper central `_emit_event()` con MemoryEventMetadata contract
- [x] execute_task() emite: task_started, agent_spawned, task_completed/task_failed
- [x] cleanup_worktree() emite: ship_started, ship_completed, ship_failed
- [x] Todos los eventos con required fields: run_id, task_id, agent_id, session_name, mode, idempotency_key
- [x] Ship events incluyen target_branch + mode
- [x] 9 tests de integración Event Spine pasando
- [x] Smoke test: `memory search "agent_spawned"` devuelve metadata completa

## DoD FASE 2 (no negociable)
- [x] `memory search "agent_spawned"` devuelve entries con metadata completa
- [x] retry/restart no duplica (validado por test)
- [x] ship events incluyen `target_branch` + `mode`
- [x] 1 helper central de emisión (sin duplicación de metadata building)

## Verificación
- [x] Build/Types/Lint/Test según aplique
- [x] 5/5 tests integración telemetría pasando
- [x] 12/12 tests unitarios MemoryService pasando
- [x] 9/9 tests integración Event Spine pasando
- [x] 48/48 tests unitarios WorkflowExecutor pasando
- [x] Smoke test CLI confirma eventos con metadata completa

## Pendientes (próximo sprint)
- [ ] FASE 3: Memory Hook (AgentMessenger)
- [ ] FASE 4: UX / queries avanzadas
- [ ] Promote entre worktrees + compaction "bonita"

## Siguiente sesión
1. Reanudar con: `/checkpoint goto memory-refactor`
2. Prioridad: FASE 3 - Memory Hook para AgentMessenger
3. Alternativa: UX improvements (queries avanzadas, dashboard)
