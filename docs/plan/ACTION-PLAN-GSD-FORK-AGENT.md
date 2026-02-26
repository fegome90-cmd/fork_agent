# Plan de Acción: Análisis Cruzado GSD vs fork_agent

> **Fuente:** [`docs/informes/CROSS-ANALYSIS-GSD-FORK-AGENT.md`](docs/informes/CROSS-ANALYSIS-GSD-FORK-AGENT.md)  
> **Fecha de generación:** 2026-02-25  
> **Tipo:** Roadmap técnico priorizado

---

## Resumen Ejecutivo

Este plan consolida las oportunidades de mejora identificadas en el análisis cruzado entre GSD (get-shit-done) y fork_agent. El objetivo es fortalecer la arquitectura DDD de fork_agent mediante la incorporación de patrones probados de GSD, particularmente en gestión de estado, verificación sistemática y contexto.

**Prioridades clave:**
- **P0 (Completado):** State Schema Versioning ✅, Hook Criticality Levels ✅, Migration System ✅
- **P1 (Inmediata):** User Decisions Tracking, Phase Skip Prevention
- **P2 (1-2 Sprints):** Goal Analysis, Evidence Collection, Phase Research
- **P3 (Largo Plazo):** Agent Definitions as Config, Context Summarization

---

## 1. Brechas Críticas (P0) - COMPLETADO

> ⚠️ **NOTA:** Estas brechas fueron identificadas en análisis anteriores pero YA ESTÁN IMPLEMENTADAS en el código actual.

### 1.1 GAP-WF-001: State Schema Versioning ✅ COMPLETADO

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | P0 - COMPLETADO |
| **Complejidad** | N/A |
| **Dependencias** | Ninguna |
| **Módulo afectado** | `src/application/services/workflow/state.py` |

**Estado actual:** ✅ IMPLEMENTADO
- `CURRENT_SCHEMA_VERSION = 1` definido en línea 12
- Campo `schema_version` en PlanState, ExecuteState, VerifyState
- Migración automática v0 → v1 en `from_json()`
- Excepciones `UnsupportedSchemaError` para versiones futuras

**Acción requerida:** Ninguna - verificar periodically con tests existentes

---

### 1.2 GAP-WF-003: Phase Skip Prevention

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | P0 - Crítica |
| **Complejidad** | Baja |
| **Dependencias** | Ninguna (schema ya implementado) |
| **Módulo afectado** | `src/application/services/workflow/`, CLI commands |

**Descripción:** No hay validación a nivel de API/Use Cases para prevenir saltos de fase.

**Acción requerida:**
- [ ] Implementar validación en Use Cases antes de transiciones de fase
- [ ] Añadir checks en `src/application/use_cases/`
- [ ] Crear excepción `PhaseSkipError` en `src/application/exceptions.py`

---

### 1.3 GAP-DB-001: Migration System ✅ COMPLETADO

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | P0 |
| **Complejidad** | Alta |
| **Dependencias** | Schema existente (GAP-WF-001 ya implementado) |
| **Módulo afectado** | `src/infrastructure/persistence/` |

**Acción requerida:**
- [ ] Diseñar sistema de migraciones de schema
- [ ] Implementar CLI para ejecución de migraciones
- [ ] Crear tabla de metadata de migraciones

---

### 1.4 GAP-DB-002: Idempotency Mechanism

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | P0 |
| **Complejidad** | Media |
| **Dependencias** | Ninguna |

**Acción requerida:**
- [ ] Implementar IDs idempotentes para operaciones de workflow
- [ ] Añadir checks de operación duplicada antes de ejecutar
- [ ] Documentar en `docs/`

---

### 1.5 GAP-HK-001: Hook Criticality Levels ✅ COMPLETADO

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | P0 - COMPLETADO |
| **Complejidad** | N/A |
| **Dependencias** | Ninguna |
| **Módulo afectado** | `src/application/services/orchestration/actions.py` |

**Estado actual:** ✅ IMPLEMENTADO
- Campo `critical: bool = True` en `HookSpec` (actions.py línea 30)
- Método `continue_on_failure()` implementado
- Uso en `.hooks/hooks.json` con valores `true`/`false`

**Acción requerida:** Ninguna

---

## 2. Oportunidades de Alta Prioridad (1 Sprint)

### 2.1 Oportunidad 1: User Decisions Tracking

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | Alta |
| **Complejidad** | Media |
| **Impacto** | Alto |
| **Brechas relacionadas** | GAP-WF-002, GAP-WF-003 |
| **Módulo afectado** | `src/application/services/workflow/` |

**Descripción:** Implementar sistema de seguimiento de decisiones del usuario en el workflow state para preservar contexto entre interacciones.

**Acciones requeridas:**

1. **Crear clase UserDecision** (`src/domain/entities/` o `src/application/services/workflow/`)
   ```python
   @dataclass
   class UserDecision:
       key: str
       value: str
       status: Literal["locked", "deferred", "discretion"]
       rationale: str | None = None
   ```

2. **Extender WorkflowState**
   - Añadir campo `decisions: dict[str, UserDecision]`
   - Implementar métodos para adicionar/consultar decisiones

3. **Integrar con CLI**
   - Modificar comandos para consultar decisiones antes de ejecutar
   - Añadir comando para listar decisiones del workflow

4. **Tests**
   - [ ] Crear tests unitarios en `tests/unit/application/services/workflow/`
   - [ ] Verificar serialización/deserialización

**Métricas de éxito:**
- Decisiones persistentes entre fases del workflow
- CLI muestra estado de decisiones
- 90% cobertura de tests

---

### 2.2 Oportunidad 2: Goal Analysis en Outline

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | Alta |
| **Complejidad** | Alta |
| **Impacto** | Alto |
| **Brechas relacionadas** | Schema existente (State Schema Versioning) |
| **Módulo afectado** | CLI commands (`src/interfaces/cli/commands/workflow.py`) |

**Descripción:** Incorporar análisis de objetivo en la fase de outline, siguiendo el patrón goal-backward planning de GSD.

**Acciones requeridas:**

1. **Extender comando outline**
   - Añadir parámetros para aceptar objetivo (--goal, --must-haves)
   - Procesar y almacenar en PlanState

2. **Extender PlanState**
   - Añadir campos: `goal`, `must_haves`, `derived_requirements`
   - Requerirá migración de schema (depende de GAP-WF-001)

3. **Implementar derivación de requisitos**
   - Análisis del objetivo para derivar requisitos mínimos
   - Identificación de dependencias entre tareas
   - Generación de plan backward desde objetivo

4. **Tests**
   - [ ] Tests de derivación de requisitos
   - [ ] Tests de integración con workflow

**Métricas de éxito:**
- Outline genera plan que cumple requisitos mínimos
- Trazabilidad entre objetivo y tareas generadas

---

## 3. Oportunidades de Prioridad Media (2 Sprints)

### 3.1 Oportunidad 3: Evidence Collection para Verificación

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | Media |
| **Complejidad** | Media |
| **Impacto** | Directo en confiabilidad |
| **Brechas relacionadas** | GAP-WF-002, GAP-WF-003 |
| **Módulo afectado** | `src/application/services/workflow/`, `src/application/services/agent/` |

**Descripción:** Separar verificación en dos pasos: recolección de evidencia y validación contra specifications.

**Acciones requeridas:**

1. **Crear módulo EvidenceCollector**
   - Recopilar outputs de ejecución
   - Recopilar resultados de tests
   - Recopilar logs relevantes

2. **Crear SpecValidator**
   - Comparar evidencia contra requisitos explícitos
   - Reportar brechas de forma estructurada

3. **Integrar con workflow**
   - Añadir fase de evidence collection antes de verify
   - Almacenar evidencia en estado

**Métricas de éxito:**
- Evidencia recopilada automáticamente en cada ejecución
- Reporte estructurado de cumplimiento de specs

---

### 3.2 Oportunidad 4: Phase Research Integration

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | Media |
| **Complejidad** | Media |
| **Impacto** | Calidad de planificación |
| **Brechas relacionadas** | GAP-WF-001 |
| **Módulo afectado** | `src/application/services/workspace/`, workflow |

**Descripción:** Añadir fase de investigación obligatoria antes de planificar/ejecutar.

**Acciones requeridas:**

1. **Integrar con workspace detection existente**
   - Utilizar `workspace_detector.py` como base
   - Añadir detección de stack tecnológico

2. **Extender workflow state**
   - Añadir campos para contexto investigado
   - Requerirá versionado de schema

3. **Crear agentes de investigación**
   - gsd-phase-researcher (análisis de fase)
   - gsd-project-researcher (contexto de proyecto)
   - gsd-codebase-mapper (estructura del codebase)

**Métricas de éxito:**
- Contexto auto-descubierto disponible en planificación
- Reducción de errores por falta de contexto

---

## 4. Oportunidades de Baja Prioridad (Largo Plazo)

### 4.1 Oportunidad 5: Agent Definitions as Config

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | Baja |
| **Complejidad** | Alta |
| **Impacto** | Mantenibilidad y extensibilidad |
| **Brechas relacionadas** | GAP-PT-001 |
| **Módulo afectado** | `src/application/services/agent/` |

**Descripción:** Migrar agentes de código Python a configuración JSON/YAML.

**Acciones requeridas:**

1. **Diseñar schema de AgentDefinition**
   - Definir estructura YAML/JSON para agentes
   - Incluir prompts, tools permitidas, comportamientos

2. **Crear AgentDefinitionLoader**
   - Cargar definiciones de archivos de configuración
   - Traducir a comportamiento ejecutable

3. **Refactorizar AgentManager**
   - Mantener como capa de ejecución
   - Cargar definiciones dinámicamente

4. **Estrategia de transición**
   - Mantener agentes actuales durante migración
   - Migrar incrementalmente

**Métricas de éxito:**
- Nuevos agentes añadibles sin modificar código
- Separation completa de definición y ejecución

---

### 4.2 Oportunidad 6: Context Summarization

| Atributo | Detalle |
|----------|---------|
| **Prioridad** | Baja |
| **Complejidad** | Alta |
| **Impacto** | Sesiones largas |
| **Brechas relacionadas** | Nueva (no mapeada en DECISION-GAPS) |

**Descripción:** Sistema de resumen/compresión de contexto cuando la ventana se llena.

**Acciones requeridas:**

1. **Implementar detección de ventana llena**
   - Monitorizar tamaño de contexto
   - Trigger antes de overflow

2. **Crear sistema de generación de resúmenes**
   - Técnicas de summary extraction
   - Retención de contexto accionable

3. **Integrar con sistema de memoria**
   - Usar SQLite existente con FTS5
   - Añadir tabla de resúmenes

**Métricas de éxito:**
- Resúmenes generados automáticamente
- Mantenimiento de calidad de respuestas con contexto reducido

---

## 5. Recomendaciones Transversales

### 5.1 Arquitectura

| # | Recomendación | Dependencia | Complejidad |
|---|---------------|-------------|-------------|
| ARQ-1 | Adoptar patrón de agentes especializados | Oportunidad 3 | Media |
| ARQ-2 | Implementar versionado de schema | ✅ Completado | Media |
| ARQ-3 | Separar definición de ejecución de agentes | Oportunidad 5 | Alta |

### 5.2 Proceso

| # | Recomendación | Dependencia | Complejidad |
|---|---------------|-------------|-------------|
| PROC-1 | Implementar pruebas de workflow state | Todas | Media |
| PROC-2 | Establecer métricas de contexto | Oportunidad 6 | Baja |

### 5.3 Técnicas

| # | Recomendación | Dependencia | Complejidad |
|---|---------------|-------------|-------------|
| TECH-1 | Extender hooks.json para criticalidad | GAP-HK-001 | Baja |
| TECH-2 | Unificar configuraciones de CircuitBreaker | Ninguna | ✅ COMPLETADO |

---

## 6. Matriz de Dependencias

```
GAP-WF-001 (Schema Versioning) - ✅ COMPLETADO
├── Oportunidad 2 (Goal Analysis)
├── Oportunidad 4 (Phase Research)
└── Oportunidad 5 (Agent Config)

Oportunidad 1 (User Decisions)
├── Requires: Estado actual con schema versioning
└── Enables: Oportunidad 3 (Evidence Collection)

Oportunidad 3 (Evidence Collection)
└── Enables: Oportunidad 5 (Agent Config - verification agent)
```

---

## 7. Roadmap Visual

| Fase | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4+ |
|------|----------|----------|----------|-----------|
| **Infraestructura** | ✅ GAP-WF-001 | ✅ GAP-DB-001 | - | - |
| **Alta Prioridad** | Oportunidad 1 | Oportunidad 2 | - | - |
| **Media Prioridad** | - | - | Opp 3 | Opp 4 |
| **Largo Plazo** | - | - | - | Opp 5, 6 |

---

## 8. Métricas de Éxito del Plan

### Métricas Técnicas
- **Cobertura de tests:** ≥ 95% en módulos modificados
- **Schema versioning:** 100% estados versionados
- **Migraciones:**Compatibilidad N-1 verificada

### Métricas Funcionales
- **User Decisions:** Persistencia verificada entre fases
- **Goal Analysis:** Trazabilidad objetivo → tareas
- **Evidence Collection:** Recopilación automática
- **Phase Research:** Contexto disponible en planificación

### Métricas de Contexto (Recomendación PROC-2)
- Tokens por sesión
- Crecimiento de contexto por fase
- Correlación con calidad de outputs

---

## 9. Referencias

- [`docs/informes/ARCHITECTURE.md`](docs/informes/ARCHITECTURE.md) - Arquitectura de referencia
- [`docs/informes/DECISION-GAPS.md`](docs/informes/DECISION-GAPS.md) - Catálogo de brechas
- [`docs/informes/EXPLORATION-DECISION-INPUTS.md`](docs/informes/EXPLORATION-DECISION-INPUTS.md) - Evidencia de pruebas
- [`docs/informes/GSD-IDEAS-FORK-AGENT.md`](docs/informes/GSD-IDEAS-FORK-AGENT.md) - Ideas de transferencia
- [GSD Repository](https://github.com/gsd-build/get-shit-done) - Proyecto de referencia

---

*Documento generado automáticamente desde CROSS-ANALYSIS-GSD-FORK-AGENT.md*
*Última actualización: 2026-02-25*
