# Checklist: memory-refactor

Plan ejecutado: usa el path del agente

## Pendientes
- [ ] Modificar WorkflowExecutor para emitir eventos con MemoryEventMetadata contract (FASE 2)
- [ ] Actualizar _record_ship_event() para usar create_event_metadata() con tipos EventType
- [ ] Agregar emisión de eventos AGENT_SPAWNED, TASK_STARTED, TASK_COMPLETED, TASK_FAILED en flujos workflow

## Verificación
- [ ] Build/Types/Lint/Test según aplique
- [ ] Revisar riesgos y regresiones
