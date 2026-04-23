# Memory System Evolution

Este documento registra la evolución del sistema de memoria de `tmux_fork`, su alineación con el estándar `engram` de `gentle-ai` y los hallazgos de las auditorías multi-agente.

## Estado Inicial (Pre-2026-04-16)
- Entidad `Observation` básica (id, timestamp, content, metadata).
- `MemoryService.save()` realizaba únicamente inserciones (cada guardado generaba un nuevo UUID).
- Búsqueda por FTS5 funcional pero sin filtros estructurales.
- Listado truncado a 8 caracteres, insuficiente para unicidad visual y sin soporte para recuperación por prefijo.

## Sprint 1: Foundation & Upsert (Completado 2026-04-16)

### Cambios Realizados
1. **Upsert por `topic_key` (P0)**:
   - Se añadió el campo `topic_key` a la entidad `Observation`.
   - **Migración 009**: Columna `topic_key` con índice único parcial.
   - `MemoryService.save()` ahora detecta `topic_key` en metadata y realiza un `update` si ya existe, preservando el UUID original.
2. **ID Prefix Matching (P1)**:
   - `ObservationRepository.get_by_id()` ahora soporta búsqueda por prefijo (mínimo 8 caracteres recomendado).
   - Manejo de ambigüedad: Lanza error si un prefijo coincide con más de una observación.
3. **Mejora de UX en CLI**:
   - `memory list` ahora muestra los primeros 12 caracteres del ID (visual alignment).
4. **Corrección de Contrato**:
   - Se actualizó `_contracts/phase-common.md §C` para reflejar con precisión el comportamiento de upsert.

### Verificación TDD
- 18 nuevos tests unitarios e integración pasando.
- Suite completa (1185 tests) sin regresiones.
- Verificación manual: `memory save` con el mismo `topic_key` retorna el mismo ID.

---

## Hallazgos de Auditoría Multi-Agente (Run 2026-04-16)

Se ejecutó una tarea espejo con 5 agentes especializados para comparar `tmux_fork` vs `engram`.

### Modelos Utilizados
| Rol | Modelo | Hallazgo Clave |
|------|-------|----------------|
| explorer | `minimax-m2.5` | 5/13 comandos alineados, 4 parciales, 4 faltantes (sesiones). |
| architect | `glm-5.1` | El schema actual es "metadata-heavy"; requiere columnas first-class. |
| implementer | `kimi-k2.5` | Inventario de 7 funciones faltantes (`update`, `suggest_topic`, `projects_list`). |
| verifier | `minimax-m2.5` | La semántica de upsert es correcta pero le falta granularidad `project+scope`. |
| analyst | `glm-5-turbo` | Cobertura estimada: 55%. Los gaps bloquean el flujo SDD completo. |

### Gaps Críticos Identificados (P0 para Sprint 2)
1. **Falta de Scoping por Proyecto**: No existe columna `project`. Las búsquedas son globales, lo que impide a los sub-agentes SDD aislar sus artefactos.
2. **Falta de Campo `type` Filtrable**: El tipo (architecture, decision, bugfix) vive en JSON, impidiendo filtros estructurales eficientes en SQL.
3. **Ciclo de Vida de Sesión**: Ausencia de `mem_session_start/end` y `mem_context` real (basado en sesión, no solo tiempo).

---

## Próximos Pasos (Sprint 2)

- [x] **Migración 010**: Añadir columnas `project` y `type` a `observations`.
- [x] **Scoping Automático**: Detectar nombre del proyecto desde el git remote (estándar engram).
- [x] **Filtros Estructurales**: Actualizar `search()` y `query()` para aceptar parámetros `project` y `type`.
- [x] **Comando `update` en CLI**: Exponer la funcionalidad de actualización directa por ID.

---

## Sprint 2: Engram Parity & Pi Extensions (Completado 2026-04-16)

Alineación completa con Engram (G1-G7) + Pi extensiones nativas.

### Pi Extensions (3)

| Extension | Eventos | Propósito |
|-----------|---------|----------|
| `context-loader.ts` | `session_start`, `turn_start`, `before_agent_start` | Inyecta rules.md + session.md + MEMORY_PROTOCOL en system prompt |
| `compact-memory-bridge.ts` | `session_before_compact`, `session_compact`, `before_agent_start` | Guarda/recupera summaries en compactación + búsqueda proactiva por keywords |
| `passive-capture.ts` | `agent_end` | Extrae `## Key Learnings:` de respuestas del agente y persiste a DB |

### Native Tools (registerTool)

| Tool | Propósito |
|------|----------|
| `memory_save` | Guardar observaciones sin shell command |
| `memory_search` | Buscar observaciones sin shell command |
| `memory_get` | Recuperar observación completa por UUID |

### Gaps G1-G7 cubiertos

| Gap | Engram feature | Implementación |
|-----|----------------|---------------|
| G1 | Self-check post-tarea | MEMORY_PROTOCOL en context-loader |
| G2 | Formato estructurado | What/Why/Where/Learned template |
| G3 | Key Learnings trigger | passive-capture.ts + regex parser |
| G4 | Búsqueda proactiva | extractKeywords() + before_agent_start |
| G5 | mem_context CLI | `memory context` command |
| G6 | Session close 6 campos | instructions field agregado |
| G7 | Native tool | registerTool x3 |

### Bugs Fixed (20 total: B1-B8 + N4-N8 + upsert tests + passive-capture)

**Críticos:**
- UNION search (FTS5 content + topic_key LIKE) — FTS5 no indexa topic_key
- One-shot cache clear perdía recovery en turn 2+ → cache persistente
- RECOVERY_QUERY constante unificada entre session_start y before_agent_start
- passive-capture: Pi messages usan `content: [{type:"text", text:...}]` no string

**Inyección de contexto:**
- session.md capped a 100 líneas (era 67% del budget)
- MEMORY_PROTOCOL: post-compact recovery como PRIMERA instrucción
- query_planner: OR terms individuales en vez de frases AND
- parse() filtra "No results found" para evitar inyección de ruido

### Budget de System Prompt

| Componente | Tokens | % del window 200K |
|-----------|--------|-------------------|
| context-loader (rules+session+protocol) | ~3300 | 1.6% |
| compact-memory-bridge (keywords+recovery) | ~450 | 0.2% |
| **Total máximo** | **~3750** | **1.9%** |

---
## Sprint 3: Sessions, Compact & Data Resilience (Completado 2026-04-16)

### Sessions Table (Migración 014)
| Componente | Ruta | Propósito |
|------------|------|------------|
| Entity | `src/domain/entities/session.py` | Modelo Session con lifecycle states |
| Port | `src/domain/ports/session_repository.py` | Interfaz abstracta |
| Repository | `src/infrastructure/persistence/repositories/session_repository.py` | Implementación SQLite |
| Service | `src/application/services/session_service.py` | Lógica de negocio |
| CLI | `memory session start/end/list/context` | Comandos de sesión |
| Lifecycle | start → active → paused → ended | Estados de sesión |

### Compact Protocol
| Comando | Propósito |
|---------|----------|
| `memory compact save-summary --goal X --accomplished X --next-steps X` | Guardar resumen de sesión |
| `memory compact recover` | Recupera últimos summaries + observations |
| `memory compact file-ops --op read --paths X` | Rastrea operaciones de archivo |

### Structured Save Format
`memory save "text" --type decision --what X --why X --where X --learned X` — Flags: --type, --what, --why, --where, --learned

### Sync Schema (Migración 015)
- Columnas `sync_id` y `synced_at` en observations — base para sync cross-device

### Subagent Failure Patterns
- 8 patrones cataloguados (P1-P8) — integrados en validación Phase 5.5

### Data Loss Incident (2026-04-16)
- DB pasó de 45K+ a 0 observations — causa: agente borró DB, recreada por migraciones
- Fix: auto-backup en `container.py` (`_auto_backup`)

### FTS5 Sanitizer Fix
- Añadidos `/` y `\` a caracteres permitidos

---
## Próximos Pasos (Sprint 3 — P2)

- [ ] `memory doctor` — health check CLI command
- [ ] `/memory` slash command en Pi
- [ ] Type backfill para 45K+ observaciones con type=NULL
- [ ] Observation TTL / cleanup policy
