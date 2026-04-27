# Pre-task Gates Two-System Exploration

> Generated: 2026-04-24 | 3 parallel explorer agents (skill, repo, boundary)
> Method: rg/grep/read across skill root + repo src/, cross-referenced for boundary analysis

---

## 1. Resumen Ejecutivo

### Dos Sistemas Separados

No existe un único sistema de gates. Hay dos sistemas acoplados:

**A. Skill de orquestador** (`~/.pi/agent/skills/tmux-fork-orchestrator/`):
- Ejecuta el flujo real hoy via tmux-live + tf:* prompts
- 70 gates identificados: 26 HARD_EXECUTABLE (infrastructure/input), 7 SOFT_EXECUTABLE, 33 PROMPT_ENFORCED, 10 DOC_ONLY
- Autoridad difusa: 47% de gates dependen del LLM para self-enforcement
- Solo `enforce-envelope` valida calidad de output con exit code real

**B. Repo backend / futuro orquestador** (`~/Developer/tmux_fork/src/`):
- Contiene servicios code-first con CAS, leases, quarantine, 335+ tests
- 40 gates identificados: 27 HARD_EXECUTABLE (CAS/transition maps), 8 SOFT_EXECUTABLE, 3 BYPASSED
- Autoridad clara: AgentLaunchLifecycleService, TaskBoardService, AgentPollingService
- **0 de 40 gates son invocados por la skill**

### Riesgo Principal

**La skill ejecuta sin consultar la autoridad del repo.** El repo tiene `AgentLaunchLifecycleService` declarado como "the ONLY component allowed to answer: May this canonical work item launch right now?" — pero `tmux-live launch` bypassa este gate completamente. El propio repo es internamente inconsistente: `workflow.py` bug-hunt llama a `tmux-live`, que bypassa su propio lifecycle service.

### Primer Gate a Endurecer

No es crear `preflight-check` como wrapper más. Es: **`tmux-live launch` debe llamar `AgentLaunchLifecycleService.request_launch()` antes de spawnear.** Esto es el contrato de borde correcto: la skill ejecuta, el repo provee autoridad verificable.

---

## 2. Inventario A: Skill de Orquestador

### 2.1 Gates HARD_EXECUTABLE (26 — bloques reales con exit code)

| # | Ubicación | Nombre | Superficie | Exit Code |
|---|-----------|--------|------------|-----------|
| 1 | `scripts/enforce-envelope:177` | Envelope validation (CRITICAL) | Sub-agent output format | 1 |
| 2 | `scripts/enforce-envelope:179` | Envelope strict mode | Optional fields | 2 |
| 3 | `scripts/enforce-envelope:13` | jq dependency | System dependency | 1 |
| 4 | `scripts/conflict-detect:61,65` | min-overlap validation | Input args | 2 |
| 5 | `scripts/conflict-detect:117` | JSONL file existence | Input files | 2 |
| 6 | `scripts/mr-plan-eval:47` | Plan file required | Input file | 1 |
| 7 | `scripts/skill-resolver:64` | Task description required | Input arg | 1 |
| 8 | `scripts/detect-env:16,312` | Project dir + language detection | Project config | 1 |
| 9 | `scripts/tmux-live:200,280` | TMUX env var required | Runtime env | 1 |
| 10 | `scripts/tmux-live:284` | Duplicate agent prevention | Agent registry | 1 (return) |
| 11 | `scripts/tmux-live:326` | Pane creation gate | tmux infrastructure | 1 |
| 12 | `scripts/tmux-live:398` | Spawn verification (retries) | Agent startup | 1 |
| 13 | `scripts/tmux-live:630,646` | Agent exit code check | Agent completion | 1 |
| 14 | `scripts/tmux-live:655` | Agent wait timeout | Agent completion | 1 |
| 15 | `scripts/tmux-live:1071,1077` | Chain file validation | Chain execution | 1 |
| 16 | `scripts/tmux-live:1121` | Chain step failure | Chain execution | 1 |
| 17 | `scripts/trifecta-preload:56,61,170` | Preload validation | Trifecta context | 1 |
| 18 | `scripts/trifecta_manager.sh:23,153,161` | Trifecta binary + warmup | Trifecta daemon | 1 |
| 19-26 | `scripts/trifecta-*.sh` | Input arg validation (7 gates) | CLI args | 1 |

**Observación**: 19 de 26 hard gates son **input validation** (args, files, env vars). Solo `enforce-envelope` valida **output quality**. Los tmux-live hard gates son **infrastructure** (pane creation, agent startup). Ninguno valida **semantic correctness** del trabajo realizado.

### 2.2 Gates PROMPT_ENFORCED (33 — LLM self-enforced, sin código)

| # | Ubicación | Nombre | Claimed Severity | Power Real |
|---|-----------|--------|-----------------|------------|
| 1 | `protocol.md §1.6` | G1.6.1 Acceptance criteria | FAIL_RETRY | NONE |
| 2 | `protocol.md §1.6` | G1.6.2 Role + artifact | FAIL_RETRY | NONE |
| 3 | `protocol.md §1.6` | G1.6.3 TDD flag | WARN | NONE |
| 4 | `protocol.md §1.6` | G1.6.4 fork init | Run fork init | WEAK |
| 5 | `protocol.md §1.6` | G1.6.5 Skill injection | FAIL_ABORT | WEAK |
| 6 | `protocol.md §1.6` | G1.6.6 Trifecta daemon | WARN | NONE |
| 7 | `protocol.md §1.6` | G1.6.7 Clean state | FAIL_ABORT | NONE |
| 8 | `protocol.md §1.6` | G1.6.8 Metrics | FAIL_RETRY | NONE |
| 9 | `protocol.md §1.5` | Plan Gate (human) | STOP | WEAK |
| 10 | `protocol.md §5.5` | Spec compliance | FAIL | WEAK |
| 11 | `protocol.md §5.5` | TDD compliance | FAIL | WEAK |
| 12 | `protocol.md §5.5` | Remediation loop (max 3) | FAIL_FINAL | NONE |
| 13 | `protocol.md §5.5` | Gate blocking on FAIL | STOP | NONE |
| 14 | `protocol.md §5.7` | Static analysis count | 0=PASS, >5=ESCALATE | NONE |
| 15 | `protocol.md §5.7` | Escalation timeout | FAIL_ABORT 5min | NONE |
| 16 | `protocol.md §6.5` | mr-plan-eval result | SHIP/NEEDS_WORK/BLOCKED | WEAK |
| 17-33 | `tf:*.md`, `phase-common.md`, `fork-run.md` | Cross-cutting (P10, P11, envelope, cleanup, etc.) | Various | NONE-WEAK |

### 2.3 Gates SOFT_EXECUTABLE (7 — siempre exit 0)

Todos los wrappers de Trifecta (`daemon-warmup`, `auto-sync`, `session-log`, `verifier-check`) + `tmux-live` concurrency guard. Diseñados para never block.

### 2.4 Gates DOC_ONLY (10 — aspiracionales)

anchor_dope gates, AV2/AV3/AV4 procedures, sdd-gate-skill reference, GateResult enum, Memory MCP SSOT enforcement.

---

## 3. Inventario B: Repo Backend

### 3.1 Gates HARD_EXECUTABLE (27 — CAS, transition maps, exceptions)

| # | Servicio | Mecanismo | Bloquea? | Skill Invoca? | Testeado? |
|---|----------|-----------|----------|---------------|-----------|
| 1 | `AgentLaunchLifecycleService.request_launch()` | Partial unique index + CAS claim | SÍ | **NO** | SÍ (14 tests) |
| 2 | `AgentLaunchLifecycleService.confirm_spawning()` | CAS (WHERE status=?) | SÍ | **NO** | SÍ |
| 3 | `AgentLaunchLifecycleService.confirm_active()` | CAS (WHERE status=?) | SÍ | **NO** | SÍ |
| 4 | `AgentLaunchLifecycleService.quarantine()` | CAS | SÍ | **NO** | SÍ |
| 5 | `AgentLaunchRepository.claim()` | Partial unique index INSERT | SÍ | **NO** | SÍ (21 tests) |
| 6 | `AgentLaunchRepository.cas_update_status()` | CAS WHERE | SÍ | **NO** | SÍ |
| 7 | `TaskBoardService.submit_plan()` | Transition + CAS | SÍ | **NO** | SÍ |
| 8 | `TaskBoardService.approve()` | Transition + CAS | SÍ | **NO** | SÍ |
| 9 | `TaskBoardService.reject()` | Transition + CAS | SÍ | **NO** | SÍ |
| 10 | `TaskBoardService.start()` | blocked_by + transition + CAS | SÍ | **NO** | SÍ |
| 11 | `TaskBoardService.complete()` | Transition + CAS | SÍ | **NO** | SÍ |
| 12 | `OrchestrationTaskRepository.cas_save()` | CAS WHERE | SÍ | **NO** | SÍ |
| 13 | `PollRun transitions` | _VALID_TRANSITIONS dict | SÍ | **NO** | SÍ (21 tests) |
| 14 | `PollRunRepository.update_status()` | Transition validation | SÍ | **NO** | SÍ |
| 15 | `AgentPollingService.poll_once()` | Concurrency cap + lifecycle + dedup | SÍ | **NO** | SÍ |
| 16 | `AgentPollingService._spawn_run()` | Full lifecycle claim→spawn→confirm | SÍ | **NO** | SÍ |
| 17 | `PromiseContract.can_transition_to()` | Transition dict | SÍ | **NO** | SÍ |
| 18 | `workflow.py _validate_phase_transition()` | Phase enum whitelist | SÍ | **NO** | SÍ (9 tests) |
| 19 | `workflow.py ship() verify gate` | unlock_ship boolean | SÍ | **NO** | SÍ |
| 20 | `workflow.py ship() preflight gate` | Dirty tree + worktree | SÍ | **NO** | SÍ |
| 21 | `AgentManager.spawn_agent()` | Dict dedup + lifecycle claim | SÍ | **NO** | SÍ (11 tests) |
| 22 | `TmuxCircuitBreaker.can_execute()` | State + threshold | SÍ | **NO** | SÍ |
| 23 | `AgentLaunch._VALID_TRANSITIONS` | State machine dict | SÍ | **NO** | SÍ |
| 24 | `AgentLaunch.BLOCKING_STATUSES` | frozenset | SÍ | **NO** | SÍ |
| 25 | `agents.py Semaphore(5)` | Concurrency cap | SÍ | **NO** | SÍ |
| 26 | `agents.py _validate_session_id()` | Regex | SÍ | **NO** | SÍ |
| 27 | `state.py UnsupportedSchemaError` | Version check | SÍ | **NO** | SÍ |

### 3.2 Gates SOFT_EXECUTABLE (8)

Lease reconciliation, retry mechanism, DB backup, event dispatch, container wiring, auto-backup — todos best-effort.

### 3.3 Gates BYPASSED (3 — implementación rota)

`state.py:save()` para PlanState, ExecuteState, VerifyState — usa `json.dump()` plain sin temp+rename. Non-atomic writes.

### 3.4 Crash Safety por Entidad

| Entidad | Writes Atómicos | CAS | Lease | Recovery on Restart | Crash-Safe? |
|---------|----------------|-----|-------|---------------------|-------------|
| AgentLaunch | SÍ (SQLite WAL) | SÍ | SÍ (5min) | reconciliar leases | **PARCIAL** |
| OrchestrationTask | SÍ (SQLite WAL) | SÍ | NO | Stuck IN_PROGRESS forever | **PARCIAL** |
| PollRun | SÍ + temp+rename | PARCIAL | PARCIAL (QUEUED only) | check_runs() detecta crashes | **PARCIAL** |
| PromiseContract | SÍ (SQLite WAL) | **NO** | NO | NO | **NO** |
| WorkflowState | **NO** (json.dump) | NO | NO | InvalidStateError on load | **NO** |
| AgentManager | N/A (memory) | N/A | NO | Lost on restart | **NO** |

---

## 4. Mapa de Borde Skill → Repo

### 4.1 Skill Llama Repo (4 interfaces)

| Caller (Skill) | Target (Repo) | Contrato | Bypass? |
|----------------|---------------|----------|---------|
| `SKILL.md` Quick Commands | `fork doctor status` CLI | Health check | No |
| `tmux-live send/message` | `fork message send-to-pane/receive/history` | Messaging | No |
| `cli-reference.md` (docs) | `fork task *`, `memory *`, `fork poll *` | Lifecycle CLI | **Doc only — skill usa pi-tasks** |
| `tmux-live launch` | `pi --mode json -p` + tmux split | Agent spawn | **Bypass de AgentLaunchLifecycleService** |

### 4.2 Skill Duplica Repo (4 superficies)

| Superficie | Skill | Repo | Reglas Match? |
|------------|-------|------|---------------|
| Agent spawning | `tmux-live launch` (pane-based) | `AgentLaunchLifecycleService` (CAS + lease) | **NO** — skill sin launch gate |
| Phase tracking | Memory MCP `fork/{change}/state` | `.claude/*-state.json` + `WorkflowPhase` | **NO** — fases diferentes, storage diferente |
| Quality gates | Phase 5.7 (ruff+mypy+pytest) | `make prePR` (lint+format+typecheck+cov) | **PARCIAL** — skill saltea format |
| Task lifecycle | pi-tasks (TaskCreate/Update/List) | `TaskBoardService` (CAS + transitions) | **NO** — estados diferentes, storage diferente |

### 4.3 Skill Bypassea Repo (5 gates)

| Repo Gate | Riesgo | Impacto |
|-----------|--------|---------|
| `AgentLaunchLifecycleService.request_launch()` | **HIGH** | Spawns duplicados sin dedup |
| `WorkflowPhase` state machine | **HIGH** | Fases independientes sin comunicación |
| `TaskBoardService` transitions | **MEDIUM** | Progreso invisible a `fork task list` |
| `TmuxCircuitBreaker` | **MEDIUM** | Sin backoff ante fallas de tmux |
| `WorkflowExecutor.cleanup_worktree()` | **MEDIUM** | Branches sin merge post-orchestración |

### 4.4 Autoridad Dual (4 conflictos)

| Superficie | Skill Claim | Repo Reality | Resolución |
|------------|-------------|--------------|------------|
| Phase progress SSOT | Memory MCP es SSOT (state-format.md) | JSON files + WorkflowPhase (state.py) | **Sin resolver** |
| Agent spawn authority | `tmux-live launch` de facto | `AgentLaunchLifecycleService` declarado "ONLY" | **Sin resolver** — repo internamente inconsistente (bug-hunt llama tmux-live) |
| `.fork/init.yaml` ownership | `fork init` documentado como repo command | No existe `fork init` en repo | **Sin resolver** — skill lo crea, repo no lo lee |
| Quality gate scope | Phase 5.7: ruff+mypy+pytest | `make prePR`: lint+format+typecheck+cov | **Menor** — skill es subset |

---

## 5. Duplicidades y Contradicciones

### Skill Interna
- Phase count: fork-run.md (12) vs SKILL.md/AGENTS.md (10)
- Plan gate: AGENTS.md (optional) vs protocol.md (mandatory STOP)
- Governance: "advisory-only" vs "FAIL_ABORT stops the pipeline"

### Repo Interno
- `workflow.py` bug-hunt llama `tmux-live` que bypassa `AgentLaunchLifecycleService`
- `PromiseContract` sin CAS — repo no sigue su propio patrón de CAS
- `state.py` non-atomic writes — crash safety gap en el sistema más robusto
- `TaskBoardService.retry()` usa `save()` no `cas_save()` — CAS bypass

### Skill vs Repo
- **Phase tracking**: Memory MCP vs JSON files — SSOT claims conflictivos
- **Agent spawn**: `tmux-live` vs `AgentLaunchLifecycleService` — autoridad dual
- **Task lifecycle**: pi-tasks vs `TaskBoardService` — sistemas paralelos
- **`.fork/init.yaml`**: Skill lo crea, repo no lo lee — archivo zombie
- **Quality gates**: Phase 5.7 vs `make prePR` — overlap parcial

---

## 6. Evaluación contra Gates Objetivo

### 6.A Authority Gate — PARCIAL

| Aspecto | Skill | Repo | Borde |
|---------|-------|------|-------|
| Fuente oficial | state-format.md claima Memory MCP | WorkflowPhase enum es real | **Conflicto** — dos SSOT claims |
| Productores legacy | tmux-live es productor legacy | AgentManager es legacy | **Ambos legacy** — LifecycleService es el futuro |
| No duplicación | 4 superficies duplicadas | Skill no invoca repo gates | **Falla** — autoridad difusa |

### 6.B Evidence vs Authority Gate — PARCIAL

| Aspecto | Skill | Repo | Borde |
|---------|-------|------|-------|
| Qué decide | LLM self-enforced | CAS + transition maps | **Sin contrato** |
| Evidencia mínima | No definida | enforce-envelope (formato) | **Formato ≠ contenido** |

### 6.C Lifecycle Gate — PARCIAL (P0 gap en borde)

| Aspecto | Skill | Repo | Borde |
|---------|-------|------|-------|
| Locks | Ninguno | CAS en 3 entidades | **Sin lock** en spawn |
| Crash-safety | DONE signal file (basic) | Lease + quarantine (robust) | **Skill sin lease** |
| Rollback | kill-all (manual) | Quarantine state | **Sin integración** |

### 6.D Ownership Gate — PARCIAL

| Aspecto | Skill | Repo | Borde |
|---------|-------|------|-------|
| Un dueño | tmux-live es spawn owner | LifecycleService es "ONLY" | **Doble dueño** |
| grep guard | No | TYPE_CHECKING limits deps | **Sin protección** contra bypass |

### 6.E Scope Gate — NO EXISTE

| Aspecto | Estado | Evidencia |
|---------|--------|-----------|
| No sistema paralelo | **FALLA** | Skill y repo son sistemas paralelos para 4 superficies |
| Cambio mínimo | NO | No hay gate de scope |

### 6.F Validation Gate — PARCIAL

| Aspecto | Skill | Repo | Borde |
|---------|-------|------|-------|
| Contrato exacto | enforce-envelope (formato) | CAS + transition maps | **Sin contrato** |
| Test antes/después | Pre-PR chain (repo) | 335+ tests (repo) | **Skill no corre tests** |
| Reproducible | `make prePR` | `make prePR` | **Skill no lo invoca** |

### 6.G Claim Discipline Gate — FALLA

| Aspecto | Skill | Repo | Borde |
|---------|-------|------|-------|
| Madurez real vs claimed | 33 gates claiman blocking, son LLM-enforced | 27 gates son realmente executable | **59% de skill gates son ilusorios** |
| Condición invalidante | No existe | No existe | **Sin mecanismo** |

---

## 7. Gaps Críticos

### P0 — Ejecución insegura, doble autoridad, corrupción

| # | Gap | Sistema | Impacto | Evidencia |
|---|-----|---------|---------|-----------|
| 1 | **Skill bypassa AgentLaunchLifecycleService** | Borde | Spawns sin dedup, sin lease, sin audit | tmux-live launch → pi directo, sin request_launch() |
| 2 | **Dos SSOT para phase progress** | Borde | fork workflow status ≠ Memory MCP state | state-format.md vs state.py |
| 3 | **WorkflowState non-atomic writes** | Repo | Crash corrompe .claude/*.json | state.py:247,370,490 — json.dump sin temp+rename |
| 4 | **PromiseContract sin CAS** | Repo | Transiciones concurrentes se sobreescriben | promise_contract.py:137 — transition_to() sin expected-status |

### P1 — Drift, claims falsos, validación superficial

| # | Gap | Sistema | Impacto | Evidencia |
|---|-----|---------|---------|-----------|
| 5 | **47% de skill gates son PROMPT_ENFORCED** | Skill | LLM puede ignorar gates sin consecuencias | 33 de 70 gates = LLM self-enforced |
| 6 | **enforce-envelope no valida contenido** | Skill | Headers vacíos pasan como válido | REQUIRED_FIELDS solo checkea existencia |
| 7 | **Skill y repo son sistemas paralelos** | Borde | Duplicación de spawn, state, tasks, quality | 4 superficies duplicadas sin comunicación |
| 8 | **20 de 21 shell scripts sin tests** | Skill | Regresiones en gates no detectadas | Solo fork-verify.sh tiene tests |
| 9 | **7 contradicciones doc-vs-doc** | Skill | Instrucciones conflictivas al LLM | C1-C7 del primer reporte |

### P2 — Ergonomía, DX, documentación

| # | Gap | Sistema | Impacto | Evidencia |
|---|-----|---------|---------|-----------|
| 10 | Phase count 10 vs 12 | Skill | Ambigüedad | fork-run.md vs SKILL.md |
| 11 | `.fork/init.yaml` zombie file | Borde | Skill lo crea, repo no lo lee | init.md documenta fork init, no existe |
| 12 | TDD flag sin enforcement | Skill | Flag cosmético | tf:spawn injecta, nadie verifica |

---

## 8. Primer Cambio Mínimo Recomendado

### No crear un tercer sistema. No crear un wrapper. Cablear.

**Cambio**: `tmux-live launch` llama `AgentLaunchLifecycleService.request_launch()` antes de spawnear.

**Implementación mínima**:
1. Agregar CLI command `fork launch request --canonical-key KEY --surface skill --owner orchestrator`
2. `tmux-live launch` llama `fork launch request` antes de `pi --mode json -p`
3. `decision=claimed` → proceed, `decision=suppressed` → skip, `decision=error` → abort
4. Post-DONE: `fork launch confirm --launch-id ID`
5. Post-kill: `fork launch finalize --launch-id ID --status terminated`

**Por qué es correcto**:
- No crea sistema paralelo — usa la autoridad existente del repo
- No mueve autoridad — el repo ya es "ONLY component allowed"
- Contrato de borde explícito — skill no puede ejecutar sin PASS del repo
- Mínimo cambio — un subprocess call en tmux-live + un CLI command en repo

**Qué NO hacer**:
- NO crear `preflight-check` como wrapper más en la skill (añadiría otro sistema)
- NO mover lifecycle logic a la skill (descentralizaría la autoridad)
- NO requerir que la skill conozca SQLite internals (acoplaría)

---

## 9. Evidencia Reproducible

### Comandos ejecutados

```bash
# Skill gates
rg -n 'exit 1\|return 1\|die\|HARD' ~/.pi/agent/skills/tmux-fork-orchestrator/scripts/
rg -n 'FAIL_ABORT\|FAIL_RETRY\|STOP\|ABORT\|MUST' ~/.pi/agent/prompts/tf:*.md
rg -n 'SSOT\|source of truth\|authoritative' ~/.pi/agent/skills/tmux-fork-orchestrator/resources/

# Repo gates
rg -n 'can_transition_to\|cas_save\|_VALID_TRANSITIONS\|BLOCKING_STATUSES' ~/Developer/tmux_fork/src/
rg -n 'raise.*Error\|ValueError\|TaskTransitionError\|PhaseSkipError' ~/Developer/tmux_fork/src/

# Boundary
rg -n 'fork doctor\|fork init\|fork task\|fork message\|request_launch' ~/.pi/agent/skills/tmux-fork-orchestrator/
rg -n 'tmux-live\|enforce-envelope\|conflict-detect' ~/Developer/tmux_fork/src/
rg -n 'request_launch\|canonical_key\|launch_id' ~/Developer/tmux_fork/src/

# Crash safety
rg -n 'json\.dump\|temp\|rename\|atomic\|AtomicWriter' ~/Developer/tmux_fork/src/
rg -n 'lease\|lease_expires\|quarantine\|reconcile' ~/Developer/tmux_fork/src/

# Test coverage
fd test_ ~/Developer/tmux_fork/tests/ -e py | wc -l  # 60+ files
fd 'test_fork' ~/.pi/agent/skills/tmux-fork-orchestrator/scripts/ 2>/dev/null  # 1 file
```

### Archivos inspeccionados
- Skill: 21 scripts, 18 resources, 7 tf:* prompts, fork-run.md, SKILL.md, AGENTS.md (2)
- Repo: 230+ Python files, project scripts, Makefile, 60+ test files
- Boundary: cross-references between both systems

---

## 10. Riesgos Residuales

1. **Repo internamente inconsistente**: `workflow.py` bug-hunt llama `tmux-live` que bypassa `AgentLaunchLifecycleService`. Incluso si la skill se integra, el repo tiene su propio bypass.

2. **Parallel state machines sin convergencia**: Skill (Memory MCP) y repo (JSON files) trackean fases independientemente. No hay plan para converger.

3. **PromiseContract CAS gap no verificado in-vivo**: El race window es teórico — no se puede reproducir sin concurrent load testing.

4. **LLM self-enforcement effectiveness**: No hay forma de medir qué porcentaje de las veces el LLM cumple los 33 PROMPT_ENFORCED gates.

5. **`.fork/init.yaml` ownership undefined**: Ni skill ni repo tienen ownership claro de este archivo.
