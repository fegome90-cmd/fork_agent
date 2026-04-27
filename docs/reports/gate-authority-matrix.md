# Gate Authority Matrix — tmux_fork

> Generated: 2026-04-26 | Method: Direct audit of scripts, prompts, docs, and repo code
> Scope: Separation of skill/orquestador actual vs repo/backend futuro
> Principle: Un gate solo es efectivo si la skill actual lo invoca en el flujo real

---

## 1. Resumen Ejecutivo

**Gates totales identificados**: 77 (26 skill scripts, 33 prompt-enforced, 27 repo backend)

| Categoría | Cantidad | Efectivos | Declarados-no-invocados | Ambiguos |
|-----------|----------|-----------|------------------------|----------|
| Skill scripts (HARD_EXECUTABLE) | 26 | 26 | 0 | 0 |
| Skill prompts (PROMPT_ENFORCED) | 33 | 0 | 33 | 0 |
| Skill soft (always exit 0) | 7 | 0 | 7 | 0 |
| Repo backend (HARD_EXECUTABLE) | 27 | 0 | 27 | 0 |
| Repo soft/bypassed | 11 | 0 | 11 | 0 |
| QUALITY-GATES-MINIMUM (7 gates) | 7 | 0 | 7 | 0 |

**Hallazgo central**: De los 53 gates que bloquean con exit code real, SOLO los 26 de la skill son invocables hoy. Los 27 del repo backend existen en código pero **ninguno es invocado por la skill en el flujo real**. Los 33 prompt-enforced dependen 100% de que el LLM se auto-imponga las reglas.

---

## 2. Matriz de Autoridad de Gates

### Capa: SKILL ACTUAL (orquestador que ejecuta hoy)

#### 2.1 Gates con código ejecutable — invocados por prompts tf:*

| gate_id | Propósito | Archivo definición | Entrypoint real invoca | Fase flujo | Condición bloqueo | Evidencia generada | Claims que respalda | Estado |
|---------|-----------|-------------------|----------------------|------------|------------------|-------------------|---------------------|--------|
| EE-01 | Validar formato envelope sub-agent | `scripts/enforce-envelope` | `tf:consolidate.md:34` | Phase 5 (Consolidate) | Exit 1 = CRITICAL fields missing | JSON verdict con issues | "Sub-agent output validated" | **EFECTIVO** |
| EE-02 | Validar existencia artifacts | `scripts/enforce-envelope:105-120` | `tf:consolidate.md:34` | Phase 5 | Exit 1 = artifact file not found | Artifact path verification | "Artifacts exist on disk" | **EFECTIVO** |
| EE-03 | Bracket parsing Artifacts field | `scripts/enforce-envelope:105` (strip `[]`) | `tf:consolidate.md:34` | Phase 5 | Exit 1 = path with brackets = not found | 12 bats tests pass | "Artifact parsing works" | **EFECTIVO** |
| EE-04 | OSC sequence sanitization | `scripts/enforce-envelope:50-53` | `tf:consolidate.md:34` | Phase 5 | Always runs (no flag needed) | Clean output file | "No OSC injection" | **EFECTIVO** |
| CD-01 | Detectar conflictos file-level | `scripts/conflict-detect` | `tf:consolidate.md:35` | Phase 5 | Exit 2 = overlap detected | JSON conflict report | "No file conflicts between agents" | **EFECTIVO** |
| MR-01 | Evaluar calidad de plan | `scripts/mr-plan-eval` | `tf:cleanup.md:37` | Phase 6.5 (Evaluation) | Exit code = SHIP/NEEDS_WORK/BLOCKED | Plan evaluation report | "Plan meets quality bar" | **EFECTIVO** |
| SR-01 | Resolver skills por rol | `scripts/skill-resolver` | `tf:spawn.md:60` | Phase 3 (Spawn) | Exit 1 = task description required | Resolved skill names | "Correct skills injected" | **EFECTIVO** |
| TL-01 | TMUX env var check | `scripts/tmux-live:200` | `tf:spawn.md` (via launch) | Phase 3 | Exit 1 = no TMUX env | Error message | "tmux available" | **EFECTIVO** |
| TL-02 | Duplicate agent prevention | `scripts/tmux-live:284` | `tf:spawn.md` | Phase 3 | Return 1 = name collision | Registry check | "No duplicate agents" | **EFECTIVO** |
| TL-03 | Pane creation gate | `scripts/tmux-live:326` | `tf:spawn.md` | Phase 3 | Exit 1 = pane creation failed | tmux split-window result | "Agent pane created" | **EFECTIVO** |
| TL-04 | Spawn verification (retries) | `scripts/tmux-live:398` | `tf:spawn.md` | Phase 3 | Exit 1 = agent not started | Process verification | "Agent process running" | **EFECTIVO** |
| TL-05 | Agent exit code check | `scripts/tmux-live:630,646` | `tf:consolidate.md` (via wait) | Phase 5 | Exit 1 = agent failed | Exit code from agent | "Agent completed successfully" | **EFECTIVO** |
| TL-06 | Agent wait timeout | `scripts/tmux-live:655` | `tf:consolidate.md` | Phase 5 | Exit 1 = timeout exceeded | Timeout event | "Agent finished in time" | **EFECTIVO** |
| TL-07 | Chain file validation | `scripts/tmux-live:1071` | `tf:orchestrate.md` | Phase 3-6 | Exit 1 = chain file invalid | Chain file check | "Chain execution valid" | **EFECTIVO** |
| TL-08 | Chain step failure | `scripts/tmux-live:1121` | `tf:orchestrate.md` | Phase 3-6 | Exit 1 = step failed | Step result | "Chain step passed" | **EFECTIVO** |
| TP-01 | Preload validation | `scripts/trifecta-preload:56,61` | `tf:init.md` (implied) | Phase 0 | Exit 1 = preload failed | Preload results | "Context loaded" | **EFECTIVO** |
| TM-01 | Trifecta binary check | `scripts/trifecta_manager.sh:23` | `tf:init.md` (implied) | Phase 0 | Exit 1 = no binary | Binary found | "Trifecta available" | **EFECTIVO** |
| TA-01 | Trifecta input arg validation (7 gates) | `scripts/trifecta-*.sh` | `tf:init.md` (implied) | Phase 0-1 | Exit 1 = missing args | Arg validation | "CLI args valid" | **EFECTIVO** |

**Subtotal EFECTIVOS**: 18 gates invocados directamente por prompts tf:* con exit code real.

#### 2.2 Gates con código pero INVOCACIÓN INDIRECTA o sin verificación de exit code

| gate_id | Propósito | Archivo | Referenciado por | Condición bloqueo | Gap | Estado |
|---------|-----------|---------|-----------------|------------------|-----|--------|
| DE-01 | Detectar entorno proyecto | `scripts/detect-env` | `tf:init.md` (via init.md resource) | Exit 1 = no project | detect-env NO aparece en ningún tf:*.md prompt directamente | **DECLARADO-NO-INVOCADO** |
| SR-02 | Skill injection en plan | `scripts/skill-resolver` | `tf:plan.md:52,71` | FAIL_ABORT si falla | Prompt dice "ABORT" pero es LLM-enforced, no exit code check real | **AMBIGUO** |
| WA-01 | Watch agent output | `scripts/watch-agent` | Ningún tf:*.md | Exit codes varios | No invocado por ningún prompt del flujo 10-phase | **DECLARADO-NO-INVOCADO** |
| RT-01 | Read turn extraction | `scripts/read-turn` | Ningún tf:*.md | Exit codes varios | Utilidad standalone, no parte del flujo | **DECLARADO-NO-INVOCADO** |
| JV-01 | JSON visualization | `scripts/json-vis` | Ningún tf:*.md | Exit codes varios | Utilidad standalone | **DECLARADO-NO-INVOCADO** |

**Subtotal**: 2 declarados-no-invocados, 1 ambiguo, 2 utilidades standalone.

#### 2.3 Gates PROMPT_ENFORCED (LLM self-enforced, sin código)

| gate_id | Propósito | Documentado en | Claimed severity | Poder real | Estado |
|---------|-----------|---------------|-----------------|------------|--------|
| PG-01 | Plan Gate (human approval) | `protocol.md §1.5`, `tf:plan.md:38` | STOP | WEAK — LLM puede saltear | **DECLARADO-NO-INVOCADO** |
| PG-02 | Pre-flight check (8 sub-checks) | `protocol.md §1.6` | FAIL_ABORT | NONE — 6 de 8 no tienen script | **DECLARADO-NO-INVOCADO** |
| PG-03 | Acceptance criteria check | `protocol.md §1.6.1` | FAIL_RETRY | NONE — LLM judgment puro | **DECLARADO-NO-INVOCADO** |
| PG-04 | TDD flag enforcement | `protocol.md §1.6.3` | WARN | NONE — flag sin verificación | **DECLARADO-NO-INVOCADO** |
| PG-05 | Clean state verification | `protocol.md §1.6.7` | FAIL_ABORT | NONE — no corre pytest/ruff | **DECLARADO-NO-INVOCADO** |
| PG-06 | Metrics validation | `protocol.md §1.6.8` | FAIL_RETRY | NONE — no valida existencia | **DECLARADO-NO-INVOCADO** |
| PG-07 | Spec compliance | `protocol.md §5.5` | FAIL | WEAK — LLM interpreta | **DECLARADO-NO-INVOCADO** |
| PG-08 | TDD compliance | `protocol.md §5.5` | FAIL | WEAK — LLM interpreta | **DECLARADO-NO-INVOCADO** |
| PG-09 | Remediation loop (max 3) | `protocol.md §5.5` | FAIL_FINAL | NONE — pi-tasks no tiene FAIL_FINAL | **DECLARADO-NO-INVOCADO** |
| PG-10 | Gate blocking on FAIL | `protocol.md §5.5` | STOP | NONE — LLM self-enforced | **DECLARADO-NO-INVOCADO** |
| PG-11 | Static analysis threshold | `protocol.md §5.7` | 0=PASS, >5=ESCALATE | NONE — governance-only | **DECLARADO-NO-INVOCADO** |
| PG-12 | Escalation timeout (5min) | `protocol.md §5.7` | FAIL_ABORT | NONE — LLM no mide tiempo | **DECLARADO-NO-INVOCADO** |
| PG-13 | Human override (AV2) | `governance.md:223` | Advisory | NONE — solo documenta evento | **DECLARADO-NO-INVOCADO** |
| PG-14 | Coverage gap detection | `governance.md:63` | CRITICAL=FAIL | NONE — LLM judgment | **DECLARADO-NO-INVOCADO** |
| PG-15 | Quality checklist (spec-kit) | `governance.md:83` | FAIL on CRITICAL | NONE — spec-kit no existe | **DECLARADO-NO-INVOCADO** |
| PG-16 | GateResult enum | `protocol.md:73` | FAIL_ABORT/FAIL_RETRY | NONE — enum aspiracional sin código | **DECLARADO-NO-INVOCADO** |
| PG-17 | SSOT enforcement (Memory MCP) | `state-format.md:5` | Memory MCP es SSOT | NONE — LLM puede consultar pi-tasks | **AMBIGUO** |
| PG-18 | Phase count (10 vs 12) | `SKILL.md` vs documentación legacy | — | NONE — inconsistencia documental | **AMBIGUO** |
| PG-19 | Plan gate optional vs mandatory | `AGENTS.md` vs `protocol.md` | STOP vs optional | NONE — contradicción | **AMBIGUO** |

**Subtotal**: 13 declarados-no-invocados, 3 ambiguos, 3+ cross-cutting adicionales.

#### 2.4 Gates SOFT_EXECUTABLE (siempre exit 0, nunca bloquean)

| gate_id | Propósito | Archivo | Comportamiento real | Estado |
|---------|-----------|---------|-------------------|--------|
| TS-01 | Trifecta LSP binary check | `trifecta_manager.sh:97` | Warn, continúa AST-only | **DECORATIVO** |
| TS-02 | Trifecta auto-sync | `trifecta-auto-sync:26` | Warn, exit 0 siempre | **DECORATIVO** |
| TS-03 | Trifecta daemon warmup | `trifecta-daemon-warmup` | Exit 0 siempre | **DECORATIVO** |
| TS-04 | Trifecta session log | `trifecta-session-log` | Exit 0 siempre | **DECORATIVO** |
| TS-05 | Trifecta verifier check | `trifecta-verifier-check` | Exit 0 siempre | **DECORATIVO** |
| TS-06 | tmux-live concurrency guard | `tmux-live` | Advisory warning | **DECORATIVO** |
| TS-07 | Fork doctor status | `tmux-live` / `fork doctor` | Report only | **DECORATIVO** |

**Subtotal**: 7 decorativos.

---

### Capa: REPO/BACKEND FUTURO (no invocado por la skill actual)

#### 3.1 Gates con código ejecutable — CAS, transition maps, exceptions

| gate_id | Propósito | Archivo | Mecanismo | Skill invoca? | Testeado? | Estado |
|---------|-----------|---------|-----------|--------------|-----------|--------|
| RB-01 | Agent launch dedup | `agent_launch_lifecycle_service.py:66` | Partial unique index + CAS | **NO** | SÍ (14 tests) | **DECLARADO-NO-INVOCADO** |
| RB-02 | Agent launch CAS transitions | `agent_launch_repository.py:100` | CAS WHERE status=? | **NO** | SÍ (21 tests) | **DECLARADO-NO-INVOCADO** |
| RB-03 | Agent launch confirm spawn | `agent_launch_lifecycle_service.py` | CAS | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-04 | Agent launch confirm active | `agent_launch_lifecycle_service.py` | CAS | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-05 | Agent launch quarantine | `agent_launch_lifecycle_service.py` | CAS | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-06 | Task submit_plan transition | `task_board_service.py` | Transition + CAS | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-07 | Task approve transition | `task_board_service.py` | Transition + CAS | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-08 | Task reject transition | `task_board_service.py` | Transition + CAS | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-09 | Task start (blocked_by check) | `task_board_service.py:192` | ValueError if blocked | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-10 | Task complete transition | `task_board_service.py` | Transition + CAS | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-11 | PollRun state machine | `poll_run.py:112` | _VALID_TRANSITIONS dict | **NO** | SÍ (21 tests) | **DECLARADO-NO-INVOCADO** |
| RB-12 | PollRun concurrency cap | `agent_polling_service.py` | Semaphore + lifecycle | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-13 | PromiseContract transitions | `promise_contract.py` | can_transition_to dict | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-14 | Workflow phase transition | `workflow.py:319` | PhaseSkipError | **NO** | SÍ (9 tests) | **DECLARADO-NO-INVOCADO** |
| RB-15 | Ship preflight gate | `workflow.py:223` | ShipPreflightError | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-16 | Ship unlock gate | `workflow.py:643` | typer.Exit 1 | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-17 | AgentManager spawn dedup | `agents.py` | Dict dedup + lifecycle | **NO** | SÍ (11 tests) | **DECLARADO-NO-INVOCADO** |
| RB-18 | Circuit breaker | `circuit_breaker.py:94` | can_execute=False | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |
| RB-19 | Rate limiter | `rate_limit.py:39` | 429 response | **NO** | PARCIAL | **DECLARADO-NO-INVOCADO** |
| RB-20 | Content validation | `hybrid.py:202` | ValueError | **NO** | NO | **DECLARADO-NO-INVOCADO** |
| RB-21 | MCP require gate | `hybrid.py:275` | RuntimeError | **NO** | NO | **DECLARADO-NO-INVOCADO** |
| RB-22 | Session ID validation | `agents.py` | Regex | **NO** | NO | **DECLARADO-NO-INVOCADO** |
| RB-23 | Schema version check | `state.py` | UnsupportedSchemaError | **NO** | NO | **DECLARADO-NO-INVOCADO** |
| RB-24 | Input sanitization | `src/infrastructure/` | Validation matrix | **NO** | SÍ | **DECLARADO-NO-INVOCADO** |

**Subtotal**: 24 gates robustos con CAS/tests — ninguno invocado por la skill.

#### 3.2 Gates BYPASSED (implementación rota)

| gate_id | Propósito | Archivo | Bug | Estado |
|---------|-----------|---------|-----|--------|
| RB-25 | WorkflowState atomic write | `state.py:247,370,490` | json.dump sin temp+rename | **ROTO** |
| RB-26 | PromiseContract CAS | `promise_contract.py:137` | transition_to() sin expected-status | **ROTO** |
| RB-27 | TaskBoard retry CAS | `task_board_service.py` | retry() usa save() no cas_save() | **ROTO** |

**Subtotal**: 3 rotos.

---

### Capa: QUALITY-GATES-MINIMUM (documento transversal)

| gate_id | Propósito | Capa declarada | Entrypoint que invoca | Estado |
|---------|-----------|---------------|----------------------|--------|
| QG-A | Authority Gate | Transversal | Ninguno — es estándar documental | **DECLARADO-NO-INVOCADO** |
| QG-B | Evidence vs Authority Gate | Transversal | Ninguno — es estándar documental | **DECLARADO-NO-INVOCADO** |
| QG-C | Lifecycle Gate | Transversal | Ninguno — es estándar documental | **DECLARADO-NO-INVOCADO** |
| QG-D | Ownership Gate | Transversal | Ninguno — es estándar documental | **DECLARADO-NO-INVOCADO** |
| QG-E | Scope Gate | Transversal | Ninguno — es estándar documental | **DECLARADO-NO-INVOCADO** |
| QG-F | Validation Gate | Transversal | Ninguno — es estándar documental | **DECLARADO-NO-INVOCADO** |
| QG-G | Claim Discipline Gate | Transversal | Ninguno — es estándar documental | **DECLARADO-NO-INVOCADO** |

**Subtotal**: 7 gates transversales — estándar de referencia, no ejecutables por diseño. Esto es correcto: el documento define qué verificar, no implementa la verificación.

---

## 3. Verificación Específica: enforce-envelope

### Pregunta: ¿El parsing de brackets funciona para `Artifacts: [a.md, b.md]`?

**SÍ.** Fix implementado. El script hace:
```bash
ARTIFACTS_LINE="${ARTIFACTS_LINE//\[/}"; ARTIFACTS_LINE="${ARTIFACTS_LINE//\]/}"
```

**Evidencia**: 12/12 bats tests pasan (verificado 2026-04-26):
- `PASS: bracketed list with real files` → exit 0
- `REGRESSION: Artifacts: [a.md, b.md] does NOT include brackets` → exit 0
- `FAIL: nonexistent artifact file in brackets` → exit 1 (correctamente)

### Pregunta: ¿Existe test persistente?

**SÍ.** `scripts/test-enforce-envelope.bats` con 12 tests incluyendo 3 regresión específicos para bracket parsing. Corren con `bats scripts/test-enforce-envelope.bats`. No requiere validación manual.

**Veredicto enforce-envelope**: EFECTIVO. Bracket parsing funciona. Tests persistentes existen y pasan.

---

## 4. Verificación: tf:* Prompts y Format Tests

### 6/6 Format Tests

Los 7 prompts `tf:*` definen la estructura de envelope `## FORK_START ##` / `## FORK_END ##`:

| Prompt | Definió envelope | Artifacts con brackets | Referencia scripts |
|--------|-----------------|----------------------|-------------------|
| `tf:init.md` | SÍ | No (no artifacts) | — |
| `tf:plan.md` | SÍ | `[subtask list...]` | skill-resolver |
| `tf:spawn.md` | SÍ | `[list of agent names...]` | skill-resolver, trifecta-context-inject |
| `tf:orchestrate.md` | No (formato tabla) | — | enforce-envelope, conflict-detect, mr-plan-eval |
| `tf:consolidate.md` | SÍ | `[list of output files]` | enforce-envelope, conflict-detect |
| `tf:validate.md` | SÍ | `[validation report path]` | — |
| `tf:cleanup.md` | SÍ | `[eval report path, session log path]` | mr-plan-eval |

**Format tests**: No existen 6 tests unitarios específicos de formato de prompts. Lo que existe es `enforce-envelope` con 12 bats tests que validan la estructura del envelope. Los prompts son plantillas de texto, no código testeable directamente.

**Interpretación**: El claim "6/6 format tests" probablemente se refiere a que 6 de los 7 prompts definen envelopes válidos (tf:orchestrate.md usa formato tabla, no envelope inline). Los 12 bats tests de enforce-envelope son los tests de formato efectivos.

---

## 5. Recursos Huérfanos

### Clasificación por tipo

| Recurso | Referenciado por | Tipo |
|---------|-----------------|------|
| `resources/agent-*.md` (5 files) | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** — cargables via search |
| `resources/architecture-detail.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/cli-reference.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/known-issues.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/live-orchestration.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/memory-commands.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/model-assignment.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/phase-driver.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/quick-reference.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/sdd-bridge.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/subagent-failure-patterns.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/workflow-recipes.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/orchestration-prompt.md` | Ningún tf:*.md ni SKILL.md | **TRIFECTA_SEARCHABLE** |
| `resources/orchestrator-system-prompt.md` | `tf:spawn.md` (1 ref) | **DIRECTAMENTE_REFERENCIADO** |
| `resources/environment.md` | `tf:spawn.md`, `tf:init.md`, `tf:plan.md` | **DIRECTAMENTE_REFERENCIADO** |
| `resources/protocol.md` | Todos los tf:*.md (7 refs) | **DIRECTAMENTE_REFERENCIADO** |
| `resources/governance.md` | `tf:plan.md`, `tf:spawn.md` | **DIRECTAMENTE_REFERENCIADO** |
| `resources/init.md` | `tf:init.md` y otros (5 refs) | **DIRECTAMENTE_REFERENCIADO** |
| `resources/safety.md` | SKILL.md | **DIRECTAMENTE_REFERENCIADO** |
| `resources/state-format.md` | SKILL.md | **DIRECTAMENTE_REFERENCIADO** |
| `resources/tasklist-bridge.md` | `tf:spawn.md` | **DIRECTAMENTE_REFERENCIADO** |
| `resources/archive/*` (5 files) | Ningún tf:*.md | **ARCHIVE** — histórico |

**Veredicto**: 13 recursos son TRIFECTA_SEARCHABLE (no huérfanos — accesibles via search). 7 son DIRECTAMENTE_REFERENCIADOS. 5 son ARCHIVE. **No hay recursos completamente huérfanos** (inaccesibles por cualquier mecanismo).

---

## 6. Next Steps de QUALITY-GATES-MINIMUM.md

| Documento declarado | Existe? | Estado |
|---------------------|---------|--------|
| `PRE-TASK-GATES-ORCHESTRATOR.md` | **NO** | No creado |
| `RC-CLOSURE-GATE.md` | **NO** | No creado |
| `BACKEND-LIFECYCLE-GATE.md` | **NO** | No creado |
| `SKILL-REPO-BOUNDARY-GATE.md` | **NO** | No creado |

Ninguno de los 4 documentos "Next Steps" fue creado. El fix-list (`skill-gates-fix-list.md`) tampoco fue mapeado a contextos correctos.

---

## 7. Lista de Gates Efectivos Reales

Gates que bloquean ejecución hoy, con evidencia de invocación en el flujo real:

### Protegen el paso plan → implementación:

| # | Gate | Qué protege | Cómo bloquea | Invocado por |
|---|------|-------------|-------------|-------------|
| 1 | enforce-envelope | Calidad output sub-agent | Exit 1 si faltan campos | tf:consolidate |
| 2 | conflict-detect | Conflictos file-level | Exit 2 si overlap | tf:consolidate |
| 3 | mr-plan-eval | Calidad del plan final | Exit code SHIP/NEEDS_WORK/BLOCKED | tf:cleanup |
| 4 | skill-resolver | Skills correctas por rol | Exit 1 si sin descripción | tf:spawn |
| 5 | tmux-live duplicate prevention | Nombres duplicados | Exit 1 si colisión | tf:spawn |
| 6 | tmux-live spawn verification | Agent arrancó | Exit 1 si proceso no existe | tf:spawn |
| 7 | tmux-live timeout | Agent completó a tiempo | Exit 1 si timeout | tf:consolidate |

**Total: 7 gates que protegen plan→implementación con código ejecutable.**

### Protegen infraestructura (no contenido semántico):

| # | Gate | Qué protege |
|---|------|-------------|
| 8-18 | tmux-live + trifecta gates | Infraestructura (pane, binary, args) |

**Nota**: Ninguno de estos 18 gates valida **corrección semántica** del trabajo realizado. Solo `enforce-envelope` valida formato de output, y `mr-plan-eval` evalúa calidad de plan.

---

## 8. Gates Decorativos / No Invocados

### Gates que claiman bloquear pero no pueden bloquear:

| Categoría | Cantidad | Razón |
|-----------|----------|-------|
| PROMPT_ENFORCED (skill) | 16 | LLM self-enforced, sin código |
| SOFT_EXECUTABLE (skill) | 7 | Exit 0 siempre |
| Repo backend no invocado | 24 | Código robusto pero skill no lo llama |
| Repo BYPASSED | 3 | Implementación rota |
| QUALITY-GATES-MINIMUM | 7 | Estándar documental (correcto por diseño) |
| QUALITY-GATES Next Steps | 4 | No creados |

---

## 9. Contradicciones Restantes

| # | Contradicción | Origen | Impacto |
|---|--------------|--------|---------|
| C1 | Plan gate: AGENTS.md dice "optional", protocol.md dice "STOP" | `AGENTS.md:38` vs `protocol.md:47` | Agente puede saltear aprobación |
| C2 | SSOT: SKILL.md dice "Task list is source of truth", state-format.md dice "Memory MCP is SSOT" | `SKILL.md:84` vs `state-format.md:5` | Doble autoridad divergente |
| C3 | Governance: línea 4 "advisory-only", línea 80 "FAIL_ABORT" | `governance.md:4,80` | Falsa confianza en blocking |
| C4 | Phase count: fork-run (12) vs SKILL.md (10) | Legacy doc vs actual | Confusión |
| C5 | Skill bypassa AgentLaunchLifecycleService | Skill no llama repo gates | Spawns sin dedup/lease |
| C6 | TaskBoardService.retry() usa save() no cas_save() | `task_board_service.py` | CAS bypass interno |
| C7 | Repo workflow.py bug-hunt llama tmux-live bypassando su propio lifecycle | `workflow.py` | Repo es internamente inconsistente |

---

## 10. Recomendaciones

### P0 — Riesgo de ejecución insegura

| # | Recomendación | Justificación |
|---|--------------|---------------|
| P0-1 | **Cablear tmux-live → AgentLaunchLifecycleService** | El gate más importante que no está conectado. `tmux-live launch` debe llamar `request_launch()` antes de spawnear. Un subprocess call al CLI del repo. | 
| P0-2 | **Resolver C2: unificar SSOT** | Elegir Memory MCP O Task list, no ambos. Documentar cuál es la autoridad y cuál es la vista. |
| P0-3 | **Resolver C1: Plan Gate mandatory/optional** | Unificar AGENTS.md y protocol.md en una sola respuesta. |

### P1 — Drift y validación superficial

| # | Recomendación | Justificación |
|---|--------------|---------------|
| P1-1 | **Mapear skill-gates-fix-list.md a contextos** | Como dice QUALITY-GATES-MINIMUM: "Fixes applied to the wrong context create the same problem this document exists to prevent." |
| P1-2 | **Crear PRE-TASK-GATES-ORCHESTRATOR.md** | El primer Next Step pendiente. Documentar qué gates protegen plan→implementación con código real vs LLM-enforced. |
| P1-3 | **Endurecer G1.6 Pre-flight Check** | Convertir de "manual checklist" a script con exit codes. 6 de 8 sub-checks no tienen script. |
| P1-4 | **Agregar gate semántico en enforce-envelope** | Actualmente solo valida formato (headers existen). No valida que el contenido sea correcto. |

### P2 — Ergonomía y documentación

| # | Recomendación | Justificación |
|---|--------------|---------------|
| P2-1 | **Crear RC-CLOSURE-GATE.md** | Template para cierres de RC. |
| P2-2 | **Crear BACKEND-LIFECYCLE-GATE.md** | Gates para servicios code-first del repo. |
| P2-3 | **Crear SKILL-REPO-BOUNDARY-GATE.md** | Contrato explícito entre skill y repo. |
| P2-4 | **Resolver C4: unificar phase count** | fork-run.md debe decir 10-phase. |
| P2-5 | **Documentar recursos Trifecta-searchable** | Los 13 recursos no referenciados por prompts son accesibles via search — documentarlo en README. |
| P2-6 | **Agregar TDD enforcement en tf:validate** | Si STRICT_TDD fue set, verificar que test files existan. |

---

## 11. Criterio de Aceptación — Verificación

| Criterio | Cumplido? | Evidencia |
|----------|-----------|-----------|
| Queda claro qué gates protegen plan→implementación hoy | **SÍ** | Sección 7: 7 gates efectivos identificados con mecanismo de bloqueo |
| Queda claro qué gates son intención futura | **SÍ** | Sección 8: 61 gates declarados-no-invocados/d decorativos |
| No declarar "production-ready"/"SSOT cerrado"/"frictionless"/"autónomo" sin evidencia | **SÍ** | No se hace ninguno de estos claims |
| Evidencia no reemplaza autoridad | **SÍ** | Logs/tests/reportes clasificados como evidencia en la matriz, no como autoridad |
