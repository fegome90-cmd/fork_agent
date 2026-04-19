# Checklist: memory-refactor (SPRINT COMPLETO)

Plan ejecutado: `.pi/checkpoints/memory-refactor-plan.md`

## ✅ FASE 1: MemoryEventMetadata Contract + Idempotency
- [x] Implementado MemoryEventMetadata con Pydantic (16 tests)
- [x] Migración 008 con idempotency_key UNIQUE INDEX
- [x] ObservationRepository.save_event() idempotente
- [x] Entity Observation actualizada con idempotency_key
- [x] 35 tests repositorio/servicio

## ✅ FASE 1.5: Telemetría Integration
- [x] MemoryService + TelemetryService conectados
- [x] CLI inicializa sesión y flushea eventos
- [x] `memory stats --telemetry` funcional
- [x] 5 tests de integración

## ✅ FASE 2: Event Spine en WorkflowExecutor
- [x] Helper central `_emit_event()` sin duplicación
- [x] Eventos: task_started, agent_spawned, task_completed/failed, ship_started/completed/failed
- [x] Metadata completa + sanitización de paths
- [x] Invariante terminal events validado
- [x] 12 tests de integración (9 base + 3 sanity checks)

## ✅ FASE 3: Memory Hook (AgentMessenger) - MVP
- [x] **Toggle OFF por defecto** ✅
- [x] **Policy estricta**: important=true + tipos {COMMAND, REPLY, HANDOFF} ✅
- [x] **Rate-limit**: 30/min por (run_id, task_id, agent_id, message_type) ✅
- [x] **Truncation**: 4KB max + payload_truncated metadata ✅
- [x] **Dedup por message_id**: idempotency_key con message_id ✅
- [x] MemoryHookConfig con gates configurables
- [x] RateLimiter con sliding window
- [x] 14 tests unitarios (todos los gates)
- [x] 4 tests de integración (toggle ON/OFF, retry, broadcast)

## DoD FASE 3 cumplido
- [x] Toggle OFF por defecto (validado en test)
- [x] Policy: important=false → no capture (validado en test)
- [x] Policy: type no permitido → no capture (validado en test)
- [x] Rate-limit: N+1 en ventana → drop (validado en test)
- [x] Truncation: payload > limit → truncated + metadata (validado en test)
- [x] Dedup: mismo message_id → no duplica (validado en test)
- [x] Integration: toggle OFF → 0 observations (validado en test)
- [x] Integration: toggle ON + important → 1 observation con metadata completa (validado)
- [x] Integration: retry mismo message_id → sigue siendo 1 (validado)

## Métricas Finales
- **Total tests**: 77 (FASE 1-2) + 18 (FASE 3) = **95 tests**
- **Tests FASE 3**: 14 unitarios + 4 integración = 18 tests
- **Cobertura de gates**: 100% (toggle, policy, rate-limit, truncation, dedup)

## Próximo Sprint: FASE 4 (UX) - MVP
Solo 2 comandos que cubren el 80%:

### 1. `memory query --agent <id> --limit N`
- Filtra por `metadata.agent_id == <id>` o `metadata.extra.from_agent_id == <id>`
- Output: timestamp + event_type + resumen corto + run_id/task_id

### 2. `memory timeline --run <run_id>`
- Ordenado por timestamp
- Muestra event_type + agent/session + success/error (redacted)

## No incluir (próximo sprint)
- Pretty printing complejo
- Dashboard interactivo
- Más comandos de query

## Arquitectura Final
```
┌─────────────────────────────────────────────┐
│         Memory System (Event Spine)         │
├─────────────────────────────────────────────┤
│ • MemoryEventMetadata contract (Pydantic)   │
│ • Idempotency by idempotency_key            │
│ • Telemetry integration                     │
│ • Event emission from WorkflowExecutor      │
│ • Memory Hook with gates                    │
│   - Toggle OFF by default                   │
│   - Policy: important + types               │
│   - Rate-limit: 30/min                      │
│   - Truncation: 4KB                         │
│   - Dedup by message_id                     │
└─────────────────────────────────────────────┘
```

## Siguiente sesión
1. Reanudar con: `/checkpoint goto memory-refactor`
2. Prioridad: FASE 4 - UX MVP (2 comandos)
3. `memory query --agent <id> --limit N`
4. `memory timeline --run <run_id>`
