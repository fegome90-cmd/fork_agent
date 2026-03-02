# Checklist: memory-refactor (FINAL)

Plan ejecutado: `.pi/checkpoints/memory-refactor-plan.md`

## ✅ COMPLETADO

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

### FASE 2: Event Spine desde WorkflowExecutor (MVP)
- [x] Helper central `_emit_event()` con MemoryEventMetadata contract
- [x] execute_task() emite: task_started, agent_spawned, task_completed/task_failed
- [x] cleanup_worktree() emite: ship_started, ship_completed, ship_failed
- [x] Todos los eventos con required fields
- [x] Ship events incluyen target_branch + mode
- [x] 9 tests de integración Event Spine pasando

### Checks de Sanidad (Agregados)
- [x] **Invariante terminal events**: Para cada (run_id, task_id) existe EXACTAMENTE UNO: task_completed O task_failed
- [x] **No leakage de paths sensibles**: error_message sanitizado (reemplaza /Users/*/ y /home/*/ con <redacted>/) salvo DEBUG=1
- [x] 3 tests nuevos: invariantes + privacidad

## DoD FASE 2 (no negociable)
- [x] `memory search "agent_spawned"` devuelve entries con metadata completa
- [x] retry/restart no duplica (validado por test)
- [x] ship events incluyen `target_branch` + `mode`
- [x] 1 helper central de emisión (sin duplicación de metadata building)
- [x] Terminal events invariant validado
- [x] Privacy sanitization implementado

## Verificación Final
- [x] 5/5 tests integración telemetría
- [x] 12/12 tests integración Event Spine (incluye invariantes + privacidad)
- [x] 12/12 tests unitarios MemoryService
- [x] 48/48 tests unitarios WorkflowExecutor
- [x] Smoke test CLI confirma eventos con metadata completa
- [x] Telemetría > 0 comprobado

**Total: 77 tests pasando**

## Próximo Sprint (FASE 3 primero, luego FASE 4)

### FASE 3: Memory Hook (AgentMessenger) - MVP
- [ ] Capturar solo `important:true` + tipos `{COMMAND, RESULT, ERROR}`
- [ ] Guardar `agent_message` con metadata: from_agent/to_agent, run_id/task_id, session_name
- [ ] Dedup por message_id
- [ ] Toggle workspace config (OFF por defecto)
- [ ] Policy estricta + rate-limit + truncation

### FASE 4: UX - MVP
- [ ] `memory query --agent <id> --limit N`
- [ ] `memory timeline --run <run_id>`

## Notas
- Base durísima para iterar: contract + dedup + telemetría + spine + invariantes
- Hook primero, UX después (sin Hook, UX solo ve eventos del executor)
- Gates desde día 1 en FASE 3: toggle OFF, policy, rate-limit, truncation, dedup
