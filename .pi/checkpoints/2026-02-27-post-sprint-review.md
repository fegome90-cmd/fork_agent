# Post-Sprint Review: memory-refactor (FASE 1-4)

**Fecha**: 2026-02-27
**Sprint**: memory-refactor completo (FASE 1-4)
**Estado**: ✅ Línea base de plataforma operable

---

## ✅ Lo que quedó impecable (y por qué)

### 1. Contract + Idempotency en DB
- **Decisión**: MemoryEventMetadata con Pydantic + UNIQUE INDEX en idempotency_key
- **Valor**: Cualquier retry es un no-op seguro. Diferencia entre "logs" y "sistema"
- **Tests**: 35 tests de contract + idempotency

### 2. Telemetría viva + flush
- **Decisión**: MemoryService + TelemetryService conectados, CLI flushea al finalizar
- **Valor**: Diagnóstico no ciego. Monitoreo de deriva de uso y ruido
- **Tests**: 5 tests de integración

### 3. Event spine centralizado
- **Decisión**: `_emit_event()` como SSOT para emisión en WorkflowExecutor
- **Valor**: Evita fragmentación del proyecto. Punto único de control
- **Tests**: 12 tests (9 base + 3 sanity checks)

### 4. Hook con gates (toggle/rate/trunc/dedup)
- **Decisión**: Toggle OFF + policy + rate-limit + truncation + dedup
- **Valor**: Barrera que evita que memory.db se convierta en chatlog infinito
- **Tests**: 18 tests (14 unit + 4 integration)

### 5. UX MVP con consultas estructuradas + scan-limit
- **Decisión**: FTS para "search", SQL+filtro para "query/timeline"
- **Valor**: Estabilidad. Evita drift de formato
- **Tests**: 10 tests (5 query + 5 timeline)

---

## ⚠️ 4 Riesgos Reales (Post-Sprint) a Vigilar

### 1. Fragmentación por worktree DB (producto, no bug)

**Problema**: ¿Estoy consultando la DB correcta? (repo-level vs worktree-level)

**Mitigación mínima (sin re-arquitectura)**:
- [ ] En `memory stats` y `memory query` imprimir siempre:
  - `db_path` resuelto
  - `workspace_mode` (repo/worktree)
- [ ] Agregar flag `--repo-db` / `--worktree-db` (próximo sprint)

**Prioridad**: Alta (UX confusion)

### 2. Colisiones de `message_id` en broadcast

**Problema**: En broadcast, mismo `message_id` para múltiples receptores puede pisar mensajes distintos

**Idempotency key actual**: `run_id:task_id:agent_message:{message_id}`

**Mitigación**:
- [ ] Cambiar idempotency key a: `run_id:task_id:agent_message:{from_agent}:{to_agent or '*'}:{message_id}`
- [ ] Esto evita colisiones entre destinatarios

**Prioridad**: Media (raro pero catastrófico)

### 3. Rate limiter in-memory vs multi-process

**Problema**: Si hay múltiples procesos/instancias del messenger, rate-limit in-memory no es global

**Mitigación MVP**:
- [x] Dejar así (está bien para MVP)
- [ ] Medir drops por proceso con telemetría
- [ ] Si se vuelve problema, migrar limiter a SQLite (más adelante)

**Prioridad**: Baja (aceptable para MVP)

### 4. "100% coverage" ≠ resistencia a caos

**Problema**: Tests están buenos, pero el sistema real falla en:
- Crashes entre `worktree add` y `remove`
- Merges con conflictos
- DB locked en carga alta

**Mitigación**:
- [ ] Test "chaos-lite" (próximo sprint):
  - Forzar exceptions en puntos aleatorios
  - Verificar:
    - Cleanup worktree
    - No duplicados
    - Invariantes terminal events no se rompen

**Prioridad**: Media (robustez)

---

## 📌 Próximo Sprint Correcto: FASE 5 — Consolidación y Navegación de Memoria

**Objetivo**: Que el sistema "aprenda" **globalmente** y sea fácil encontrar "lo importante"

### 5.1 Promote entre worktree → repo-level (mínimo viable)

**Problema**: Memoria aislada que nunca se consolida

**Solución**: En `ship_completed` (o al cerrar WO), promover:
- `summary`, `decision`, `discovery`, `result` importantes

**Con provenance**:
- `source_worktree`, `source_branch`, `promoted_at`, `run_id/task_id`

**Entregable**:
- [ ] Comando `memory promote` o automático en ship
- [ ] Migración para tabla `promoted_observations`
- [ ] Tests de promote con provenance

**Valor**: Memoria global reutilizable

### 5.2 Compaction "por run/task" (sin embeddings)

**Problema**: Eventos individuales no dan contexto

**Solución**: Al cerrar `task_completed/failed`:
- [ ] Crear `summary` canónica (5–10 líneas)
- [ ] Linkear a evidencia (`logs`, `artifacts`, `payload_ref`)

**Entregable**:
- [ ] Servicio `CompactionService`
- [ ] Trigger en `task_completed/failed`
- [ ] Tests de compaction

**Valor**: Contexto condensado + links a evidencia

### 5.3 Queries UX pequeñas pero de alto impacto

**Sin inflar comandos**:

- [ ] `memory promote status` (qué está local vs global)
- [ ] `memory summary --task <id>` (recupera la summary canónica)

**Valor**: Navegación de memoria consolidada

---

## Arquitectura Post-FASE 5 (Visión)

```
┌─────────────────────────────────────────────┐
│         Memory System (Knowledge Base)      │
├─────────────────────────────────────────────┤
│ FASE 1-4: ✅ Operable                       │
│ • Contract + idempotency                    │
│ • Telemetry                                 │
│ • Event spine                               │
│ • Hook con gates                            │
│ • UX MVP                                    │
├─────────────────────────────────────────────┤
│ FASE 5: Consolidation & Navigation          │
│ • Promote worktree → repo                   │
│ • Compaction por run/task                   │
│ • Queries de memoria consolidada            │
│ • Provenance tracking                       │
└─────────────────────────────────────────────┘
```

---

## Métricas Finales FASE 1-4

**Tests creados**: **105 tests**
- Integration: 31 tests
- Unit: 26 tests
- FASE 1-2: 77 tests
- FASE 3: 18 tests
- FASE 4: 10 tests

**Cobertura**:
- Contract + dedup: 100%
- Telemetría: 100%
- Event Spine: 100%
- Memory Hook gates: 100%
- UX commands: 100%

**Líneas de código**: ~2100 líneas nuevas (16 archivos)

---

## Lecciones Aprendidas

### ✅ Lo que funcionó

1. **Briefing cerrado + DoD explícito**: Cada fase tuvo scope quirúrgico y DoD no negociable
2. **Tests primero**: 105 tests dan confianza para refactor
3. **Naming canónico**: Corregir inconsistencias ANTES de implementar UX
4. **Consultas estructuradas**: LIMIT K + Python filter > FTS para queries estructuradas
5. **Gates desde día 1**: Toggle OFF + policy + rate-limit + truncation + dedup

### ⚠️ Lo que mejorar

1. **Considerar multi-process antes**: Rate limiter in-memory no es global
2. **Pensar en broadcast desde el inicio**: Colisiones de message_id
3. **Chaos testing**: 100% coverage ≠ resistencia a caos

---

## Veredicto Final

✅ **Plataforma operable sin vergüenza**

⚠️ **Riesgo**: Memoria local que nunca se consolida (worktree isolation)

📌 **Próximo paso**: FASE 5 (promote + compaction) para convertir "observabilidad útil" en "conocimiento reutilizable"

**Solo después de FASE 5** vale la pena hablar de:
- Búsqueda híbrida
- Writeback sofisticado
- Embeddings

---

## Checklist para FASE 5

- [ ] Mitigar riesgo 1: `db_path` + `workspace_mode` en output
- [ ] Mitigar riesgo 2: idempotency key con from_agent + to_agent
- [ ] Diseñar migración para `promoted_observations`
- [ ] Implementar `CompactionService`
- [ ] Tests de chaos-lite
- [ ] Comandos: `memory promote status`, `memory summary --task`

**Tiempo estimado**: 1 sprint completo
