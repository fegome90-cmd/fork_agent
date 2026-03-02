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

## Pendientes

### FASE 2: Event Spine desde WorkflowExecutor (MVP)
- [ ] Modificar WorkflowExecutor para emitir eventos con MemoryEventMetadata contract
- [ ] Actualizar _record_ship_event() para usar create_event_metadata() con tipos EventType
- [ ] Agregar emisión de eventos AGENT_SPAWNED, TASK_STARTED, TASK_COMPLETED, TASK_FAILED
- [ ] Integration test: workflow mínimo genera eventos con metadata completa
- [ ] Verificar sincronía con execute-state.json (solo verificación, no reemplazo)

## Verificación
- [x] Build/Types/Lint/Test según aplique
- [x] 5/5 tests integración telemetría pasando
- [x] 12/12 tests unitarios MemoryService pasando
- [x] Smoke test CLI confirma telemetría > 0

## Siguiente sesión
1. Reanudar con: `/checkpoint goto memory-refactor`
2. Prioridad: FASE 2 MVP - Event Spine desde WorkflowExecutor
