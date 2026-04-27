# Pre-task Gates Exploration

> Generated: 2026-04-24 | 3 parallel explorer agents (scripts, docs, code)
> Method: rg/grep/read across 230+ Python files, 21 shell scripts, 7 tf:* prompts, 18 skill resources, 2 AGENTS.md

---

## 1. Resumen Ejecutivo

### Veredicto General

El sistema tiene **dos capas de gates completamente distintas**:

1. **Capa code-first** (Python + SQLite): `AgentLaunchLifecycleService`, `OrchestrationTask`, `PollRun` — gates robustos con CAS, lease, quarantine, tests. Son los gates más sólidos del sistema.

2. **Capa prompt-first** (LLM self-enforcement): Gates 1.5, 1.6, 5.5, 5.7, 6.5, todo governance — 13 de 22 gates documentados NO tienen código ejecutable. Son instrucciones en prompts que el LLM interpreta y auto-aplica.

### Riesgo Principal

**El sistema presenta gates estructurales en documentación que no existen en código.** La brecha no es que los gates sean malos — los de la capa code-first son excelentes. El riesgo es que la documentación los presenta como si fueran todos iguales, cuando en realidad 59% son LLM self-enforced sin verificación posible.

### Recomendación

El primer gate a endurecer es **G1.6 Pre-flight Check** — convertir de "manual checklist" (LLM) a script ejecutable con exit codes reales. Es el gate con más superficie desprotegida y el que más daño causa cuando falla.

---

## 2. Inventario de Gates Actuales

### 2.1 Gates Code-First (20 gates con código ejecutable)

| # | Gate | Ubicación | Tipo | Bloquea? | Dueño | Testeado |
|---|------|-----------|------|----------|-------|----------|
| 1 | Workflow phase transition | `workflow.py:319` | lifecycle | HARD (PhaseSkipError) | CLI commands | SÍ |
| 2 | Workflow state existence | `workflow.py:145-167` | lifecycle | HARD (typer.Exit 1) | CLI commands | SÍ |
| 3 | Ship preflight | `workflow.py:223` | safety | HARD (ShipPreflightError) | CLI commands | SÍ |
| 4 | Ship unlock | `workflow.py:643` | lifecycle | HARD (typer.Exit 1) | CLI commands | SÍ |
| 5 | Task state machine | `task_board_service.py:197` | lifecycle | HARD (TaskTransitionError) | TaskBoardService | SÍ |
| 6 | Task blocked_by guard | `task_board_service.py:192` | lifecycle | HARD (ValueError) | TaskBoardService | SÍ |
| 7 | AgentLaunch dedup | `agent_launch_lifecycle_service.py:66` | lifecycle | HARD (suppressed) | LifecycleService | SÍ |
| 8 | AgentLaunch CAS transitions | `agent_launch_repository.py:100` | lifecycle | HARD (CAS fail) | LifecycleService | SÍ |
| 9 | tmux session guard | `tmux-live:200` | runtime | HARD (exit 1) | tmux-live | NO |
| 10 | Agent name collision | `tmux-live:284` | runtime | HARD (return 1) | tmux-live | NO |
| 11 | Enforce envelope | `enforce-envelope` | validation | HARD (exit 1/2) | enforce-envelope | NO |
| 12 | tmux health gate | `tmux_health_gate.sh` | preflight | HARD (exit 1) | tmux_health_gate | NO |
| 13 | Trifecta daemon start | `trifecta_manager.sh:96` | lifecycle | HARD (exit 1) | trifecta_manager | NO |
| 14 | fork-verify | `fork-verify.sh` | validation | HARD (exit 1/2) | fork-verify | SÍ (smoke) |
| 15 | Pre-PR chain | `Makefile:prePR` | validation | HARD (sequential) | Makefile | NO |
| 16 | Content validation | `hybrid.py:202` | runtime | HARD (ValueError) | HybridDispatcher | NO |
| 17 | MCP require gate | `hybrid.py:275` | runtime | HARD (RuntimeError) | HybridDispatcher | NO |
| 18 | PollRun state machine | `poll_run.py:112` | lifecycle | HARD (can_transition_to) | AgentPollingService | SÍ |
| 19 | Circuit breaker | `circuit_breaker.py:94` | runtime | HARD (can_execute=False) | TmuxCircuitBreaker | SÍ |
| 20 | Rate limiter | `rate_limit.py:39` | runtime | HARD (429 response) | InMemoryRateLimiter | NO |

### 2.2 Gates Prompt-First (15 gates sin código, LLM self-enforced)

| # | Gate | Documentado En | Bloquea (doc)? | Código Real | Gap Principal |
|---|------|---------------|----------------|-------------|---------------|
| 21 | G1.5 Plan Gate | protocol.md:47, tf:plan.md:38 | SÍ (STOP) | Ninguno | AGENTS.md dice "opcional", protocol.md dice STOP (C2) |
| 22 | G1.6 Pre-flight (8 checks) | protocol.md:57-69 | SÍ (FAIL_ABORT) | 2 de 8 scripts existen | 6 checks sin script (C4) |
| 23 | G1.6.1 Acceptance Criteria | protocol.md:62 | FAIL_RETRY | Ninguno | LLM judgment puro |
| 24 | G1.6.3 TDD Flag | protocol.md:64 | WARN | Ninguno | Flag sin enforcement |
| 25 | G1.6.7 Clean State | protocol.md:68 | FAIL_ABORT | Ninguno | No corre pytest/ruff |
| 26 | G1.6.8 Metrics | protocol.md:69 | FAIL_RETRY | Ninguno | No valida existencia |
| 27 | G5.5 Validate Gate | protocol.md:153 | SÍ (PASS only) | enforce-envelope (formato) | Formato ≠ contenido |
| 28 | G5.7 Quality Check | protocol.md:175 | SÍ (>5=ESCALATE) | Ninguno | Governance-only |
| 29 | G6.5 Plan Evaluation | protocol.md:195 | SÍ (BLOCKED) | **mr-plan-eval existe** | MATCH — script real |
| 30 | GateResult enum | protocol.md:73 | — | Ninguno | Enum aspiracional |
| 31 | FAIL_FINAL propagation | tasklist-bridge.md:86 | SÍ (skip cleanup) | Ninguno | pi-tasks no tiene FAIL_FINAL |
| 32 | Human Override (AV2) | governance.md:223 | Advisory | Ninguno | Solo documenta evento |
| 33 | Escalation Timeout (AV3) | governance.md:231 | SÍ (5min) | Ninguno | LLM no mide tiempo |
| 34 | Coverage Gap Detection | governance.md:63 | CRITICAL=FAIL | Ninguno | LLM judgment |
| 35 | Quality Checklist (spec-kit) | governance.md:83 | FAIL on CRITICAL | Ninguno | spec-kit no existe |

### 2.3 Gates Cosméticos (10 gates que solo advierten)

| # | Gate | Ubicación | Comportamiento Real |
|---|------|-----------|-------------------|
| 36 | LSP binary check | `trifecta_manager.sh:97` | Warn, continúa AST-only |
| 37 | trifecta-auto-sync | `trifecta-auto-sync:26` | Warn, exit 0 |
| 38 | trifecta-daemon-warmup | `trifecta-daemon-warmup:18` | Warn, exit 0 |
| 39 | trifecta-session-log | `trifecta-session-log:3` | Siempre exit 0 |
| 40 | DB path mismatch | `hybrid.py:215` | logger.warning, continúa |
| 41 | Skill resolver cache | `skill-resolver:67` | Falls through on corrupt |
| 42 | Concurrency queue | `tmux-live:291` | Queues, no bloquea |
| 43 | Orphan pane detection | `tmux-live:649` | Warn only |
| 44 | Conflict detection | `conflict-detect` | Reporta, no fuerza stop |
| 45 | trifecta-verifier-check | `trifecta-verifier-check` | **Siempre exit 0** |

---

## 3. Mapa de Autoridad

### 3.1 Code-First — Autoridad Clara

```
AgentLaunchLifecycleService  ─── SSOT para launch decisions
    ↓ CAS + lease + quarantine
    ├── WorkflowExecutor  ─── "workflow:{task_id}"
    ├── AgentManager      ─── "manager:{agent_name}"
    └── AgentPollingService ─── "task:{task_id}"

TaskBoardService             ─── SSOT para task transitions
    ↓ CAS + transition map
    └── OrchestrationTask   ─── PENDING→COMPLETED

CircuitBreaker               ─── SSOT para resilience
    ↓ Per-agent Lock
    └── TmuxAgent           ─── CLOSED→OPEN→HALF_OPEN
```

### 3.2 Prompt-First — Autoridad Difusa

```
protocol.md                  ─── CLAIMED (FAIL_ABORT)
    ↓ sin código
    ├── GateResult enum      ─── NO EXISTE en runtime
    ├── Pre-flight 8-check   ─── LLM interpreta
    └── FAIL_FINAL           ─── LLM self-enforces

governance.md                ─── CLAIMED ("blocking")
    ↓ auto-declara "advisory"
    ├── Quality Check 5.7   ─── Sin script
    ├── Escalation AV3      ─── LLM no mide tiempo
    └── Coverage Gap        ─── LLM judgment
```

### 3.3 Zonas de Competencia

| Superficie | Sistema A | Sistema B | Conflicto |
|------------|-----------|-----------|-----------|
| Agent tracking | LifecycleService (SQLite) | AgentManager (in-memory) | SSOT no consultado por queries |
| Agent tracking | LifecycleService (SQLite) | SessionStore (memory+disk) | Tercer sistema diverge |
| Task execution | WorkflowExecutor ("workflow:{id}") | AgentPollingService ("task:{id}") | Keys diferentes, posible doble registro |
| Phase progress | Memory MCP (state-format.md) | pi-tasks (SKILL.md:84) | **SKILL.md contradice state-format.md** |
| Plan gate | AGENTS.md (optional) | protocol.md (mandatory STOP) | **Contradicción directa** |
| Phase count | fork-run.md (12) | Todo lo demás (10) | **Contradicción de conteo** |
| Hook dispatch | HookService (rules) | WorkflowExecutor._emit_event() | Dos caminos, mismo evento |

---

## 4. Duplicidades y Contradicciones

### C1: Phase Count — 10 vs 12
- **fork-run.md:1** dice "12-phase"
- **SKILL.md:29**, **AGENTS.md:32**, **tf:orchestrate.md:1** dicen "10-phase"
- **Evidencia**: fork-run.md cuenta sub-phases como separadas
- **Riesgo**: Ambigüedad — "Phase 5" significa cosas distintas

### C2: Plan Gate — Optional vs Mandatory
- **AGENTS.md:38**: "opcional pero recomendado"
- **protocol.md:47**: "STOP. Present plan to user"
- **Evidencia**: 2 de 3 fuentes dicen mandatory

### C3: Governance "Advisory" vs FAIL_ABORT
- **governance.md:3-4**: "advisory-only, no code enforcement"
- **governance.md:71**: "Checks 7-8 are blocking — FAIL_ABORT"
- **Evidencia**: El documento se contradice en su propia definición

### C4: Pre-flight — Scripts que no existen
- **protocol.md:57-69**: Tabla de 8 checks con FAIL_ABORT/FAIL_RETRY
- **fork-run.md:58**: Correctamente identifica como "Manual checklist"
- **Evidencia**: protocol.md presenta como automatizado, no lo es

### C5: SSOT — Memory MCP vs pi-tasks
- **state-format.md**: "Memory MCP is SSOT"
- **SKILL.md:84**: "Task list is source of truth"
- **Evidencia**: fork-run.md resuelve correctamente (Memory MCP wins), SKILL.md no

### C6: Envelope Format — RESUELTO
- enforce-envelope busca `^## Status:`, tf:* prompts ahora generan `## Status:`

### C7: Post-Cleanup Check — Misplaced
- **protocol.md:175-189**: Post-cleanup "MANDATORY" bajo sección 5.7
- **Evidencia**: Nesting incorrecto sugiere que solo corre con GOVERNANCE=1

---

## 5. Evaluación contra Gates Objetivo

### 5.A Authority Gate — PARCIAL

| Aspecto | Estado | Evidencia |
|---------|--------|-----------|
| Fuente oficial de verdad | PARCIAL | AgentLaunch y TaskBoard tienen SSOT claro. Governance/protocol claiman authority sin código |
| Productores legacy | SÍ | AgentManager y SessionStore no consultan LifecycleService |
| No duplicación | NO | 3 sistemas tracking agentes, 2 caminos de task execution |

### 5.B Evidence vs Authority Gate — PARCIAL

| Aspecto | Estado | Evidencia |
|---------|--------|-----------|
| Qué decide | PARCIAL | LifecycleService decide launches. Pero 13 gates son LLM-decided |
| Evidencia insuficiente | SÍ | enforce-envelope pasaría output con 6 headers vacíos |

### 5.C Lifecycle Gate — PARCIAL (P0 gap)

| Aspecto | Estado | Evidencia |
|---------|--------|-----------|
| Locks | PARCIAL | CAS en Lifecycle/TaskBoard. Nada en PromiseContract o WorkflowState |
| Rollback | NO | Quarantine es estado final, no rollback |
| Crash-safety | PARCIAL | LifecycleService: SÍ. WorkflowState: NO (non-atomic JSON). AgentManager: NO (in-memory) |

### 5.D Ownership Gate — PARCIAL

| Aspecto | Estado | Evidencia |
|---------|--------|-----------|
| Un dueño por responsabilidad | PARCIAL | Agent tracking tiene 3 dueños |
| grep guard contra rutas paralelas | NO | No hay protección contra callers bypassando LifecycleService |

### 5.E Scope Gate — NO EXISTE

| Aspecto | Estado | Evidencia |
|---------|--------|-----------|
| Cambio mínimo | NO | No hay gate de scope en ningún prompt ni script |
| No infra nueva | NO | Governance es puramente advisory |
| Deuda aceptada | NO | No hay mecanismo para aceptar deuda explícitamente |

### 5.F Validation Gate — PARCIAL

| Aspecto | Estado | Evidencia |
|---------|--------|-----------|
| Contrato exacto | PARCIAL | enforce-envelope valida formato, no contenido |
| Test antes/después | PARCIAL | Pre-PR chain existe pero no está en CI |
| Caso límite | NO | No hay edge case testing en gates |
| Comando reproducible | SÍ | `make prePR` es reproducible |

### 5.G Claim Discipline Gate — NO EXISTE

| Aspecto | Estado | Evidencia |
|---------|--------|-----------|
| Madurez real vs claimed | NO | 13 gates claim "FAIL_ABORT" pero son LLM-interpreted |
| Evidencia para claims | NO | governance.md dice "advisory" y "blocking" en el mismo documento |
| Condición invalidante | NO | No hay mecanismo para invalidar claims |

---

## 6. Gaps Críticos (ordenados por severidad)

### P0 — Evita corrupción de estado o ejecución insegura

| # | Gap | Impacto | Evidencia |
|---|-----|---------|-----------|
| 1 | **WorkflowState non-atomic writes** | Crash corrompe state files (PlanState, ExecuteState, VerifyState) | `state.py:247,370,490` — plain json.dump sin temp+rename |
| 2 | **PromiseContract sin CAS** | Transiciones concurrentes se sobreescriben silenciosamente | `promise_contract.py:137` — transition_to() sin expected-status |
| 3 | **G1.6 Pre-flight: 6 de 8 checks sin código** | Agentes proceden sin validación de criteria, TDD, clean state | protocol.md:57-69 — solo 2 scripts existen |

### P1 — Evita drift, claims falsos o validación superficial

| # | Gap | Impacto | Evidencia |
|---|-----|---------|-----------|
| 4 | **3 sistemas tracking agentes** | LifecycleService es SSOT pero AgentManager y SessionStore no lo consultan | agent_manager.py, agents.py, agent_launch_lifecycle_service.py |
| 5 | **enforce-envelope no valida contenido** | Output con headers vacíos pasa como válido | enforce-envelope REQUIRED_FIELDS — solo chequea existencia de línea |
| 6 | **GateResult enum aspiracional** | FAIL_ABORT/FAIL_RETRY existen solo en docs, no en runtime | protocol.md:73 — no code implements |
| 7 | **7 contradicciones doc-vs-doc** | Agente recibe instrucciones conflictivas | C1-C7 arriba |
| 8 | **20 shell scripts sin tests** | Regresiones en gates no detectadas | Solo fork-verify.sh tiene tests |
| 9 | **AgentManager in-memory only** | Estado perdido en restart, sin recovery | agent_manager.py:319 — _agents dict |

### P2 — Mejora ergonomía, DX, documentación

| # | Gap | Impacto | Evidencia |
|---|-----|---------|-----------|
| 10 | **Phase count 10 vs 12** | Ambigüedad en comunicación | fork-run.md vs todo lo demás |
| 11 | **trifecta-verifier-check siempre exit 0** | Gate documentado como validation pero nunca bloquea | Script exits 0 always |
| 12 | **8 undocumented gates** | Comandos/script útiles no referenciados en protocolo | tmux-live events/send, detect-env, --sanitize |
| 13 | **TDD flag sin enforcement** | Flag existe pero no hay verificación de test existence | tf:spawn injecta flag, nadie verifica |

---

## 7. Recomendación de Implementación Mínima

### Primer cambio seguro: `preflight-check` script

Crear un script `preflight-check` que convierta los 6 checks sin código de G1.6 en un ejecutable con exit codes reales:

```
preflight-check <project-dir>
  Check 1: acceptance-criteria   → grep task files for "criteria:" pattern   → exit 1 if missing
  Check 3: TDD-enabled           → grep plan for "STRICT_TDD" or detect tests/ dir → exit 0 (soft)
  Check 4: fork-init             → test -f .fork/init.yaml                   → exit 1 if missing
  Check 5: skill-resolved        → skill-resolver --check                    → exit 1 if fails
  Check 7: clean-state           → ruff check && pytest --co                → exit 1 if fails
  Check 8: metrics-defined       → grep plan for "KPI" or "threshold"       → exit 1 if missing
```

**Por qué es seguro**: No muta estado existente. Solo lee y reporta. Exit codes reales permiten que tf:plan.md lo invoque como gate real en vez de depender del LLM.

**Por qué este gate primero**: G1.6 es el gate más referenciado (protocol.md, tf:plan.md, fork-run.md, governance.md) y el que más daño causa cuando falla — es el pre-task gate por excelencia.

---

## 8. Evidencia Reproducible

### Comandos ejecutados

```bash
# 1. Gate inventory — scripts
rg -l 'exit 1\|exit 0\|die\|return 1' ~/.pi/agent/skills/tmux-fork-orchestrator/scripts/
rg -n 'REQUIRED_FIELDS\|GateResult\|FAIL_ABORT\|FAIL_RETRY' ~/.pi/agent/skills/tmux-fork-orchestrator/

# 2. Gate inventory — code
rg -n 'can_transition_to\|_TRANSITIONS\|cas_save\|cas_update' ~/Developer/tmux_fork/src/domain/
rg -n 'raise.*Error\|ValueError\|RuntimeError' ~/Developer/tmux_fork/src/application/

# 3. Contradiction search
rg 'SSOT\|source of truth\|FAIL_ABORT\|advisory' ~/.pi/agent/skills/tmux-fork-orchestrator/resources/
rg 'opcional\|mandatory\|MANDATORIO\|STOP' ~/.pi/agent/prompts/tf:*.md

# 4. Test coverage
fd test_ ~/Developer/tmux_fork/tests/ -e py | wc -l  # result: 60+ test files
fd test_ ~/Developer/tmux_fork/tests/ -e py -x grep -l 'workflow\|task_board\|lifecycle'  # 8 files

# 5. Shell script test coverage
fd '\.sh$' ~/.pi/agent/skills/tmux-fork-orchestrator/scripts/ -x basename | sort  # 21 scripts
fd 'test_.*\.sh$' ~/Developer/tmux_fork/scripts/ -x basename  # 1 file (test_fork_verify.sh)
```

### Archivos inspeccionados

- 21 shell scripts en `~/.pi/agent/skills/tmux-fork-orchestrator/scripts/`
- 7 shell scripts en `~/Developer/tmux_fork/scripts/`
- 230+ Python files en `src/`
- 7 tf:* prompts
- 18 skill resources
- 2 AGENTS.md
- fork-run.md
- protocol.md, governance.md, phase-driver.md, state-format.md, tasklist-bridge.md
- Makefile, .pre-commit-config.yaml

---

## 9. Riesgos Residuales

1. **Casos de crash no verificables**: No se puede simular un crash mid-write en WorkflowState sin instrumentar el código (riesgo detectado pero no reproducible sin implementar)

2. **LLM self-enforcement effectiveness**: No hay forma de medir qué porcentaje de las veces el LLM realmente self-enforces los gates prompt-first (requeriría un experimento con 50+ runs)

3. **Concurrent task execution paths**: Las dos paths (WorkflowExecutor y AgentPollingService) no fueron testeadas concurrentemente — el riesgo de race condition entre canonical keys es teórico

4. **Shell script edge cases**: La mayoría de los shell scripts no tienen tests — edge cases como concurrent `init`, panic durante `kill-all`, o power-loss durante `spawn` no están verificados

5. **Task dependency cycle detection**: `OrchestrationTask.detect_cycle()` existe pero nunca se llama desde el service layer — el riesgo de ciclos depende de si el CLI o API pueden crear blocked_by recursivos
