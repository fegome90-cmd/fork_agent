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

## 7. Open Questions

- [ ] ¿anchor_dope scripts faltantes (new_sprint_pack.sh, doctor.sh) se implementan o se descarta?
- [ ] ¿SDD persistence mode default: engram o hybrid?
- [ ] ¿CLOOP+G+S es el default o solo cuando el usuario lo pide explícito?
- [ ] ¿El governance layer es opt-in o always-on?
- [ ] ¿`memory workflow outline` se reemplaza por CLOOP o conviven?

---

## 8. Historial de cambios

| Fecha | Cambio |
|-------|--------|
| 2026-04-23 | Creación del documento con findings de 3 auditores + exploración anchor_dope + SDD |
