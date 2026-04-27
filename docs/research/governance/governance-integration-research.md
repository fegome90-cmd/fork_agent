# Governance Integration Research — tmux_fork × anchor_dope × SDD × CLOOP

> **Tipo:** Living document — investigación y diseño de integración
> **Creado:** 2026-04-23
> **Estado:** En investigación

---

## 1. Mapa de Componentes

```
CLOOP (plan-architect)     → Arquitectura del plan (Clarify→Layout→Operate→Observe→Reflect)
  ↓ alimenta
anchor_dope (sprint pack)  → Materializa el plan en ANCHOR.md + SKILL.md + gates
  ↓ alimenta
SDD (spec-driven)          → Descompone cada sprint en spec→design→tasks→apply→verify→archive
  ↓ alimenta
tmux_fork (orchestrator)   → Ejecuta con sub-agentes en paralelo, valida, archiva
```

**Principio:** CLOOP gobierna la arquitectura. anchor_dope genera el artefacto. SDD descompone. tmux_fork ejecuta.

---

## 2. CLOOP — Metodología de Planificación

**Fuente:** `/Users/felipe_gonzalez/Developer/examen_grado/skills/plan-architect/SKILL.md`
**Registry:** `skill-hub` → `plan-architect`

### Fases CLOOP

| Fase | Propósito | Output |
|------|-----------|--------|
| **C**larify | Extraer objetivo SMART, hipótesis implícitas, criterios de éxito | Goal statement + hipótesis + métricas |
| **L**ayout | Arquitectura mínima (MVP), interfaces/contratos, métricas a recolectar | Diagrama + interfaces + checklist |
| **O**perate | Descomponer en fases, dependencias, checklist de validación | Fases + dependencias + orden |
| **O**bserve | Métricas con umbrales, evidencia a recolectar | KPIs + umbrales + collector plan |
| **R**eflect | Riesgos con mitigaciones, señales de stop/go | Risk register + go/no-go criteria |

### Variante CLOOP+G+S

**G**ates + **S**cope. Agrega gates explícitos entre fases y definición de scope/non-goals.

### Mapeo CLOOP → Protocolo tmux_fork

| CLOOP | Protocolo tmux_fork | Estado |
|-------|---------------------|--------|
| Clarify | Phase 0 (Clarify) | **Reemplazar** — CLOOP es más riguroso (SMART + hipótesis) |
| Layout | Phase 1 (Plan) | **Enriquecer** — Layout provee arquitectura mínima |
| Operate | Phase 1 (Plan) | **Enriquecer** — Descomposición en fases con dependencias |
| Observe | Phase 1.6 (Pre-flight) | **Nuevo** — Definir métricas ANTES de ejecutar |
| Reflect | Phase 1.5 (Plan Gate) | **Reemplazar** — Riesgos + stop/go reemplazan plannotator |

---

## 3. anchor_dope — Sprint Pack Generator

**Repo:** `/Users/felipe_gonzalez/Developer/anchor_dope/`
**Propósito:** CLI de scaffolding para sprint packs con governance (Constitución AI v1.1, 13 leyes)

### Artefactos que genera

| Template | Output | Rol |
|----------|--------|-----|
| `anchor.md.tmpl` | ANCHOR.md | SSOT del sprint |
| `SKILL.md.tmpl` | SKILL.md | Bridge operacional |
| `agents.md.tmpl` | AGENTS.md | Roles (Arquitecto/Ejecutor) |
| `prime.md.tmpl` | PRIME.md | Pre-flight gates |

### 4 Gates Pre-flight (obligatorios para todo plan)

| Gate | Condición | Evidencia |
|------|-----------|-----------|
| 1 — Contexto | Read anchor.md antes de cualquier acción | Puede resumir objetivo, scope, exit criteria |
| 2 — Fase | Identificó la fase actual | Puede declarar plan/execute/verify |
| 3 — Superficie | Identificó archivos a modificar | Lista de archivos confirmada |
| 4 — Estado limpio | Tests y lint pasan antes del cambio | `make test` y `make lint` retornan 0 |

### Reglas de conflicto

1. `anchor.md` gana sobre cualquier otro documento — **sin excepciones**
2. `SKILL.md` gana sobre `agents.md` y `prime.md`
3. Entre `agents.md` y `prime.md`: sin jerarquía — contradicción es error

### Validación

`doctor.sh` verifica: estructura, secciones requeridas, consistencia de slugs, límites de líneas, resolución de referencias.

### Gaps actuales

- `new_sprint_pack.sh` y `doctor.sh` están referenciados pero **no existen en disco**
- Solo `trifecta_manager.sh` existe en `scripts/`
- SDD solo aparece en tests (`verify_sdd_utils.sh`)

---

## 4. SDD — Spec-Driven Development

**Skills:** 11 skills bajo `~/.pi/agent/skills/sdd-*`

### Ciclo SDD

```
sdd-init → sdd-explore → sdd-propose → [sdd-spec + sdd-design] → sdd-tasks → sdd-gate → sdd-apply → sdd-verify → sdd-archive
                                      (paralelo posible)                   (quality gate)  (TDD-aware)  (evidence)
```

### Skills Disponibles

| Skill | Propósito | Persistencia |
|-------|-----------|-------------|
| `sdd-init` | Detectar stack, convenciones, testing | engram/openspec/hybrid/none |
| `sdd-explore` | Investigar codebase, comparar approaches | engram |
| `sdd-propose` | Change proposal con intent, scope, approach | engram |
| `sdd-spec` | Delta specs (requisitos + escenarios) | engram/openspec |
| `sdd-design` | Design doc técnico, decisiones arquitectura | engram/openspec |
| `sdd-tasks` | Breakdown en implementation tasks | engram |
| `sdd-gate-skill` | Quality gate pre-implementación | — |
| `sdd-apply` | Escribir código siguiendo specs + design | — |
| `sdd-verify` | Validar implementación vs specs/design/tasks | — |
| `sdd-archive` | Sync delta specs → main specs, archivar | engram/openspec |
| `sdd-onboard` | Walkthrough guiado del ciclo completo | — |

### Flujo existente en memory CLI

| Comando CLI | ≈ SDD Phase | Gap |
|-------------|-------------|-----|
| `memory workflow outline` | propose + spec + design + tasks | Combinado, no separa |
| `memory workflow execute` | apply | OK |
| `memory workflow verify` | verify | OK |
| `memory workflow ship` | archive (parcial) | No sync specs |

**Brecha:** CLI workflow no tiene exploration phase, spec/design separation, quality gate, ni spec archival.

### Mapeo SDD → Protocolo tmux_fork

| Protocolo | Integración SDD |
|-----------|----------------|
| Phase 0: Clarify | sdd-explore puede alimentar respuestas |
| Phase 1: Plan | **sdd-propose** reemplaza decomposición ad-hoc |
| Phase 1.5: Plan Gate | **sdd-gate-skill** agrega quality check de specs |
| Phase 1.6: Pre-flight | sdd-init fast-path |
| Phase 2: Save | Agregar metadata `sdd_change` |
| Phase 3: Spawn | sdd-tasks spawn mapping → agent assignment |
| Phase 5: Consolidate | sdd-verify cross-validation |
| Phase 5.5: Validate | sdd-verify como verification layer formal |
| Phase 6: Cleanup | sdd-archive (condicional si `sdd_change` presente) |

### Plan de integración previo (nunca implementado)

Diseñado en `resources/sdd-integration-plan.md` (DEAD — a reemplazar):
- 3 fases de implementación (Skills + Protocol + Docs)
- ~175 líneas de cambios
- 9 cambios concretos en 7 archivos
- **Nada se implementó** — solo diseño

---

## 5. Integración Diseñada — Governance Unificada

### 5.1 Flujo completo

```
Usuario: "orquesta X"
  │
  ├─ Phase 0: CLOOP Clarify (plan-architect)
  │   └─ SMART goal + hipótesis + criterios de éxito
  │
  ├─ Phase 1: CLOOP Layout + Operate (plan-architect)
  │   ├─ anchor_dope: materializa plan → ANCHOR.md + SKILL.md
  │   └─ SDD: sdd-propose → sdd-spec + sdd-design → sdd-tasks
  │
  ├─ Phase 1.5: CLOOP Reflect + anchor_dope Gates
  │   ├─ 4 gates pre-flight (Contexto, Fase, Superficie, Estado limpio)
  │   └─ sdd-gate-skill (quality check specs/design/tasks)
  │
  ├─ Phase 1.6: Pre-flight + CLOOP Observe
  │   ├─ Métricas con umbrales definidos
  │   └─ sdd-init fast-path (read .fork/init.yaml)
  │
  ├─ Phase 2: Save Context (metadata: sdd_change + cloop_plan_id)
  │
  ├─ Phase 3: Spawn (sdd-tasks → agent assignment mapping)
  │
  ├─ Phase 4-5: Monitor + Consolidate (sin cambios)
  │
  ├─ Phase 5.5: Validate
  │   ├─ sdd-verify (implementación vs specs)
  │   └─ anchor_dope doctor (structural validation)
  │
  └─ Phase 6: Cleanup
      ├─ sdd-archive (sync specs, archivar change)
      └─ Quality report + session log
```

### 5.2 Contratos entre componentes

| Desde | Hacia | Contrato |
|-------|-------|----------|
| CLOOP (plan) | anchor_dope | CLOOP output → anchor.md template vars |
| anchor_dope | SDD | ANCHOR.md → sdd-propose scope input |
| SDD (tasks) | tmux_fork | Task list → agent assignment table |
| SDD (verify) | anchor_dope | Verification results → doctor.sh input |
| SDD (archive) | memory CLI | Delta specs → engram/openspec persistence |

### 5.3 Entregables

| # | Qué | Dónde | ~Líneas | Prioridad |
|---|-----|-------|---------|-----------|
| 1 | Governance doc (CLOOP + anchor_dope + SDD) | `resources/governance.md` | ~80 | P1 |
| 2 | SDD bridge (reemplaza integration-plan) | `resources/sdd-bridge.md` | ~60 | P1 |
| 3 | Protocol Phase 0-1 enriquecido con CLOOP | `resources/protocol.md` | ~30 cambios | P1 |
| 4 | Protocol Phase 1.5 con anchor_dope gates | `resources/protocol.md` | ~20 cambios | P1 |
| 5 | SKILL.md governance section + index update | `SKILL.md` | ~15 cambios | P1 |
| 6 | Eliminar dead resources | plannotator-gate.md, sdd-integration-plan.md | — | P0 |

---

## 6. Hallazgos del Audit (2026-04-23)

### Scripts (18 total)

| Estado | Cantidad | Detalle |
|--------|----------|---------|
| KEEP | 14 | Sin issues |
| BUG | 3 | trifecta-context-inject (hardcoded path), trifecta-quality-report (--json), detect-env (no --help) |
| REMOVE | 0 | — |

### Resources (26 total)

| Estado | Cantidad | Detalle |
|--------|----------|---------|
| DEAD | 2 | plannotator-gate.md, sdd-integration-plan.md |
| STALE | 3 | protocol-legacy.md, workflow-recipes.md, protocol.md |
| UPDATE | 2 | cli-reference.md, memory-commands.md |
| MINOR | 1 | known-issues.md (archive fixed) |
| CURRENT | 17 | Sin cambios necesarios |

### SKILL.md

- Model Assignment: faltan roles free-tier (explorer-free, implementer-free)
- Resources Index: 2 entries dead (plannotator-gate, sdd-integration-plan)
- Sin governance layer — **nuevo section necesario**

---

## 7. Authority Flow Audit — Hallazgos Críticos

> Fuente: `docs/research/governance/authority-flow-audit.md`
> 11 findings: 2 CRITICAL, 3 HIGH, 4 MEDIUM, 2 LOW

### P1 — Block antes de implementar (4 findings)

| # | Problema | Tipo | Resolución propuesta |
|---|----------|------|---------------------|
| F1 | **Double writer en ANCHOR.md** — orchestrator y anchor_dope ambos escriben | double-writer | ANCHOR.md es SSOT solo si anchor_dope está activo. Si no, PLAN.md manda. Regla: "si ANCHOR.md existe, Phase 1 lee, nunca escribe" |
| F2 | **CLOOP Clarify vs Phase 0** — dos pipelines de clarificación | competing-pipeline | Protocol Phase 0 hace dispatch: si plan-architect disponible → delegar a CLOOP. Sino → inline |
| F3 | **CLOOP Layout/Operate vs Phase 1** — output format no mapea 1:1 | competing-pipeline | Definir transformación: CLOOP output → normalizar al schema de Phase 1 (subtasks + roles + acceptance criteria) |
| F4 | **workflow outline vs SDD propose** — dos decomposition pipelines | competing-pipeline | Decidir: deprecar outline para proyectos SDD, mantener como fast-path para no-SDD |

### P2 — Prerequisitos (2 findings)

| # | Problema | Tipo |
|---|----------|------|
| F5 | False SSOT: ANCHOR.md declarado rey pero no existe (scripts faltantes) | false-ssot |
| F9 | anchor_dope scripts faltantes (new_sprint_pack.sh, doctor.sh) — toda la capa es vapor | false-ssot |

### P3 — Diseño (4 findings)

| # | Problema | Resolución |
|---|----------|------------|
| F6 | Double gate Phase 1.5 + 1.6 | Merge en secuencia ordenada: anchor_dope gates (context) → pre-flight (infrastructure) |
| F7 | sdd-gate vs human approval | sdd-gate ANTES del humano. FAIL = auto-reject. PASS = forward a humano |
| F8 | Persistence mode fragmentation | Pin governance pipeline a `hybrid` |
| F10 | sdd-verify vs Phase 5.5 | sdd-verify REEMPLAZA spec compliance, no duplica |

### Principio de diseño derivado del audit

> **Cada capa LEE del anterior y ESCRIBE sus propios artefactos. Ninguna capa escribe artefactos de otra capa.**

---

## 7b. Principio de No-Regresión — Gates de Protección

> **Regla fundamental:** La integración es ADDITIVE. Nada de lo construido se pierde, se reemplaza o se degrada. Cada nueva capa pasa por gates que verifican que el sistema existente sigue funcionando idéntico.

### El contrato

```
Sin governance → el protocolo de 10 fases funciona EXACTAMENTE como hoy
Con governance → las fases existentes se ENRIQUECEN, nunca se reemplazan
Fallback        → si una capa falla, el sistema continúa sin esa capa
```

### Gates de No-Regresión (por fase)

| Gate | Protege qué | Verifica | Blocking |
|------|------------|----------|----------|
| **G0: Fast-path intacto** | Proyectos sin .fork/init.yaml | `memory workflow outline/execute/verify/ship` funciona sin CLOOP/SDD/anchor_dope | Sí |
| **G1: Protocolo 10 fases intacto** | Fases 0-6 sin dependencias nuevas | Sin CLOOP: Phase 0 usa inline clarify. Sin SDD: Phase 1 usa ad-hoc decomposition. Sin anchor_dope: Phase 1 genera PLAN.md | Sí |
| **G2: Retrocompatibilidad de skills** | Skills existentes cargan igual | skill-resolver, phase-common, agent-*.md, enforce-envelope funcionan sin governance | Sí |
| **G3: Scripts existentes intactos** | 18 scripts siguen funcionando | `bash -n` + `--help` en todos los scripts. json-vis, read-turn, watch-agent sin cambios | Sí |
| **G4: CLI commands intactos** | memory + fork CLI sin breaking changes | `memory save/search/list/get/delete` + `fork doctor/message` idénticos | Sí |
| **G5: MCP tools intactos** | 21 MCP tools sin cambios | MCP server arranca, tools responden, formato idéntico | Sí |
| **G6: Persistence compatible** | Memory DB schema sin cambios | Lectura de observaciones pre-governance funciona. No se pierden datos existentes | Sí |
| **G7: Session continuity** | Sesiones activas continúan | Session recovery después de upgrade funciona. Context budget respetado | Sí |

### Reglas de implementación

**R1: Feature flags para toda nueva funcionalidad**
```bash
# Sin governance (fast-path) — idéntico a hoy
memory workflow outline "task"

# Con governance — enriquecido, pero outline sigue siendo el entry point
GOVERNANCE=1 memory workflow outline "task"
# → dispara CLOOP Clarify + SDD propose automáticamente
```

**R2: Degrade gracefully, nunca hard-fail**
```
CLOOP no disponible  → Phase 0 usa inline clarify (como hoy)
SDD no disponible    → Phase 1 usa ad-hoc decomposition (como hoy)
anchor_dope no activo → Phase 1 genera PLAN.md (como hoy)
Trifecta no arranca  → skill-resolver fallback (como hoy)
MCP server caído     → direct service calls (como hoy, hybrid mode)
```

**R3: Cada layer es independiente**
- CLOOP puede usarse sin SDD
- SDD puede usarse sin CLOOP
- anchor_dope puede usarse sin CLOOP ni SDD
- tmux_fork funciona sin ninguna de las tres

**R4: Tests de no-regresión obligatorios**
Antes de mergear cualquier cambio de governance:
1. Ejecutar tests existentes (uv run pytest) — todos deben pasar sin cambios
2. Ejecutar scripts con --help — todos deben responder
3. Ejecutar memory workflow outline/execute/verify/ship — sin governance
4. Ejecutar fork doctor status — sin cambios
5. Verificar MCP tools response format — sin cambios
6. Verificar que observaciones pre-governance son legibles

**R5: Artifact format backward-compatible**
- PLAN.md sigue siendo el formato default (sin governance)
- ANCHOR.md es adicional (con anchor_dope), no reemplaza PLAN.md
- SDD artifacts usan topic_keys que no colisionan con observaciones existentes
- Config nueva (schema.yaml, constitution.md) es opcional, no requerida

### Checklist de Gate por Entregable

Antes de cada entregable del §5.3:

- [ ] Tests existentes pasan sin cambios
- [ ] Scripts existentes funcionan sin cambios
- [ ] CLI commands funcionan sin governance habilitado
- [ ] MCP tools responden igual
- [ ] Memory DB legible sin nuevos campos requeridos
- [ ] No se eliminó ni renombró ningún archivo existente
- [ ] No se cambió la firma de ningún CLI command existente
- [ ] No se agregó dependencia obligatoria nueva

---

## 8. spec-kit Borrow List

> Fuente: `docs/research/governance/complement-analysis.md`

### Tomar de spec-kit

| # | Qué | Dónde integrar |
|---|-----|---------------|
| 1 | Clarification phase con coverage-based questioning | Protocol Phase 0.5 |
| 2 | Constitution para tech decisions (no reemplaza Constitución AI) | `.fork/constitution.md` — usamos nuestro propio directorio |
| 3 | Coverage gap detection (requerimientos sin tasks) | Mejorar `sdd-gate-skill` |
| 4 | User Story priority markers [P1]/[P2]/[P3] | Agregar a SDD spec format |
| 5 | Quality checklist generation | Protocol Phase 1.5 |

### NO tomar de spec-kit

| Qué | Por qué |
|-----|--------|
| Extension system | skill-hub ya lo cubre |
| Workflow engine | tmux_fork protocol ES nuestro engine |
| Multi-agent registry | pi-only es nuestro scope |
| spec.md format | SDD delta specs son mejores para brownfield |
| implement command | sdd-apply con strict TDD es más riguroso |

---

## 8b. OpenSpec — Análisis Complementario

> Fuente: `docs/research/governance/openspec-analysis.md` + `openspec-complement.md`
> Repo: https://github.com/Fission-AI/OpenSpec

### Qué es OpenSpec

CLI TypeScript (pnpm + vitest) para spec-driven change management. Modelo: **repo-scoped canonical specs + change folders con delta specs**.

**Arquitectura:** `openspec/specs/` (source of truth) + `openspec/changes/<name>/` (deltas) + `openspec/changes/archive/` (history).

### Ciclo de vida

```
openspec init → /opsx:explore → /opsx:propose → validate → /opsx:apply → /opsx:verify → /opsx:archive
```

### Puntos fuertes vs spec-kit

1. **Lifecycle completo** — archive + bulk-archive como first-class citizens
2. **Brownfield-friendly** — specs/ = current truth, changes/ = deltas
3. **Parallel changes** — múltiples cambios activos con conflict resolution
4. **Schema YAML** — artifact DAG declarativo como workflow contract
5. **Menos ceremonia** — propose → apply → archive como fast path

### Puntos donde nuestro stack SUPERA a OpenSpec

1. Governance rigor (CLOOP + anchor_dope + SDD gates)
2. Pre-implementation blocking gates (sdd-gate)
3. Post-implementation compliance matrix (sdd-verify)
4. Strict TDD con evidence tables
5. Hybrid persistence (filesystem + memory MCP)
6. Orquestación paralela con agentes (tmux_fork)

### 3 ideas para ROBAR

| # | Idea | Dónde aplicar |
|---|------|---------------|
| 1 | **specs/ vs changes/ topology** — separación visual de truth vs deltas | Repositorio de artefactos SDD — layout más legible |
| 2 | **Schema YAML como artifact DAG** — workflow contract declarativo | `.fork/schema.yaml` — config para artifact dependencies sin hardcodear en skills |
| 3 | **bulk-archive con conflict resolution** — cerrar múltiples cambios en paralelo | Phase 6 — multi-change archive/sync |

### Ideas a EVITAR

| Idea | Por qué |
|------|--------|
| Verification advisory-only | Necesitamos blocking gates |
| Filesystem-only state | Ya tenemos hybrid persistence |
| Fluididad sin boundaries | Governance > speed |
| Parser-fragile markdown | Un typo no debería romper semántica |

### Diferencia filosófica fundamental

- **OpenSpec** optimiza por **friction reduction** — specs prácticos para brownfield
- **spec-kit** optimiza por **spec discipline** — constitución como governance
- **Nuestro stack** optimiza por **spec discipline + orchestration discipline** — governance + ejecución

OpenSpec es el **análogo externo más cercano a SDD** (delta specs, change folders, archive), pero más ligero y menos gobernado.

---

## 9. Decisiones Resueltas

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| Q1 | anchor_dope scripts | **Implementar** | Necesario para contrato SSOT de anchor.md |
| Q2 | SDD persistence | **hybrid, pero sin engram** | Usar MCP de memory propio de tmux_fork |
| Q3 | CLOOP+G+S default | **Sí, default** | Pasa a ser el modo estándar |
| Q4 | Governance layer | **Always-on con fast-path** | Siempre activo, pero proyectos no-SDD usan fast-path sin spec/design separation |
| Q5 | workflow outline vs CLOOP | **Conviven, outline es state tracker** | Ver análisis abajo |
| Q6 | fork task/poll | **Otro agente trabaja en ello** | Esperar a que termine |
| Q7 | Template stamping | **Orquestador lo hace** | anchor_dope es subordinado del proceso de orquestación |
| Q8 | Spec compliance | **Dinámica con reporte estático** | Test execution real + reporte de trazabilidad |
| Q9 | Capa de salida (review loop) | **Phase 5.7: Quality Loop** | Ver diseño abajo |

### Q5: memory workflow outline — Análisis

`memory workflow outline` es un **state tracker minimalista**: crea un plan file con la task description como único item, genera session_id, guarda state en JSON, despacha eventos. NO descompone, NO genera specs, NO hace design.

**Veredicto:** outline y CLOOP/SDD son **capas diferentes, no compiten**.

- `memory workflow outline` = state machine + session tracking + evento dispatch
- CLOOP = metodología de planificación (Clarify→Layout→Operate→Observe→Reflect)
- SDD = decomposition pipeline (propose→spec→design→tasks)

**Integración:** outline se convierte en el **entry point** del governance pipeline. Cuando CLOOP+SDD están activos:
1. `outline` recibe la task description
2. Dispara `WorkflowOutlineStartEvent`
3. CLOOP Clarify reemplaza la generación ad-hoc del plan
4. SDD populates el plan con spec/design/tasks
5. `WorkflowOutlineCompleteEvent` marca el fin

Cuando CLOOP+SDD NO están activos (fast-path):
1. `outline` funciona como hoy — stub mínimo

### Q9: Phase 5.7 — Quality Loop (nueva fase)

```
Phase 5.5: Validate (sdd-verify + compliance matrix)
    ↓
Phase 5.7: Quality Loop (nuevo)
    ├─ Iteración 1: review + audit + bug-hunt
    ├─ Si warnings > 0: loop (fix → verify → review)
    ├─ Si warnings = 0: exit
    ├─ Si complejidad alta: pedir autorización humana
    └─ Output: Quality Report (métricas + hallazgos + recomendaciones)
    ↓
Phase 6: Cleanup
    ├─ sdd-archive
    ├─ memory update (quality report)
    └─ Sugerir commit + PR
```

**Reglas del loop:**
1. Termina cuando warnings == 0
2. Complejidad alta (>N archivos, >M líneas) → pedir autorización humana
3. Cada iteración genera reporte incremental
4. Reporte final: métricas de calidad + hallazgos por severidad + recomendaciones
5. Último paso: actualizar memoria + sugerir commit y PR

**Herramientas integradas:**
- `memory workflow bug-hunt` → adversarial testing
- `conflict-detect` → conflicts entre fixes paralelos
- `trifecta-verifier-check` → caller completeness
- `sdd-verify` → spec compliance re-check

---

## 10. Historial de cambios

| Fecha | Cambio |
|-------|--------|
| 2026-04-23 | Creación del documento con findings de 3 auditores + exploración anchor_dope + SDD |
| 2026-04-23 | Deep-dive: SDD skill internals (10 skills, contracts, artifact graph, TDD modules) |
| 2026-04-23 | Deep-dive: anchor_dope templates (2 vars, 4 docs, line limits, conflict rules) |
| 2026-04-23 | CLI gap analysis: fork task/poll NO implementado, outline es flat, falta archive |
| 2026-04-23 | spec-kit deep-dive: 8-command lifecycle, constitution system, 30+ agent integrations |
| 2026-04-23 | Complement analysis: 85% overlap ya cubierto, borrow 5 ideas |
| 2026-04-23 | Authority flow audit: 11 findings (2 CRITICAL, 3 HIGH) — double-writer + competing pipelines |
| 2026-04-23 | 9/9 open questions resueltas. Phase 5.7 Quality Loop diseñado |
| 2026-04-23 | Q5: outline = state tracker, CLOOP/SDD = planning layers, conviven sin competir |
| 2026-04-23 | OpenSpec deep-dive: specs/ vs changes/ topology, schema YAML DAG, bulk-archive. Más cercano a SDD que spec-kit |
| 2026-04-23 | No-Regression Gates (§7b): 8 gates de protección + 5 reglas de implementación + checklist por entregable |
