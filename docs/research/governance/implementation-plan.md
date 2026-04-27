# Governance Implementation Plan — Run Guide

> **Tipo:** Plan de implementación metodico, secuencial, por objetivos
> **Creado:** 2026-04-23
> **Estado:** Ready for execution
> **Principio:** ADDITIVE — nada se pierde, todo se extiende
> **Research:** `docs/research/governance/governance-integration-research.md`

---

## Secuencia de Runs

```
Run 0 (P0): Cleanup → Eliminar dead code + fix bugs en scripts
Run 1 (P1): Governance doc → Nuevo resource con la teoría unificada
Run 2 (P1): SDD bridge → Contratos concretos entre SDD y protocolo
Run 3 (P1): Protocol update → Phase 0-1.6 enriquecidos con CLOOP + gates
Run 4 (P1): SKILL.md update → Governance section + index limpio
Run 5 (P2): Quality Check → Single-pass post-validation check
Run 6 (P2): ~~Schema YAML~~ CANCELLED → moved to governance.md as reference table
```

**Dependencias:** Run 0 es prerequisito de todo. Run 1-2 son independientes entre sí. Run 3 depende de Run 1+2. Run 4 depende de Run 1+3. Run 5-6 son independientes.

---

## Run 0: Cleanup — Eliminar dead code + fix bugs

**Objetivo:** Dejar la skill limpia antes de agregar nada nuevo.
**Gate:** Scripts + CLI + tests funcionan idéntico después del cleanup.

### Acciones

**0a. Eliminar dead resources (2 archivos)**

```bash
rm ~/.pi/agent/skills/tmux-fork-orchestrator/resources/plannotator-gate.md
rm ~/.pi/agent/skills/tmux-fork-orchestrator/resources/sdd-integration-plan.md
```

- `plannotator-gate.md` — plannotator nunca se instaló, 5674 líneas muertas
- `sdd-integration-plan.md` — plan nunca implementado, 9388 líneas muertas

**0b. Fix bug en `trifecta-context-inject:438`**

```bash
# ANTES (hardcoded path):
FALLBACK_SCRIPT="/Users/felipe_gonzalez/.pi/agent/skills/tmux-fork-orchestrator/scripts/skill-resolver"

# DESPUÉS (usa SKILL_ROOT):
FALLBACK_SCRIPT="${SKILL_ROOT}/scripts/skill-resolver"
```

**0c. Fix bug en `trifecta-quality-report:116`**

```bash
# ANTES (--json no es flag válido):
trifecta telemetry report --json --last "$LAST"

# DESPUÉS (--format json es correcto):
trifecta telemetry report --format json --last "$LAST"
```

**0d. Fix bug en `detect-env`**

Agregar check de `--help` antes del `cd`:

```bash
# ANTES: "$1" se pasa directo a cd
cd "$1" 2>/dev/null || cd "$(pwd)"

# DESPUÉS: check --help primero
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    head -30 "$0"
    exit 0
fi
cd "${1:-$(pwd)}" 2>/dev/null || cd "$(pwd)"
```

### Verificación (Gate G0-G5)

```bash
# Todos los scripts parsean sin error
for s in ~/.pi/agent/skills/tmux-fork-orchestrator/scripts/*; do
  bash -n "$s" && echo "OK: $(basename $s)" || echo "FAIL: $(basename $s)"
done

# Tests existentes pasan
cd ~/Developer/tmux_fork && uv run pytest tests/ -v --tb=short

# CLI funciona
memory save "gate-test-$$" --project gate-test
memory search "gate-test" --project gate-test
fork doctor status
```

---

## Run 1: Governance Doc — Resource unificado

**Objetivo:** Documento que el orquestador carga en Phase 1.5 como governance layer.
**Output:** `resources/governance.md` (~120 líneas)
**Gate:** El archivo existe, carga dentro del context budget, y no modifica nada existente.

### Qué tomar de cada proyecto

| Fuente | Tomar | Ejemplo de código/lógica |
|--------|-------|------------------------|
| **CLOOP** | Metodología Clarify→Layout→Operate→Observe→Reflect | Ver §CLOOP abajo |
| **anchor_dope** | ~~Removed from v1~~ (scripts don't exist) | See governance-authority-closure.md D2 |
| **spec-kit** | Coverage gap detection + clarification questioning | Ver §spec-kit abajo |
| **OpenSpec** | specs/ vs changes/ topology + schema YAML | Ver §OpenSpec abajo |
| **SDD** | Delta spec format + compliance matrix | Ya lo tenemos, solo documentar |

### Estructura del documento

```markdown
# Governance Layer

## When to Load
Phase 1 (Plan) when governance is active.

## Detection
Governance is active when `GOVERNANCE=1` env var is set (user export).
Otherwise, protocol runs without governance (identical to pre-governance behavior).

**Advisory-only notice:** GOVERNANCE=1 is advisory guidelines for the AI orchestrator.
It has no code-level enforcement. The orchestrator reads protocol.md text and follows
governance-mode branches when the env var is set. There is no script, hook, or code
that gates this behavior. See authority flow audit for details.

**Config system note:** `.fork_agent.yaml` and `.fork/init.yaml` are both effectively
dead config — ForkAgentConfig.load() has zero runtime consumers, DI container hardcodes
all defaults. Do NOT add `governance: bool` to WorkspaceConfigModel until the config
system is fixed (separate work order). Use `GOVERNANCE=1` env var only.

## CLOOP: Planning Methodology
[Metodología CLOOP completa con ejemplos]

## Pre-flight Gates
[6 infrastructure gates only — anchor_dope gates deferred to v2]

## Spec System
[Delta specs format + compliance matrix]

## Quality Check
[Phase 5.7 — single-pass check. Iterative loop deferred to v2.]
```

### Ejemplo: CLOOP Clarify en Phase 0

Tomado de `plan-architect/SKILL.md`, adaptado como dispatch:

```markdown
## Phase 0: Clarify (Governance Mode)

When `plan-architect` skill is available via skill-hub, delegate:

### CLOOP Clarify
1. Extract SMART goal from user request
2. Identify implicit hypotheses (what we assume but isn't stated)
3. Define success criteria (measurable, testable)

Output format:
- **Goal:** [SMART statement]
- **Hypotheses:** [list, each falsifiable]
- **Success Criteria:** [checklist]

When plan-architect is NOT available, use inline clarification:
Ask 2-3 targeted questions about DECISIONS (scope, testing bar).
Skip when unambiguous. Max 6 rounds.
```

### Infrastructure Gates (6 checks, v1)

> **Note:** anchor_dope context gates (Context, Phase, Surface, Clean State) are **planned for v2**.
> Scripts (`new_sprint_pack.sh`, `doctor.sh`) and ANCHOR.md don't exist yet.
> See governance-authority-closure.md D2.

```markdown
## Phase 1.6: Gate Sequence (v1)

Run gates in order. Any gate FAIL_ABORT → STOP.

| # | Gate | Condition | Evidence |
|---|------|-----------|----------|
| 1 | Acceptance criteria | Every subtask has measurable criteria | Checklist confirmed |
| 2 | Skill injection | skill-resolver produced output | File exists |
| 3 | TDD flag | Code tasks have TDD mode | Instructions present |
| 4 | Clean state | Tests and lint pass before change | Exit code 0 |
| 5 | Trifecta daemon | Daemon warm (if available) | Health check |
| 6 | Metrics | KPIs + thresholds defined | Declared in plan |
```

### Artifact DAG (reference table — conceptual only, no runtime validation)

| Artifact | Produces | Requires | Notes |
|----------|----------|----------|-------|
| plan | PLAN.md | — | Always produced |
| anchor | ANCHOR.md | plan | **Removed from v1** (scripts don't exist) |
| proposal | sdd/{change}/proposal | plan | mem_save() MCP |
| spec | sdd/{change}/spec | proposal | mem_save() MCP |
| design | sdd/{change}/design | proposal | mem_save() MCP |
| tasks | sdd/{change}/tasks | spec + design | mem_save() MCP |
| gate_report | inline | spec + design + tasks | Blocking: FAIL stops pipeline |
| apply_progress | sdd/{change}/apply-progress | tasks + gate_report | Tracks tasks |
| verify_report | sdd/{change}/verify-report | apply_progress | Compliance matrix |
| quality_report | quality/{change}/report | verify_report | Single-pass in v1 |
| archive | sdd/{change}/archive-report | quality_report | Merge delta→main specs |

### Quality Check (Phase 5.7) — Decision Tree

*Single-pass quality check for v1. Iterative loop deferred to future enhancement.*

```
Phase 5.5 verdict = ?
├── FAIL → STOP, return to Phase 3 (fix)
└── PASS/PASS WITH WARNINGS →
    ├── Run static analysis
    │   ├── ruff check → warnings?
    │   └── mypy → type errors?
    ├── Run tests
    │   └── pytest → failures?
    ├── Count total warnings
    │   ├── 0 → PASS, proceed to Phase 6
    │   ├── 1-5 → LOG warnings, proceed to Phase 6
    │   └── >5 → ESCALATE: ask human (proceed with warnings / abort / manual fix)
    └── Save quality report via mem_save()
```

### Output: Quality Report
| Metric | Value |
|--------|-------|
| Warnings found | N |
| Lint violations | N |
| Type errors | N |
| Test failures | N |
| Verdict | PASS / PASS WITH WARNINGS / ESCALATED |

### Final step
1. Save quality report via mem_save() with topic_key `quality/{change}/report`
2. If PASS: suggest commit + PR
3. If ESCALATED: wait for human decision

---

## Run 2: SDD Bridge — Contratos concretos

**Objetivo:** Documento que define cómo SDD skills se conectan al protocolo.
**Output:** `resources/sdd-bridge.md` (~80 líneas)
**Gate:** El documento existe y referencia skills existentes sin modificarlos.

### Contratos

```markdown
# SDD Bridge — Protocol ↔ Skills Integration

## When to Load
Phase 1 (Plan) when governance is active AND SDD skills are available.

## Detection
Check: `skill-hub "sdd-propose"` returns a result.

## Phase Mapping

| Protocol Phase | SDD Skill | Input | Output | Persistence |
|---------------|-----------|-------|--------|-------------|
| Phase 0 | sdd-explore | Task description | Exploration analysis | `mem_save(topic_key="sdd/{change}/explore")` |
| Phase 1 | sdd-propose | Explore + CLOOP output | Proposal.md | `mem_save(topic_key="sdd/{change}/proposal")` |
| Phase 1 | sdd-spec | Proposal | Delta specs | `mem_save(topic_key="sdd/{change}/spec")` |
| Phase 1 | sdd-design | Proposal + spec | Design doc | `mem_save(topic_key="sdd/{change}/design")` |
| Phase 1 | sdd-tasks | Spec + design | Task checklist | `mem_save(topic_key="sdd/{change}/tasks")` |
| Phase 1.5 | sdd-gate | Spec + design + tasks | Gate verdict | Inline (no artifact) |
| Phase 1.6 | sdd-init | env detection | Project context | Cached |
| Phase 3 | — | sdd-tasks output | Agent assignment | — |
| Phase 5.5 | sdd-verify | All artifacts | Compliance matrix | `mem_save(topic_key="sdd/{change}/verify-report")` |
| Phase 6 | sdd-archive | Verify report | Spec sync + archive | `mem_save(topic_key="sdd/{change}/archive-report")` |

## Persistence Contract

**AUDIT FIX:** SDD uses `mem_save()` MCP tool, NOT `memory save` CLI.

```python
# Topic key convention (verified across all 9 SDD skills)
topic_key = f"sdd/{change_name}/{artifact_type}"

# Save (MCP tool call)
mem_save(
    title="SDD Proposal: {change}",
    topic_key="sdd/{change}/proposal",
    type="architecture",
    project="{project}",
    content="..."
)

# Retrieve (two-step: search for preview, get for full content)
mem_search(query="sdd/{change}/")  # returns 300-char previews
mem_get_observation(id="{observation_id}")  # full content REQUIRED
```

**NOTE:** `mem_search` returns 300-char previews only. `mem_get_observation(id)` is REQUIRED for full content.

## Agent Assignment Mapping

**AUDIT FIX:** sdd-tasks produces standard markdown checklists with NO parallel markers.
The `[P]` convention was INVENTED by the plan. sdd-apply is a single sequential agent.

### Correct mapping (post-audit):
1. Orchestrator receives sdd-tasks output (flat markdown checklist)
2. Orchestrator analyzes tasks for parallelism (manual, based on file dependencies)
3. Orchestrator splits into subtask groups:
   - Tasks referencing same files → same agent (sequential)
   - Independent tasks → parallel agents
   - Test tasks → verifier agent
4. Each group gets a `tmux-live launch` with the task subset in the prompt

This mapping is ORCHESTRATOR-driven, not tool-driven.

## Fallback

When SDD skills are NOT available:
- Phase 1 uses ad-hoc decomposition (as today)
- Phase 5.5 uses inline spec compliance check (as today)
- Phase 6 uses cleanup only (no spec sync)

## SDD Prerequisites

- `sdd-init` must have been run before any SDD workflow
- Every SDD sub-agent receives `artifact_store.mode` from the orchestrator
- Return envelope contract: status, summary, artifacts, next_recommended, risks, skill_resolution
- sdd-gate has degraded modes: oracle→explore fallback, agent timeout downgrades, fail-closed BLOCK
```

---

## Run 3: Protocol Update — Phase 0-1.6 enriquecidos

**Objetivo:** Modificar `resources/protocol.md` para incorporar governance.
**Gate:** Sin GOVERNANCE=1, el protocolo lee idéntico a hoy. Con GOVERNANCE=1, las fases se enriquecen.

### Cambios concretos

**Phase 0 — Cambio mínimo:**

```markdown
## Phase 0: Clarify

**Default:** Ask 2-3 targeted questions BEFORE decomposing. Skip when unambiguous.
**Governance mode (GOVERNANCE=1):** Delegate to CLOOP Clarify via plan-architect skill.
Load `resources/governance.md` §CLOOP for details.
```

**Phase 1 — Agregar SDD dispatch:**

```markdown
## Phase 1: Plan

1-7. [existing steps unchanged]

7b. **Governance decomposition** (when GOVERNANCE=1):
    If SDD skills available → run sdd-propose → sdd-spec → sdd-design → sdd-tasks
    See `resources/sdd-bridge.md` for mapping.
    Output *may inform* subtask decomposition from step 2 (enrichment, not replacement).

7c. **~~anchor_dope stamping~~ Removed from v1** (scripts don't exist):
    Orchestrator generates PLAN.md (as today). No ANCHOR.md interaction.
```

**Phase 1.5 — Replace plannotator with sdd-gate:**

```markdown
## Phase 1.5: Plan Gate

**Default:** Present plan in chat → user approves. On deny: incorporate feedback.

**Governance mode (advisory):**
1. Run sdd-gate-skill (automated quality check) — BLOCK on critical findings
2. If gate PASS → forward to human for approval
3. Human has final veto (can reject even if gate passed)
4. Full gate sequence in `resources/governance.md` §Gates
```

### GateResult Table (for governance.md)

| Gate | On PASS | On FAIL | Recovery | Max retries |
|------|---------|---------|----------|-------------|
| 1. Acceptance criteria | → next gate | → FAIL_RETRY | Return to Phase 1 | 1 |
| 2. Skill injection | → next gate | → FAIL_ABORT | ABORT (can't spawn without skills) | 0 |
| 3. TDD flag | → next gate | → WARN (proceed) | Add TDD instructions inline | 0 |
| 4. Clean state | → next gate | → FAIL_ABORT | Fix tests/lint first | 0 |
| 5. Trifecta daemon | → next gate | → WARN (proceed) | Daemon may be cold | 0 |
| 6. Metrics defined | → next gate | → FAIL_RETRY | Define KPIs before proceeding | 1 |

GateResult enum: PASS | WARN (proceed with log) | FAIL_RETRY (return, max N) | FAIL_ABORT (stop)
Human override: allowed on any gate, must log reason.

**Phase 1.6 — Merge gates:**

```markdown
## Phase 1.6: Pre-flight Check (Gate)

**Default:** [existing 6 checks unchanged]

**Governance mode (advisory):** Add infrastructure gates (see governance.md §Gates).
Run acceptance and skill gates first (blocking), then TDD and metrics (non-blocking).
```

---

## Run 4: SKILL.md Update — Governance section + index limpio

**Objetivo:** Agregar governance al SKILL.md y limpiar Resources Index.
**Gate:** SKILL.md carga dentro del context budget (~300 líneas).

### Cambios

**Nuevo section después de "Orchestration Mode":**

```markdown
## Governance Mode

**Advisory-only:** GOVERNANCE=1 env var activates advisory guidelines for the AI
orchestrator. No code-level enforcement. Config file NOT used (see authority audit).

When active, protocol phases are enriched with:
- **CLOOP** planning methodology (Clarify→Layout→Operate→Observe→Reflect) — *optional enrichment*
- **SDD** spec decomposition (propose→spec→design→tasks→gate→apply→verify→archive)
- **Quality Check** (Phase 5.7: single-pass review)

> **anchor_dope** removed from v1 (scripts don't exist). Planned for v2.

Details: `resources/governance.md`
SDD contracts: `resources/sdd-bridge.md`

**Without GOVERNANCE=1, everything works identically to today.**
No functionality is removed or degraded. All layers degrade gracefully.
```

**Resources Index — eliminar 2 entries muertos:**

Eliminar del index:
- `resources/plannotator-gate.md` (DEAD — eliminado en Run 0)
- `resources/sdd-integration-plan.md` (DEAD — eliminado en Run 0)

Agregar al index:
- `resources/governance.md` — Governance layer completo
- `resources/sdd-bridge.md` — SDD protocol contracts

---

## Run 5: Quality Check — Phase 5.7

**Objetivo:** Single-pass quality check entre Validate y Cleanup.
**Gate:** Phase 5.5 funciona idéntico. Phase 5.7 es additive.
**Depends on:** Run 3 (both modify protocol.md)

### Decision tree (AI agent reads this, not bash)

```
Phase 5.5 verdict = ?
├── FAIL → STOP, return to Phase 3 (fix)
└── PASS/PASS WITH WARNINGS →
    ├── Run static analysis (ruff, mypy)
    ├── Run tests (pytest)
    ├── Count total warnings
    │   ├── 0 → PASS
    │   ├── 1-5 → LOG warnings, proceed to Phase 6
    │   └── >5 → ESCALATE: ask human (proceed with warnings / abort)
    └── Save quality report via mem_save()
```

### Quality Report (saved via mem_save)

| Metric | Value |
|--------|-------|
| Lint violations | N |
| Type errors | N |
| Test failures | N |
| Total warnings | N |
| Verdict | PASS / WARN / ESCALATED |

### Verification command

```bash
cd "${PROJECT_DIR}" && uv run ruff check src/ 2>/dev/null | head -5
uv run mypy src/ 2>/dev/null | grep -c "error:"
uv run pytest tests/ --tb=no -q 2>/dev/null | tail -3
```

---

## Run 6: ~~Schema YAML~~ CANCELLED

**Authority flow audit finding:** `.fork/schema.yaml` is FALSE AUTHORITY.
- No code reads or validates it
- Creates split-brain risk (schema says X, protocol does Y)
- A YAML file in `.fork/` implies runtime validation that doesn't exist

**Resolution:** Artifact DAG moves INTO `resources/governance.md` as a markdown reference table.
If schema validation is wanted later, create a work order with an actual validator.

---

## Dependencias Visuales

```
Run 0 (cleanup)
  ├── Run 1 (governance.md) ──┐
  └── Run 2 (sdd-bridge.md) ──┤
                               ├── Run 3 (protocol update) ── Run 4 (SKILL.md)
                               │                              └── Run 5 (quality check)
                               └── Run 6 (CANCELLED)
```

## ¿Qué NO hacemos en este run?

| Item | Por qué | Cuándo |
|------|--------|--------|
| Implementar anchor_dope scripts | Falta otro agente (fork task/poll) | Después de que termine |
| Modificar CLI workflow outline | outline es state tracker, no decomposition | Después de protocol update |
| Crear constitution.md | Depende de definir el contenido | Después de governance.md |
| SDD skill modifications | Skills son independientes del protocolo | Run separado |
| Fork task/poll CLI | Otro agente trabaja en eso | Esperar |

## ¿Qué SÍ hacemos?

| Run | Output | Líneas estimadas |
|-----|--------|-----------------|
| 0 | 2 archivos eliminados, 3 bugs fixeados | ~10 líneas cambiadas |
| 1 | `resources/governance.md` | ~120 líneas nuevas |
| 2 | `resources/sdd-bridge.md` | ~80 líneas nuevas |
| 3 | `resources/protocol.md` actualizado | ~40 líneas cambiadas |
| 4 | `SKILL.md` actualizado | ~20 líneas cambiadas |
| 5 | Phase 5.7 en protocol.md | ~50 líneas nuevas |
| 6 | ~~CANCELLED~~ (DAG absorbed into governance.md) | 0 líneas |

**Total: ~320 líneas nuevas/cambiadas, 0 líneas eliminadas (excepto dead resources).**

---

## Historial

| Fecha | Cambio |
|-------|--------|
| 2026-04-23 | Creación del plan de implementación metodico y secuencial |
| 2026-04-23 | Pre-impl exploration: ForkAgentConfig (Pydantic frozen), 18 scripts OK, plannotator in 3 files, sdd-phase-common exists at _shared/, 20 event types, HookService.dispatch() available |

---

## Pre-Implementation Findings

### Config Authority (AUDITED 2026-04-23)
- `.fork_agent.yaml` = **DEAD CONFIG** — ForkAgentConfig.load() exists but has 0 runtime consumers
- `.fork/init.yaml` = **ORPHAN** — 0 references in src/
- `_container_di.py:156` = **TRUE AUTHORITY** — hardcodes WorkspaceConfig defaults
- **GOVERNANCE=1 env var** = **ONLY** feature flag mechanism (like FORK_HYBRID=1)
- Do NOT add governance to WorkspaceConfigModel — it would be cosmetic, not functional
- Config system fix is a SEPARATE WORK ORDER (wire ForkAgentConfig.load() into DI container)

### Event System
- 20 event types in `events.py` including `WorkflowOutlineStartEvent/CompleteEvent`
- `HookService.dispatch(event)` — can hook governance into outline events
- Hook dispatcher loaded from `hooks_dir` in config

### Feature Flag Pattern
- `FORK_HYBRID=1` → hybrid dispatch in `hybrid.py` (line 231)
- `FORK_MCP_DISABLED=1` → skip MCP client (line 231)
- `FORK_MCP_REQUIRE=1` → hard-fail on MCP (line 235-277)
- **Governance:** Use `GOVERNANCE=1` env var only (FORK_HYBRID pattern), NO config model change

### topic_key Usage
- Existing: `topic_key` in `diff_service.py` for comparison keys
- No `sdd/` namespace in use — safe to adopt `sdd/{change}/{artifact}` convention

### SDD _shared
- `sdd-phase-common.md` exists at `~/.pi/agent/skills/_shared/sdd-phase-common.md`
- Defines sections A (skill loading), B (retrieval), C (persistence), D (return envelope)

### Cleanup Scope (exact)
- **plannotator references:** 3 files
  1. `resources/plannotator-gate.md` — DELETE file
  2. `resources/protocol.md` lines 4, 38-39 — UPDATE text
  3. `SKILL.md` line 164 — REMOVE entry from Resources Index
- **sdd-integration-plan.md:** `SKILL.md` line 197 — REMOVE entry, DELETE file
- **known-issues.md:** Issues #7 and #15 marked FIXED — MOVE to archive section
- **All 18 scripts:** Present and executable

### Script Bugs (exact locations)
1. `trifecta-context-inject:438` → hardcoded path
2. `trifecta-quality-report:116` → `--json` should be `--format json`
3. `detect-env` → no `--help` handling before `cd`


## Authority Flow Audit — Plan Defects (2026-04-23)

3 parallel audit agents: artifact writers, pipeline conflicts, SDD verification.

### Plan Claims Verified ✅
| Claim | Status | Evidence |
|-------|--------|---------|
| sdd-gate 3-agent dispatch | TRUE | sdd-structure, sdd-design, sdd-risk agents |
| topic_key = sdd/{change}/{artifact} | TRUE | Verified across all 9 skills |
| sdd-archive merges delta→main | TRUE | ADDED→append, MODIFIED→replace, REMOVED→delete |
| Compliance matrix format | TRUE | Markdown table with COMPLIANT/FAILING/UNTESTED/PARTIAL |
| FORK_HYBRID=1 pattern works | TRUE | 6 Python files check it inline |

### Plan Defects Fixed ✅
| Defect | Fix Applied |
|--------|------------|
| `[P]` parallel marker invented | Removed. Orchestrator-driven parallelism instead |
| `memory save` CLI syntax wrong | Changed to `mem_save()` MCP tool calls |
| `.fork/schema.yaml` false authority | Run 6 CANCELLED, DAG moves to governance.md |
| Two-step retrieval not documented | Added `mem_get_observation(id)` requirement |

### Open Issues for Implementation (7)
| # | Issue | Severity | Run affected | Action |
|---|-------|----------|-------------|--------|
| O1 | GOVERNANCE=1 is advisory prose, no code enforcement | HIGH | Run 3 | Accept as advisory guidelines, not feature flag. Document clearly. |
| O2 | anchor_dope gates reference non-existent scripts | HIGH | Run 1 | Gate the gates: only run if ANCHOR.md exists AND scripts are executable |
| O3 | Gate FAIL recovery undefined ("STOP" ambiguous) | HIGH | Run 3 | Define per-gate recovery: return to Phase X, retry, abort, ask human |
| O4 | Human override of sdd-gate BLOCK — authority vacuum | HIGH | Run 3 | Log override + reason. Human has final veto but must acknowledge. |
| O5 | Quality loop bug-hunt requires tmux, no fallback | MEDIUM | Run 5 | Add tmux detection guard, skip bug-hunt if not in tmux |
| O6 | MAX_ITERATIONS exhaustion — no escalation | MEDIUM | Run 5 | Save quality report, log remaining warnings, request human decision |
| O7 | Context budget pressure from SDD artifacts | MEDIUM | Run 2 | Define budget allocation: 1500 chars for SDD context, 1500 for task |

### Authority Vacuums (5)
| # | Decision Point | Who Decides | Status |
|---|---------------|-------------|--------|
| AV1 | Is plan-architect "available enough"? | Orchestrator with criteria | Needs criteria definition |
| AV2 | Human overrides sdd-gate BLOCK | Human with mandatory acknowledgment | Needs logging |
| AV3 | MAX_ITERATIONS reached, warnings > 0 | Human (escalation) | Needs escalation path |
| AV4 | sdd-archive merge conflict | Human with conflict summary | Needs resolution strategy |
| AV5 | anchor_dope gate FAIL — retry or skip? | Orchestrator with fallback | Needs fallback definition |

## mr-plan-eval Report (2026-04-23)

**Preset:** comprehensive (7 agents, 3 batches)
**Result:** 6/7 agents reported, 49 findings (C=7 H=17 M=18 L=7)
**Recommendation:** BLOCK (auto) → REVIEW (manual override with justification)

### Fixes Applied from Report

**Group 1: Run 6 zombie cleanup** (2C, 1H)
- Remove Run 6 from "¿Qué SÍ hacemos?" table and line count totals
- Update totals: ~320 lines (not 380)
- Artifact DAG is in governance.md only, no YAML file

**Group 2: Governance enforcement framing** (3C, 2H)
- Label ALL governance-mode blocks as "advisory guidelines" not "feature flags"
- Add disclaimer to governance.md: "This document provides advisory guidelines for the AI orchestrator. It has no code-level enforcement. The orchestrator follows these guidelines when GOVERNANCE=1 is set."
- Document exact GOVERNANCE=1 mechanism: user exports env var, orchestrator reads protocol.md text

**Group 3: Gate recovery** (5H)
- Define GateResult for each gate: PASS / FAIL_RETRY / FAIL_ABORT / FAIL_ESCALATE
- Add recovery column to gate tables in Run 1 and Run 3
- Protocol.md governance blocks: hook/dispatch pattern, not inline expansion

**Group 4: Quality loop** (3H)
- Replace bash pseudocode with decision-tree description matching AI agent operation
- Align persistence to MCP tools (mem_save/mem_search), not CLI
- Quote all variables, validate PROJECT_DIR before cd
- Simplify initial implementation: single-pass check, iterative loop deferred

**Group 5: Run 5 depends on Run 3** (1H)
- Both modify protocol.md — update dependency graph

**Group 6: Test strategy** (2C, 2H)
- Golden-file snapshot of protocol.md default phases (pre-governance)
- One integration test per Run 0 bug fix
- Mock MCP fixture for SDD bridge tests (deferred to post-implementation)

### What We're NOT Doing (from report)

| Report Recommendation | Decision | Reason |
|----------------------|----------|--------|
| Build gate-checker script | DEFER | Over-engineering for advisory guidelines |
| E2E governance test | DEFER | No code change to test — governance is text-only |
| Bats-core shell tests | DEFER | Quality loop simplified to single-pass |
| Mock MCP server fixture | DEFER | SDD bridge is a doc, not code |
| Build schema YAML validator | CANCELLED | Run 6 cancelled entirely |

### Recommendation Override

The report says BLOCK. Manual override to **PROCEED WITH CONDITIONS**:

1. Apply fixes from Groups 1-5 before execution
2. Accept governance as advisory (Group 2) — no code enforcement
3. Simplify quality loop to single-pass (Group 4)
4. Gate recovery table added to Run 1/3 (Group 3)
5. Test strategy: snapshot test for protocol.md + integration tests for Run 0 bug fixes only

Risk accepted: governance is advisory text, not runtime code. The 7 CRITICAL findings are
all consequences of this architectural decision, which is intentional and documented.

### mr-plan-eval v2 (quick, post-corrections)

**Preset:** quick (2 agents: structure + risk)
**Result:** 2/2 agents, 16 findings (C=0 H=4 M=8 L=4)
**Recommendation:** CAUTION (proceed with awareness)
**Improvement from v1:** 49→16 findings, 7→0 CRITICAL, BLOCK→CAUTION

#### Remaining HIGH items (accepted)

| # | Finding | Action | Status |
|---|---------|--------|--------|
| H1 | Dependency tree missing Run 5→Run 3 | ASCII tree already updated | DONE |
| H2 | Run 0 scope gap (deletions vs text updates) | Document that Run 0 is "file+script only", text updates in Run 3-4 | ACCEPT |
| H3 | Full-text search before deletion | grep -rl across ~/.pi/ and ~/Developer/ | EXECUTE in Run 0 |
| H4 | Authority vacuums need resolution | AV1-AV5 have decision-makers assigned in table | ACCEPT |

#### Remaining MEDIUM items (accepted)

| # | Finding | Action |
|---|---------|--------|
| M1 | Collapse Run 6 references | Already collapsed to CANCELLED section |
| M2 | Merge audit findings into Runs | Deferred — audit trail is valuable |
| M3 | Context budget DoD | Add line count gate: governance.md <150 lines |
| M4 | Simplify GateResult | Keep 4-level enum, matches governance complexity |
| M5 | Run 5 dependency explicit | Already updated |
| M6 | Smoke test scripts | Add --dry-run to verification in Run 0 |
| M7 | Context budget measurement | Measure before/after Run 1 |
| M8 | Remove 2>/dev/null from verification | Accept — 2>/dev/null is intentional for non-blocking checks |
