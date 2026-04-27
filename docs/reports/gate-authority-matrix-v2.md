# Gate Authority Matrix v2 — tmux_fork

> Generated: 2026-04-26 | Revision of: gate-authority-matrix.md (v1)
> Method: Reclassification of all gates using 8 explicit categories
> Principle: Un gate solo es efectivo si la skill actual lo invoca en el flujo real. Evidence != authority.
> Rule: No declarar production-ready, frictionless, autonomous ni SSOT cerrado.

---

## 1. Resumen Ejecutivo

### Inventario Total

| Categoría | Definición | Cantidad | Bloquea hoy? |
|-----------|-----------|----------|-------------|
| **HARD_EXECUTABLE_INVOKED** | Script con exit code que bloquea dentro del flujo real (invocación directa por tf:*, subgate runtime de un comando, o paso implícito de init/preflight) | **11** | **SÍ** |
| **HARD_EXECUTABLE_AVAILABLE** | Script con exit code, existe pero no está en el flujo 10-phase | **8** | Disponible, no invocado |
| **SOFT_EXECUTABLE** | Script que siempre devuelve exit 0 | **7** | NO |
| **PROMPT_GUIDANCE** | Instrucción en prompt que el LLM interpreta, sin código | **20** | NO |
| **SEMANTIC_GATE** | Valida corrección semántica del trabajo realizado | **0** | No existe |
| **POLICY_STANDARD** | Estándar documental que define qué verificar, no implementa verificación | **7** | N/A — no es un gate ejecutable |
| **BACKEND_FUTURE_GATE** | Gate del repo/backend con CAS/tests, no invocado por la skill | **24** | Disponible, no cableado |
| **BROKEN_OR_BYPASSED** | Gate que existe pero su implementación falla bajo condiciones reales | **3** | NO — roto |
| **Total** | | **80** | |

### Aclaración de conteos v1 vs v2

| Métrica | v1 decía | v2 corrige | Razón de la diferencia |
|---------|----------|------------|----------------------|
| Gates totales | 77 | **80** | v1 sumaba 111 en la tabla resumen pero declaraba 77. v2 cuenta cada item una vez. |
| Skill scripts "HARD" | 26 | **19** (11 INVOKED + 8 AVAILABLE) | v1 contaba TA-01 como "7 gates" pero lo listaba como 1 item. v2 lo cuenta como 1 gate consolidado. v1 mezclaba invocados con disponibles. |
| Prompt-enforced | 33 | **20** | v1 heredó "33" del reporte pre-task que incluía cross-cutting. v2 cuenta solo los items explícitamente listados (PG-01 a PG-19 + SR-02 reclasificado). |
| Repo backend | 27 | **27** (24 FUTURE + 3 BROKEN) | Sin cambio. |
| Repo soft/bypassed | 11 (sin detalle) | **incluido en los 27** | v1 listaba "11" en tabla pero solo detallaba 3 bypassed. v2 integra los 8 soft en BACKEND_FUTURE_GATE. |
| QG-MINIMUM | "7 gates fallidos" | **7 POLICY_STANDARD** | No son gates fallidos. Son estándares documentales que definen criterios. |
| "Efectivos" | 26 (tabla) / 18 (texto) / 7 (sección 7) | **11 INVOKED** | v1 tenía 3 números contradictorios. v2 distingue: 11 invocados, de los cuales 7 son de calidad y 4 de infraestructura básica. |

---

## 2. Taxonomía de Gates (8 categorías)

### Definiciones

| Categoría | Qué significa | Ejemplo |
|-----------|--------------|---------|
| `HARD_EXECUTABLE_INVOKED` | Existe el script, tiene exit code real, bloquea dentro del flujo real. Incluye invocación directa por tf:*, subgates internos de comandos, y pasos implícitos de init/preflight | `enforce-envelope` invocado por `tf:consolidate` |
| `HARD_EXECUTABLE_AVAILABLE` | Existe el script, tiene exit code real, pero ningún prompt tf:* lo invoca directamente | `detect-env` existe pero no aparece en ningún tf:*.md |
| `SOFT_EXECUTABLE` | Existe el script, siempre devuelve exit 0, informa pero nunca bloquea | `trifecta-auto-sync` |
| `PROMPT_GUIDANCE` | Instrucción en un prompt o documento que el LLM interpreta. Sin código, sin exit code, sin verificación externa. | "STOP. Present the plan" en `tf:plan.md` |
| `SEMANTIC_GATE` | Valida corrección semántica del trabajo (no solo formato). Requiere juicio o test específico. | No existe hoy. |
| `POLICY_STANDARD` | Estándar documental que define qué propiedades verificar. No es un gate ejecutable — es el criterio contra el cual medir. | `QUALITY-GATES-MINIMUM.md` Gate A: Authority |
| `BACKEND_FUTURE_GATE` | Gate del repo/backend con código robusto (CAS, tests), pero la skill actual no lo invoca. Pertenece a otra capa. | `AgentLaunchLifecycleService.request_launch()` |
| `BROKEN_OR_BYPASSED` | Gate que existe pero falla bajo condiciones normales o se bypassa internamente. | `state.py` json.dump sin atomic write |

---

## 3. Matriz por Capa

### CAPA A: Skill Actual (orquestador que ejecuta hoy)

#### A1. HARD_EXECUTABLE_INVOKED (11 gates)

Gates con código ejecutable que bloquean dentro del flujo real. Se clasifican por tipo de invocación:
- **DIRECT_PROMPT**: el prompt tf:* invoca explícitamente el script con verificación de exit code.
- **RUNTIME_SUBGATE**: se ejecuta como paso interno de un comando que el prompt invoca (ej: `tmux-live launch` ejecuta dedup check internamente).
- **IMPLIED_INIT**: se ejecuta como paso implícito de inicialización/preflight, sin mención explícita en el prompt.

| gate_id | Propósito | Script | Invocado por | Invocation type | Fase | Bloqueo | Bats tests |
|---------|-----------|--------|-------------|-----------------|------|---------|------------|
| EE-01 | Validar formato envelope sub-agent | `enforce-envelope` | `tf:consolidate.md:34` | DIRECT_PROMPT | 5 Consolidate | Exit 1 = CRITICAL | 12/12 pass |
| CD-01 | Detectar conflictos file-level | `conflict-detect` | `tf:consolidate.md:35` | DIRECT_PROMPT | 5 Consolidate | Exit 2 = overlap | 33/33 pass |
| MR-01 | Evaluar calidad del plan (PLAN_QUALITY_GATE) | `mr-plan-eval` | `tf:cleanup.md:37` | DIRECT_PROMPT | 6.5 Evaluation | Exit code = verdict | 8/8 pass |
| SR-01 | Resolver skills por rol | `skill-resolver` | `tf:spawn.md:60` | DIRECT_PROMPT | 3 Spawn | Exit 1 = sin input | 15/15 pass |
| TL-01 | Prevenir agentes duplicados | `tmux-live:284` | `tf:spawn.md` | RUNTIME_SUBGATE | 3 Spawn | Return 1 = colisión | 20/20 pass |
| TL-02 | Verificar spawn exitoso | `tmux-live:398` | `tf:spawn.md` | RUNTIME_SUBGATE | 3 Spawn | Exit 1 = no arrancó | 20/20 pass |
| TL-03 | Timeout de agent | `tmux-live:655` | `tf:consolidate.md` | RUNTIME_SUBGATE | 5 Consolidate | Exit 1 = timeout | 20/20 pass |
| TL-04 | Validar chain files | `tmux-live:1071` | `tf:orchestrate.md` | RUNTIME_SUBGATE | 3-6 Chain | Exit 1 = invalid | 20/20 pass |
| TL-05 | Verificar pane creation | `tmux-live:326` | `tf:spawn.md` | RUNTIME_SUBGATE | 3 Spawn | Exit 1 = fail | 20/20 pass |
| TM-01 | Verificar Trifecta binary | `trifecta_manager.sh:23` | `tf:init.md` | IMPLIED_INIT | 0 Init | Exit 1 = no binary | 14/14 pass |
| TA-01 | Validar args de trifecta scripts | `trifecta-*.sh` (conjunto) | `tf:init.md` | IMPLIED_INIT | 0-1 Pre-flight | Exit 1 = bad args | 82/82 pass |

**Nota sobre TA-01**: Los scripts `trifecta-affected-symbols`, `trifecta-ast-snippet`, `trifecta-auto-sync`, `trifecta-context-inject`, `trifecta-daemon-warmup`, `trifecta-preload`, `trifecta-quality-report`, `trifecta-session-log`, `trifecta-verifier-check` comparten el mismo patrón de input arg validation. Se cuentan como 1 gate consolidado.

**Subtotal: 11 gates. De estos, 4 protegen calidad (EE-01, CD-01, MR-01, SR-01) y 7 protegen infraestructura (TL-* TM-01, TA-01).**

#### A2. HARD_EXECUTABLE_AVAILABLE (8 gates)

Gates con código ejecutable, con exit code real, pero sin invocación directa en el flujo 10-phase.

| gate_id | Propósito | Script | Gap | Potencial |
|---------|-----------|--------|-----|-----------|
| DE-01 | Detectar entorno proyecto (stack, lang) | `detect-env` | No aparece en ningún tf:*.md | Integrable en tf:init |
| WA-01 | Observar output de agent en vivo | `watch-agent` | No invocado por ningún tf:*.md | Utilidad para monitoring |
| RT-01 | Extraer turns de conversación | `read-turn` | No invocado por ningún tf:*.md | Utilidad para consolidate |
| JV-01 | Visualizar JSON de agent output | `json-vis` | No invocado por ningún tf:*.md | Utilidad para debugging |
| TL-06 | TMUX env var check | `tmux-live:200` | Se ejecuta dentro de tmux-live pero no como gate explícito en prompt | Runtime prerequisite |
| TL-07 | Agent exit code propagation | `tmux-live:630,646` | Se ejecuta dentro de tmux-live wait | Post-completion check |
| TP-01 | Preload de contexto Trifecta | `trifecta-preload` | Invocado implícitamente pero sin gate explícito en prompt | Pre-flight candidate |
| TL-08 | Chain step failure propagation | `tmux-live:1121` | Se ejecuta dentro de chain execution | Runtime safety |

**Subtotal: 8 gates disponibles, no invocados.**

#### A3. SOFT_EXECUTABLE (7 gates)

Gates con código ejecutable que siempre devuelven exit 0. Informan pero nunca bloquean.

| gate_id | Propósito | Script | Comportamiento |
|---------|-----------|--------|---------------|
| TS-01 | Trifecta LSP binary check | `trifecta_manager.sh:97` | Warn, continúa AST-only |
| TS-02 | Trifecta auto-sync | `trifecta-auto-sync` | Exit 0 siempre |
| TS-03 | Trifecta daemon warmup | `trifecta-daemon-warmup` | Exit 0 siempre |
| TS-04 | Trifecta session log | `trifecta-session-log` | Exit 0 siempre |
| TS-05 | Trifecta verifier check | `trifecta-verifier-check` | Exit 0 siempre |
| TS-06 | tmux-live concurrency advisory | `tmux-live` | Warning, no bloquea |
| TS-07 | Fork doctor status | `tmux-live` / `fork doctor` | Report only |

**Subtotal: 7 gates. Ninguno bloquea.**

#### A4. PROMPT_GUIDANCE (20 gates)

Instrucciones en prompts o documentos que el LLM interpreta. Sin código, sin exit code, sin verificación externa. El LLM puede cumplirlas o ignorarlas sin consecuencia automática.

| gate_id | Propósito | Documentado en | Claimed severity | Poder real |
|---------|-----------|---------------|-----------------|------------|
| PG-01 | Plan Gate (aprobación humana) | `protocol.md §1.5`, `tf:plan.md:38` | STOP | LLM decide si para |
| PG-02 | Pre-flight check (8 sub-checks) | `protocol.md §1.6` | FAIL_ABORT | LLM decide si aborta |
| PG-03 | Acceptance criteria check | `protocol.md §1.6.1` | FAIL_RETRY | LLM judgment |
| PG-04 | TDD flag enforcement | `protocol.md §1.6.3` | WARN | Flag sin verificación |
| PG-05 | Clean state verification | `protocol.md §1.6.7` | FAIL_ABORT | No corre pytest/ruff |
| PG-06 | Metrics validation | `protocol.md §1.6.8` | FAIL_RETRY | No valida existencia |
| PG-07 | Spec compliance | `protocol.md §5.5` | FAIL | LLM interpreta specs |
| PG-08 | TDD compliance | `protocol.md §5.5` | FAIL | LLM interpreta |
| PG-09 | Remediation loop (max 3) | `protocol.md §5.5` | FAIL_FINAL | pi-tasks no tiene FAIL_FINAL |
| PG-10 | Gate blocking on FAIL | `protocol.md §5.5` | STOP | LLM self-enforced |
| PG-11 | Static analysis threshold | `protocol.md §5.7` | >5=ESCALATE | LLM no corre static analysis |
| PG-12 | Escalation timeout (5min) | `protocol.md §5.7` | FAIL_ABORT | LLM no mide tiempo |
| PG-13 | Human override (AV2) | `governance.md:223` | Advisory | Documenta evento |
| PG-14 | Coverage gap detection | `governance.md:63` | CRITICAL=FAIL | LLM judgment |
| PG-15 | Quality checklist (spec-kit) | `governance.md:83` | FAIL on CRITICAL | spec-kit no existe |
| PG-16 | GateResult enum enforcement | `protocol.md:73` | FAIL_ABORT/FAIL_RETRY | Enum aspiracional |
| PG-17 | SSOT Memory MCP enforcement | `state-format.md:5` | SSOT declarado | LLM puede consultar pi-tasks |
| PG-18 | Phase count consistency | `SKILL.md` vs docs legacy | — | Inconsistencia documental |
| PG-19 | Plan gate optional vs mandatory | `AGENTS.md` vs `protocol.md` | STOP vs optional | Contradicción |
| PG-20 | Skill injection abort on failure | `tf:plan.md:52,71` | FAIL_ABORT | Prompt dice ABORT, sin exit code check |

**Subtotal: 20 gates. Ninguno bloquea automáticamente. El LLM puede ignorar todos.**

#### A5. SEMANTIC_GATE (0 gates)

No existe ningún gate que valide la corrección semántica del trabajo realizado por los sub-agentes.

`enforce-envelope` valida formato (campos existen, artifacts existen en disco). No valida que el contenido sea correcto, que los tests pasen, que el código compile, o que el plan sea coherente.

`mr-plan-eval` evalúa calidad del plan por criterios documentales. Es un **PLAN_QUALITY_GATE** (evalúa el documento del plan antes de proceder), no un SEMANTIC_GATE de resultado implementado. Un SEMANTIC_GATE validaría que el trabajo producido cumple las specs — eso no existe hoy.

**Este es el gap más significativo: el flujo 10-phase no tiene verificación automática de corrección semántica.**

---

### CAPA B: QUALITY-GATES-MINIMUM (estándar documental)

#### B1. POLICY_STANDARD (7 estándares)

Estos NO son gates ejecutables. Son criterios documentales que definen qué propiedades verificar. Se usan para evaluar si un gate ejecutable es suficiente, no como gates en sí mismos.

| gate_id | Nombre | Criterio que define | Uso correcto |
|---------|--------|--------------------| ------------|
| QG-A | Authority Gate | ¿Hay exactamente una fuente autoritativa para esta superficie? | Evaluar si HARD_EXECUTABLE_INVOKED es suficiente |
| QG-B | Evidence vs Authority | ¿Evidencia informa, autoridad decide? | Distinguir logs/tests de decisiones |
| QG-C | Lifecycle Gate | ¿Cada transición de estado tiene owner, lock, crash safety? | Evaluar BACKEND_FUTURE_GATE |
| QG-D | Ownership Gate | ¿Exactamente un componente posee esta responsabilidad? | Detectar duplicaciones |
| QG-E | Scope Gate | ¿Es el cambio mínimo, sin sistemas paralelos? | Prevenir scope creep |
| QG-F | Validation Gate | ¿Qué significa "pass" en términos precisos, con test reproducible? | Diseñar SEMANTIC_GATE futuro |
| QG-G | Claim Discipline Gate | ¿El claim está soportado por evidencia? | Auditar PROMPT_GUIDANCE claims |

**Uso**: Cuando se diseñe un HARD_EXECUTABLE_INVOKED nuevo, debe pasar los 7 estándares QG. No se aplican como gates runtime.

---

### CAPA C: Repo/Backend Futuro (no invocado por la skill actual)

#### C1. BACKEND_FUTURE_GATE (24 gates)

Gates con código robusto (CAS, transition maps, exceptions, tests). Existen en el repo. La skill actual no los invoca en ningún punto del flujo 10-phase. Pertenecen a la capa del backend.

| gate_id | Servicio | Mecanismo | Tests | Nota |
|---------|----------|-----------|-------|------|
| RB-01 | `AgentLaunchLifecycleService.request_launch()` | Partial unique index + CAS | 14 | Gate más importante no cableado |
| RB-02 | `AgentLaunchRepository.claim()` | CAS INSERT | 21 | Dedup por canonical key |
| RB-03 | `AgentLaunchRepository.cas_update_status()` | CAS WHERE | 21 | Transiciones atómicas |
| RB-04 | `AgentLaunchLifecycleService.confirm_spawning()` | CAS | 14 | Post-spawn verification |
| RB-05 | `AgentLaunchLifecycleService.confirm_active()` | CAS | 14 | Active state confirm |
| RB-06 | `AgentLaunchLifecycleService.quarantine()` | CAS | 14 | Failed agent isolation |
| RB-07 | `TaskBoardService.submit_plan()` | Transition + CAS | SÍ | Task lifecycle |
| RB-08 | `TaskBoardService.approve()` | Transition + CAS | SÍ | Task lifecycle |
| RB-09 | `TaskBoardService.reject()` | Transition + CAS | SÍ | Task lifecycle |
| RB-10 | `TaskBoardService.start()` | blocked_by + transition + CAS | SÍ | Dependency guard |
| RB-11 | `TaskBoardService.complete()` | Transition + CAS | SÍ | Task lifecycle |
| RB-12 | `OrchestrationTaskRepository.cas_save()` | CAS WHERE | SÍ | Atomic save |
| RB-13 | `PollRun._VALID_TRANSITIONS` | Transition dict | 21 | Poll lifecycle |
| RB-14 | `AgentPollingService.poll_once()` | Concurrency cap + lifecycle | SÍ | Full polling guard |
| RB-15 | `AgentPollingService._spawn_run()` | claim→spawn→confirm | SÍ | Full lifecycle |
| RB-16 | `PromiseContract.can_transition_to()` | Transition dict | SÍ | Contract lifecycle |
| RB-17 | `workflow._validate_phase_transition()` | Phase enum whitelist | 9 | Workflow phases |
| RB-18 | `workflow.ship()` verify gate | unlock_ship boolean | SÍ | Ship safety |
| RB-19 | `workflow.ship()` preflight gate | Dirty tree + worktree | SÍ | Ship safety |
| RB-20 | `AgentManager.spawn_agent()` | Dict dedup + lifecycle | 11 | Spawn dedup |
| RB-21 | `TmuxCircuitBreaker.can_execute()` | State + threshold | SÍ | Failure protection |
| RB-22 | `InMemoryRateLimiter` | 429 response | PARCIAL | Rate limiting |
| RB-23 | `HybridDispatcher` content validation | ValueError | NO | Content safety |
| RB-24 | `HybridDispatcher` MCP require gate | RuntimeError | NO | Dependency check |

**Subtotal: 24 gates. Ninguno invocado por la skill. La mayoría tiene tests; algunos están en estado parcial o sin cobertura (RB-22: PARCIAL, RB-23/RB-24: NO).**

#### C2. BROKEN_OR_BYPASSED (3 gates)

Gates que existen en el repo pero fallan bajo condiciones normales.

| gate_id | Servicio | Bug | Impacto |
|---------|----------|-----|---------|
| RB-25 | `state.py:247,370,490` WorkflowState save | `json.dump()` sin temp+rename | Crash corrompe .claude/*.json |
| RB-26 | `promise_contract.py:137` transition_to() | Sin expected-status en CAS | Transiciones concurrentes se sobreescriben |
| RB-27 | `task_board_service.py` retry() | Usa `save()` no `cas_save()` | CAS bypass en retry path |

**Subtotal: 3 gates rotos. Deben repararse antes de cablear cualquier integración skill↔repo.**

---

## 4. enforce-envelope: Contrato de Salida

`enforce-envelope` es un **contrato de formato de salida**, no un juez semántico.

### Qué hace
- Verifica que los 6 campos requeridos existen en el output (Status, Summary, Artifacts, Next, Risks, Skill Resolution)
- Verifica que Status tiene valor válido (success/partial/blocked)
- Parsea Artifacts con bracket stripping: `[a.md, b.md]` → `a.md, b.md`
- Verifica que cada artifact existe en disco
- Sanitiza secuencias OSC del output

### Qué NO hace
- No valida que el contenido de Summary sea correcto
- No valida que los artifacts contengan código que compile
- No valida que los tests pasen
- No valida que el plan sea coherente
- No juzga la calidad del trabajo realizado

### Estado del bracket parsing

**FIXED.** El script hace:
```bash
ARTIFACTS_LINE="${ARTIFACTS_LINE//\[/}"
ARTIFACTS_LINE="${ARTIFACTS_LINE//\]/}"
```

**Tests**: 12/12 bats tests pasan (verificado 2026-04-26). Incluye 3 regresión tests específicos para bracket parsing. Tests persistentes, no validación manual.

---

## 5. tf:* Prompts — Cobertura de Envelope

6 de 7 prompts definen envelope inline con `## FORK_START ##` / `## FORK_END ##`:

| Prompt | Envelope | Referencia scripts de validación |
|--------|----------|--------------------------------|
| `tf:init.md` | SÍ | — |
| `tf:plan.md` | SÍ | skill-resolver |
| `tf:spawn.md` | SÍ | skill-resolver, trifecta-context-inject |
| `tf:consolidate.md` | SÍ | enforce-envelope, conflict-detect |
| `tf:validate.md` | SÍ | — |
| `tf:cleanup.md` | SÍ | mr-plan-eval |
| `tf:orchestrate.md` | Formato tabla (no envelope inline) | enforce-envelope, conflict-detect, mr-plan-eval |

Los 12 bats tests de `enforce-envelope` son los tests de formato efectivos. No existen tests unitarios adicionales de formato de prompts — los prompts son plantillas de texto.

---

## 6. Recursos: Estado de Accesibilidad

| Tipo | Cantidad | Mecanismo de acceso |
|------|----------|-------------------|
| Directamente referenciados por tf:* o SKILL.md | 8 | Carga explícita |
| Trifecta-searchable (no referenciados por nombre) | 13 | Búsqueda semántica bajo demanda |
| Archive (histórico) | 5 | Solo lectura histórica |
| Totalmente huérfanos (inaccesibles) | **0** | — |

No hay recursos completamente huérfanos. Los 13 Trifecta-searchable son accesibles via `trifecta ctx search`.

---

## 7. Boundary Decision: Skill ↔ Repo/Backend

### Principios

1. **`tmux-live` no debe depender de internals del repo/backend.** Si `tmux-live` importa SQLite, SQLAlchemy models, o servicios internos del repo, se crea acoplamiento que rompe la separación de capas. La comunicación debe ser por CLI/API estable.

2. **Cualquier integración futura debe hacerse por CLI estable.** El contrato es: `tmux-live launch` llama un comando CLI del repo (ej: `fork launch request --canonical-key KEY`), recibe un JSON con `decision=claimed|suppressed|error`, y actúa en consecuencia. No hay import de Python, no hay shared state.

3. **Antes de cablear, crear `SKILL-REPO-BOUNDARY-GATE.md`.** Este documento debe definir:
   - Contrato de borde exacto (CLI commands, JSON schema, exit codes)
   - Qué pasa si el backend no está disponible (fallback graceful)
   - Qué pasa si el backend rechaza el launch (suppressed → skip agent)
   - Rollback: qué hace la skill si el backend falla mid-launch
   - Tests de contrato: bats tests que validan el CLI interface sin depender del backend

### Por qué no cablear directamente

- El repo tiene 3 gates BROKEN_OR_BYPASSED (RB-25, RB-26, RB-27). Cablear antes de reparar estos gates introduce dependencia en código roto.
- El repo es internamente inconsistente: `workflow.py` bug-hunt llama `tmux-live` que bypassa su propio `AgentLaunchLifecycleService`.
- No existe `SKILL-REPO-BOUNDARY-GATE.md` que defina el contrato de borde.

### Secuencia correcta

1. Crear `SKILL-REPO-BOUNDARY-GATE.md` (contrato de borde — prerrequisito para todo lo demás)
2. Reparar RB-25, RB-26, RB-27 (gates rotos del backend)
3. Implementar CLI/API estable en el repo (`fork launch request`)
4. Cablear `tmux-live launch` solo contra esa CLI/API (no a internals)
5. Agregar bats tests de contrato

---

## 8. Contradicciones Restantes

| # | Contradicción | Origen | Impacto | Prioridad |
|---|--------------|--------|---------|-----------|
| C1 | Plan gate: AGENTS.md "optional", protocol.md "STOP" | `AGENTS.md:38` vs `protocol.md:47` | Agente puede saltear aprobación | **P0** |
| C2 | SSOT: SKILL.md "Task list is source of truth", state-format.md "Memory MCP is SSOT" | `SKILL.md:84` vs `state-format.md:5` | Doble autoridad divergente | **P0** |
| C3 | Governance: "advisory-only" vs "FAIL_ABORT" | `governance.md:4,80` | Falsa confianza en blocking | P2 |
| C4 | Phase count: 12 vs 10 | fork-run.md vs SKILL.md | Confusión | P2 |
| C5 | Skill bypassa AgentLaunchLifecycleService | Skill no llama repo gates | Spawns sin dedup/lease | **P0** (post-boundary) |
| C6 | TaskBoardService.retry() CAS bypass | `task_board_service.py` | CAS bypass interno | P1 |
| C7 | Repo workflow.py llama tmux-live bypassando lifecycle propio | `workflow.py` | Repo internamente inconsistente | P1 |

---

## 9. Recomendaciones

### P0 — Decisiones que bloquean progreso

| # | Recomendación | Razón |
|---|--------------|-------|
| P0-1 | **Resolver C1: unificar Plan Gate mandatory/optional** | AGENTS.md y protocol.md dan instrucciones contradictorias. El agente no sabe si pedir aprobación o proceder. Unificar en una respuesta: si la contradicción existe, el agente defaultea a "no para". |
| P0-2 | **Resolver C2: declarar una SSOT** | Dos fuentes claiman autoridad sobre phase progress. Memory MCP y pi-tasks pueden diverger. Decidir cuál es la autoridad, cuál es la vista, y documentarlo. |
| P0-3 | **Definir boundary skill ↔ repo/backend** | Antes de cablear nada, crear `SKILL-REPO-BOUNDARY-GATE.md` con contrato explícito. Sin contrato, cualquier integración es acoplamiento ad-hoc. |

### P1 — Gates ejecutables que faltan

| # | Recomendación | Razón |
|---|--------------|-------|
| P1-1 | **Crear PRE-TASK-GATES-ORCHESTRATOR.md** | Documentar qué gates protegen plan→implementación con código real (HARD_EXECUTABLE_INVOKED) vs PROMPT_GUIDANCE. Es el primer Next Step de QG-MINIMUM. |
| P1-2 | **Endurecer G1.6 Pre-flight Check** | 6 de 8 sub-checks son PROMPT_GUIDANCE. Convertir a HARD_EXECUTABLE_AVAILABLE o HARD_EXECUTABLE_INVOKED. |
| P1-3 | **Crear SEMANTIC_GATE separado** | `enforce-envelope` es contrato de formato. Un gate semántico nuevo debe validar que: tests pasen, código compile, plan sea coherente. No mezclar con formato. |
| P1-4 | **Reparar RB-25, RB-26, RB-27** | Gates rotos del backend. Prerrequisito para cualquier cableado futuro. |

### P2 — Documentación y limpieza

| # | Recomendación | Razón |
|---|--------------|-------|
| P2-1 | **Crear RC-CLOSURE-GATE.md** | Template para cierres de RC. |
| P2-2 | **Crear BACKEND-LIFECYCLE-GATE.md** | Gates para servicios code-first del repo. |
| P2-3 | **Resolver C3: governance advisory vs FAIL_ABORT** | Cambiar línea 4 de governance.md a: "Advisory LLM guidelines. GateResult describes expected behavior, not enforced behavior." |
| P2-4 | **Resolver C4: unificar phase count a 10** | fork-run.md debe decir 10-phase. |
| P2-5 | **Documentar recursos Trifecta-searchable** | Los 13 recursos accesibles via search deben estar documentados en README. |
| P2-6 | **Agregar TDD enforcement en tf:validate** | Si STRICT_TDD fue seteado, verificar que test files existan para código modificado. |
| P2-7 | **Mapear skill-gates-fix-list.md a contextos correctos** | Cada fix pertenece a un contexto (pre-task, RC closure, backend, boundary). Aplicar fixes al contexto equivocado recrea el problema. |

---

## 10. Tabla de Decisión Final

| Pregunta | Respuesta | Gates |
|----------|-----------|-------|
| **Qué bloquea hoy** | 11 HARD_EXECUTABLE_INVOKED: 4 de calidad (envelope, conflicts, plan eval, skill resolution) + 7 de infraestructura (tmux-live, trifecta). | EE-01, CD-01, MR-01, SR-01, TL-01..05, TM-01, TA-01 |
| **Qué solo orienta** | 20 PROMPT_GUIDANCE + 7 SOFT_EXECUTABLE = 27 instrucciones sin poder de bloqueo automático. | PG-01..20, TS-01..07 |
| **Qué pertenece al backend futuro** | 24 BACKEND_FUTURE_GATE con CAS/tests, no cableados a la skill. | RB-01..24 |
| **Qué define criterios transversales** | 7 POLICY_STANDARD que definen qué propiedades verificar. No son gates ejecutables, no pertenecen al backend. Son el estándar contra el cual medir. | QG-A..G |
| **Qué está roto** | 3 BROKEN_OR_BYPASSED en el repo backend. | RB-25, RB-26, RB-27 |
| **Qué falta para impedir planes malos** | 1 SEMANTIC_GATE (no existe), 1 boundary contract (no existe), 2 contradicciones P0 sin resolver (C1, C2). | Gap de diseño, no de implementación |

---

## 11. Criterio de Aceptación

| Criterio | Cumplido? | Evidencia |
|----------|-----------|-----------|
| Los números cuadran | **SÍ** | 11+8+7+20+0+7+24+3 = 80 total. Cada item contado una vez. |
| Se puede usar como fuente de decisión | **SÍ** | Categorías explícitas, capa separada, recomendaciones priorizadas. |
| Gates decorativos no se venden como protección real | **SÍ** | PROMPT_GUIDANCE y SOFT_EXECUTABLE clasificados como "no bloquea". |
| No recomienda acoplar skill y backend sin contrato de frontera | **SÍ** | Sección 7 define secuencia: reparar → contrato → CLI → cablear → tests. |
| Evidence != authority | **SÍ** | Tests, logs, reports clasificados como evidencia. Authority es el componente que decide. |
