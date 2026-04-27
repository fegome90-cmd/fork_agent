# Skill Gates — Actionable Fix List

> Scope: skill tmux-fork-orchestrator ONLY
> Date: 2026-04-24
> Evidence-based: every fix has a test command that proves the bug

---

## P0 — Gates que dicen que bloquean pero NO bloquean (o bloquean incorrectamente)

### Fix 1: enforce-envelope no parsea brackets en Artifacts
- **Qué**: `Artifacts: [a.md, b.md]` se parsea como `[a.md` y `b.md]` — incluye brackets como parte del path
- **Dónde**: `scripts/enforce-envelope` línea ~105 (`IFS=',' read -ra ARTIFACT_LIST`)
- **Evidencia**: `echo '## Artifacts: [/tmp/a.md, /tmp/b.md]' > /tmp/test.md && enforce-envelope /tmp/test.md` → CRITICAL: Artifact not found: [/tmp/a.md
- **Fix mínimo**: Agregar `ARTIFACTS_LINE="${ARTIFACTS_LINE//[\[\]]/}"` antes del IFS read
- **Impacto**: 5 de 7 tf:* prompts generan Artifacts con brackets → **toda validación de envelope FALLA en producción**

### Fix 2: Phase count 12 vs 10
- **Qué**: fork-run.md dice "12-phase", todo lo demás dice "10-phase"
- **Dónde**: `prompts/fork-run.md` línea 1
- **Evidencia**: `head -1 ~/.pi/agent/prompts/fork-run.md` → "12-phase"; `grep 'phase' SKILL.md` → "10-phase"
- **Fix mínimo**: Cambiar fork-run.md de "12-phase" a "10-phase (con sub-fases)"
- **Impacto**: Ambigüedad en comunicación, no rompe ejecución

### Fix 3: Plan gate — optional vs mandatory
- **Qué**: AGENTS.md dice "opcional pero recomendado", protocol.md y tf:plan.md dicen "STOP"
- **Dónde**: `~/Developer/tmux_fork/AGENTS.md` línea ~38
- **Evidencia**: grep "opcional" AGENTS.md → "opcional pero recomendado"; grep "STOP" tf:plan.md → "STOP. Present the plan"
- **Fix mínimo**: Cambiar AGENTS.md a "MANDATORIO (protocol.md §1.5)" o agregar nota que explique cuándo es optional
- **Impacto**: Agente puede saltear aprobación humana si lee AGENTS.md y no protocol.md

### Fix 4: SSOT conflict — SKILL.md vs state-format.md
- **Qué**: SKILL.md dice "Task list is source of truth", state-format.md dice "Memory MCP is SSOT"
- **Dónde**: `SKILL.md` línea 84, `resources/state-format.md` línea 5
- **Evidencia**: `grep 'source of truth' SKILL.md` vs `grep 'SSOT' state-format.md`
- **Fix mínimo**: Cambiar SKILL.md a "Task list is UI scaffold for phase progress. Memory MCP (see state-format.md) is SSOT."
- **Impacto**: Agente puede consultar pi-tasks como autoridad cuando Memory MCP diverge

### Fix 5: Governance self-contradiction
- **Qué**: governance.md línea 4 dice "advisory-only, no code enforcement", línea 80 define GateResult con FAIL_ABORT
- **Dónde**: `resources/governance.md` líneas 4 y 80
- **Evidencia**: grep ambas líneas
- **Fix mínimo**: Cambiar línea 4 a "Advisory LLM guidelines. GateResult describes EXPECTED behavior, not enforced behavior."
- **Impacto**: Falsa confianza en blocking behavior

---

## P1 — Gates que funcionan parcialmente o tienen gaps

### Fix 6: sdd-gate-skill referenced 8 times but doesn't exist as executable
- **Qué**: Referenciado en protocol.md, governance.md, phase-driver.md, sdd-bridge.md, tf:plan.md, tf:orchestrate.md
- **Dónde**: 8 files total
- **Evidencia**: `command -v sdd-gate-skill` → not found; `skill-hub sdd-gate` → skill exists in pi registry
- **Fix mínimo**: Verificar si la skill carga correctamente via skill-hub. Si sí, agregar nota en protocol.md que es una skill (no un script). Si no, marcar como DOC_ONLY.
- **Impacto**: Agente intenta "run sdd-gate-skill" sin saber si está instalado

### Fix 7: verification-loop referenced 2 times but unclear if executable
- **Qué**: Referenciado en tf:orchestrate.md y tf:validate.md
- **Dónde**: `prompts/tf:orchestrate.md` línea 45, `prompts/tf:validate.md` línea 34
- **Fix mínimo**: Mismo approach que Fix 6 — verificar si carga via skill-hub

### Fix 8: protocol.md references `memory save/search/session` CLI but bridge uses MCP tools
- **Qué**: protocol.md líneas 82-83 usan `memory save "text"` CLI syntax, pero la skill opera con `memory_save()` MCP tool
- **Dónde**: `resources/protocol.md` líneas 82-83, 146, 197
- **Evidencia**: `grep 'memory save\|memory session' protocol.md` → CLI syntax; bridge usa MCP tools
- **Fix mínimo**: Actualizar protocol.md para usar `memory_save(content="...", type="config")` syntax
- **Impacto**: Agente puede intentar CLI commands que no son su interfaz

### Fix 9: enforce-envelope no distingue "field exists but empty" de "field missing"
- **Qué**: Artifacts con valor vacío (`## Artifacts: `) pasa como WARNING, pero `## Status: ` (vacío) es CRITICAL. Inconsistencia.
- **Dónde**: `scripts/enforce-envelope` lógica de Status vs Artifacts
- **Evidencia**: Test con `## Status: ` → CRITICAL; test con `## Artifacts: ` → no check
- **Fix mínimo**: Uniformizar — si field existe pero está vacío, siempre WARNING (no CRITICAL)
- **Impacto**: Menor — pero genera confusión en agents que generan envelopes parciales

---

## P2 — Cosmetic, documentation, DX

### Fix 10: anchor_dope gates still referenced as "planned for v2"
- **Qué**: governance.md referencia scripts que no existen
- **Dónde**: `resources/governance.md` línea ~107
- **Fix mínimo**: Agregar "(deferred)" o mover a sección "Future Work"

### Fix 11: 18 orphan resources not referenced by any prompt
- **Qué**: Trifecta-indexed pero no prompt-referenced. Funcionales via search, pero no cargados explícitamente.
- **Dónde**: resources/ directory
- **Fix mínimo**: No action needed — Trifecta search los hace accesibles. Documentar en README.

### Fix 12: TDD flag without enforcement
- **Qué**: tf:spawn inyecta STRICT_TDD pero nadie verifica test existence
- **Dónde**: tf:spawn.md, tf:validate.md
- **Fix mínimo**: Agregar gate en tf:validate: "If STRICT_TDD was set, verify test files exist for modified code"

---

## Evidence Summary

| Fix | Test Command | Expected | Actual | Priority |
|-----|-------------|----------|--------|----------|
| 1 | `enforce-envelope` on `[a.md, b.md]` | EXIT 0 (valid) | EXIT 1 (BUG) | P0 |
| 2 | `head -1 fork-run.md` | "10-phase" | "12-phase" | P0 |
| 3 | `grep opcional AGENTS.md` | No results | "opcional pero recomendado" | P0 |
| 4 | `grep 'source of truth' SKILL.md` | Matches state-format | Contradicts state-format | P0 |
| 5 | `grep advisory governance.md` | Consistent | Self-contradicts | P0 |
| 6 | `command -v sdd-gate-skill` | Found | Not found | P1 |
| 8 | `grep 'memory save' protocol.md` | MCP syntax | CLI syntax | P1 |
