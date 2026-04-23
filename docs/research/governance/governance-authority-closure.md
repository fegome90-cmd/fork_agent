# Governance Authority Closure

> **Date:** 2026-04-23
> **Status:** Pre-implementation gate
> **Inputs:** implementation-plan.md, authority-flow-audit.md, authority-flow-audit-plan.md, governance-integration-research.md
> **Principles applied:** single authority per surface, no parallel semantics, evidence ≠ authority, no naming inflation, fail-closed with explicit fallback, **adaptation not integration** (all external systems are adapted to tmux_fork's own MCP memory — nothing is consumed literally)

---

## 1. Veredicto

**READY WITH CONDITIONS**

El plan puede ejecutarse si se resuelven las 4 condiciones de §4 antes de Run 1.
Run 0 (cleanup) no requiere condiciones y puede ejecutarse inmediatamente.

---

## 2. Matriz de Autoridad Final

| Superficie | Rol | Autoridad real | Evidencia | Fallback | Estado |
|------------|-----|----------------|-----------|----------|--------|
| SKILL.md | Entry point del skill | Carga condicional de resources | skill-hub lo indexa | Si skill-hub no lo encuentra, no hay skill | live |
| protocol.md | SSOT de fases de orquestación | Define Phase 0-6 | El orquestador lo lee y sigue | Si no existe, el orquestador opera sin protocolo | live |
| resources/governance.md | Extensiones advisory para protocol.md | Ninguna — es texto que el orquestador puede seguir o ignorar | Ninguna — no hay código que lo enforce | Si GOVERNANCE!=1, no se carga | planned |
| resources/sdd-bridge.md | Contrato entre protocol y SDD skills | Ninguna — documento de coordinación | Ninguna — los skills no leen este archivo | Si SDD skills no existen, no se usa | planned |
| GOVERNANCE=1 env var | Mecanismo de activación | Ninguna — variable de entorno que el orquestador podría verificar | El orquestador es un LLM, no un proceso que checkea env vars | Si el LLM no verifica, governance se aplica siempre o nunca | advisory |
| PLAN.md | Plan de orquestación por sesión | Lo escribe Phase 1, lo lee Phase 3/5 | Archivo en disco (o memoria) | Si no existe, Phase 3 aborta | live |
| ANCHOR.md | SSOT del sprint (anchor_dope) | **No existe** — scripts no implementados | Ninguno | No aplica — no se puede verificar algo que no existe | vapor |
| sdd-* skills | Ciclo SDD completo | Cada skill es authority de su fase | Skills existen en disco, son cargados por skill-hub | Si skill-hub no los encuentra, se usa ad-hoc decomposition | live |
| GateResult table | Recovery semántico por gate | Ninguna — es texto en governance.md | Ninguna — no hay código que enforce PASS/FAIL_RETRY/FAIL_ABORT | El orquestador sigue el texto o no | planned |
| Quality Check (Phase 5.7) | Single-pass post-validation | Ninguna — es texto en protocol.md | Ninguna — no hay script que lo ejecute | Si el orquestador no lo ejecuta, se saltea | planned |
| Artifact DAG table | Referencia conceptual de dependencias | Ninguna — tabla markdown sin validator | Ninguna — nada lee esta tabla | Si está desactualizada, nadie se entera | planned |
| trifecta-context-inject | Inyección de contexto en Phase 3 | Script ejecutable que inyecta contexto | Corre en bash, produce output | Si falla, skill-resolver como fallback | live |
| detect-env | Detección de entorno en Phase 1.6 | Script ejecutable | Corre en bash | Si falla, se continua sin env info | live |
| trifecta-quality-report | Reporte de calidad en Phase 6 | Script ejecutable | Corre en bash | Si falla, cleanup procede sin reporte | live |

---

## 3. Resolución de Authority Vacuums (AV1–AV5)

### AV1: ¿Está plan-architect "suficientemente disponible" para delegar?

**Resolución:** No se delega. El orquestador usa CLOOP como *input opcional*, no como *dispatch obligatorio*.

- Si plan-architect responde a skill-hub → el orquestador *puede* usar su output para enriquecer Phase 0/1
- Si no responde → el orquestador usa inline clarification (comportamiento actual)
- No hay retry, no hay quality validation del output de CLOOP
- **Regla:** CLOOP es un *enricher*, no un *gate*. Su ausencia no bloquea nada.

**Por qué:** El plan dice "When plan-architect skill is available via skill-hub, delegate" pero skill-hub es búsqueda LLM-mediada — puede dar falsos positivos. Delegar obligatoriamente a algo que puede fallar crea un vacuum peor que no delegar. Si es optional enrichment, el vacuum desaparece.

### AV2: Human override de sdd-gate BLOCK

**Resolución:** sdd-gate corre primero. BLOCK auto-rechaza. Human no override BLOCK.

- sdd-gate BLOCK → auto-reject, nunca llega a human
- sdd-gate REVIEW → pasa a human con warning
- sdd-gate PASS → pasa a human para aprobación final
- Human puede RECHAZAR un PASS (veto final)
- Human NO puede APROBAR un BLOCK

**Por qué:** Si permitimos override de BLOCK, el gate pierde authority. Si el gate dice "critical finding" y un humano lo ignora sin trazabilidad, el gate era decorativo. Fail-closed: BLOCK es BLOCK.

### AV3: MAX_ITERATIONS reached — ya no aplica

**Resolución:** MAX_ITERATIONS se eliminó con el bash loop. Phase 5.7 es single-pass.

- Single-pass = una iteración, sin loop
- Si warnings > 5 → ESCALATE (pedir al humano)
- Si warnings 1-5 → LOG y proceder
- Si warnings 0 → PASS

**Por qué:** El bash loop con MAX_ITERATIONS=10 era over-engineering. Single-pass elimina el vacuum.

### AV4: sdd-archive merge conflict

**Resolución:** Merge conflict → BLOCK. Human decide con summary.

- sdd-archive detecta conflict (same requirement modified by two deltas)
- Produce conflict summary: requirement ID + delta A content + delta B content
- Guarda en memoria como blocked_merge
- Human recibe el summary y elige: keep A, keep B, manual merge
- sdd-archive no procede hasta que human resuelva

**Por qué:** Merge semántico sin estrategia de resolución es un vacuum. Fail-closed: si no se puede resolver automáticamente, para.

### AV5: anchor_dope gate FAIL — retry o skip?

**Resolución:** Las anchor_dope gates no se ejecutan en v1.

- anchor_dope gates requieren: ANCHOR.md existente + scripts ejecutables
- Ninguno de los dos existe
- En v1: solo se ejecutan los 6 infrastructure gates existentes del protocolo
- anchor_dope gates son "planned integration" — se agregan cuando los scripts existan

**Por qué:** Ejecutar gates que dependen de artefactos que no existen produce FAIL siempre, lo cual es un false negative. Si el gate siempre falla, no es un gate — es un error de diseño.

---

## 4. Decisiones Obligatorias

### D1: Mecanismo de activación — GOVERNANCE=1 opt-in

**Decisión:** GOVERNANCE=1 env var, opt-in. No always-on.

**Justificación:**
- Always-on con fast-path crearía dos semánticas paralelas: "activado por defecto pero se saltea si no hay necesidad". Eso es opt-in disfrazado.
- El protocolo tiene 10 fases que funcionan hoy sin governance. Agregar una capa que "siempre está ahí pero a veces no hace nada" infla la superficie sin agregar valor cuando no se necesita.
- Opt-in es explícito: si querés governance, lo pedís. Si no, el protocolo es exactamente el de hoy.
- El único costo de opt-in es que el usuario debe setear la env var. Eso es un feature, no un bug — hace explícita la decisión de usar governance.

**Contra-argumento rechazado:** "always-on degrada gracefully." Sí, pero degradation invisible no es lo mismo que no-activation. Siempre hay un code path que se evalúa, siempre hay texto que se lee, siempre hay budget que se consume. Opt-in elimina todo eso cuando no se necesita.

### D2: anchor_dope — remove from v1

**Decisión:** anchor_dope se remueve de v1 (Runs 1-5). Se menciona como "planned integration" en governance.md con una nota: "anchor_dope gates and ANCHOR.md are not active in v1. They require new_sprint_pack.sh and doctor.sh to be implemented."

**Justificación:**
- anchor_dope depende de 2 scripts que no existen (new_sprint_pack.sh, doctor.sh)
- ANCHOR.md no se genera porque no hay script que lo genere
- Las 4 anchor_dope gates requieren ANCHOR.md para funcionar
- doctor.sh (referenciado en Phase 5.5) no existe
- Integrar algo que no se puede ejecutar es integrar vapor

**Impacto en el plan:**
- Run 1 governance.md: anchor_dope gates se mueven a sección "Planned (v2)"
- Run 3 protocol.md Phase 1.6: solo infrastructure gates (6 existentes), no unified 10-gate sequence
- GateResult table: se reduce de 8 a 6 gates (solo infrastructure)
- Run 3 Phase 1 anchor_dope stamping: se elimina ("If ANCHOR.md exists → read it" → no existe)

### D3: Renombre — "Quality Check" no "Quality Loop"

**Decisión:** Se confirma "Quality Check" para v1. No se usa "Loop" en ningún artefacto.

**Justificación:**
- v1 es single-pass: una pasada de ruff + mypy + pytest → contar warnings → decidir
- No hay loop, no hay iteración, no hay MAX_ITERATIONS
- Llamarlo "Loop" cuando no loopea es naming inflation
- "Quality Check" describe exactamente lo que hace

**Corrección pendiente:**
- Línea 19 del plan: `Run 5 (P2): Quality Loop → Phase 5.7 + reporte final` → debe decir `Quality Check`
- Cualquier referencia a "Quality Loop" en governance.md debe decir "Quality Check"
- El section header "Quality Loop" en Run 1 example debe decir "Quality Check"

### D4: CLOOP — enricher, no replacement

**Decisión:** CLOOP no reemplaza Phase 0 ni Phase 1. Los enriquece opcionalmente.

**Justificación:**
- El research doc dice "Reemplazar — CLOOP es más riguroso" pero CLOOP es un skill externo que puede no estar disponible
- Reemplazar una fase del protocolo con algo que puede no existir crea un vacuum
- Si CLOOP no está → ¿qué corre en Phase 0? ¿el texto viejo que se "reemplazó"? ¿nada?
- Enrichment: si CLOOP está → output enriquece Phase 0/1. Si no → Phase 0/1 corren como hoy.
- El protocolo no modifica sus fases — agrega branches condicionales

---

## 5. Contradicciones Residuales

Si se ejecuta el plan sin este cierre, quedarían estas contradicciones:

| # | Contradicción | Dónde | Impacto |
|---|--------------|-------|---------|
| R1 | Línea 19 dice "Quality Loop" pero el cuerpo dice "Quality Check" | implementation-plan.md:19 vs :457 | Confusión en ejecución — ¿se itera o no? |
| R2 | anchor_dope gates en tabla GateResult (gates 1-4) pero scripts no existen | implementation-plan.md GateResult table | Gates 1-4 siempre fallan → false negatives |
| R3 | "Governance mode (GOVERNANCE=1)" aparece como branch en protocol.md pero GOVERNANCE=1 es advisory, no code-enforced | Run 3 proposed protocol text | El orquestador puede seguir governance sin GOVERNANCE=1 o ignorarlo con GOVERNANCE=1 |
| R4 | "Phase 1 never writes to ANCHOR.md" pero ANCHOR.md no existe | Run 3 Phase 1 7c | Proteger un archivo que no existe es noise |
| R5 | "memory workflow outline = state tracker" (research doc) vs "outline combines propose+spec+design+tasks" (research doc §4) | governance-integration-research.md §4 | Dos semánticas para el mismo comando |
| R6 | ~~SDD persistence mode mismatch~~ | **RESUELTO** — SDD skills se adaptan al MCP memory de tmux_fork directamente. No se usa engram ni openspec. La capa de persistencia se modifica para usar mem_save()/mem_search()/mem_get_observation() de tmux_fork. | Resuelto por decisión de adaptación |
| R7 | "Advisory-only" aparece 10 veces pero el plan usa lenguaje imperativo ("Run gates", "Delegate to CLOOP") | governance.md draft, protocol.md draft | Tensión entre "es advisory" y "haz esto" |

---

## 6. Qué Queda Cerrado

| Ítem | Decisión | Cómo se cierra |
|------|----------|---------------|
| Activación | GOVERNANCE=1 opt-in | D1 arriba |
| anchor_dope | Remove from v1 | D2 arriba |
| Nombre Phase 5.7 | "Quality Check", no "Quality Loop" | D3 arriba |
| CLOOP rol | Enricher, no replacement | D4 arriba |
| AV1 (CLOOP availability) | Optional enrichment | §3 AV1 |
| AV2 (human override) | No override de BLOCK | §3 AV2 |
| AV3 (MAX_ITERATIONS) | Eliminado con single-pass | §3 AV3 |
| Double-writer ANCHOR.md | No aplica — anchor_dope removido de v1 | D2 elimina el conflicto |
| CLOOP vs Phase 0 | No replacement — enrichment | D4 |
| CLOOP vs Phase 1 | No replacement — enrichment | D4 |
| Schema YAML | CANCELLED | Ya resuelto en plan |
| [P] parallel markers | ELIMINATED | Ya resuelto en plan |
| Persistence API | mem_save() MCP | Ya resuelto en plan |
| workflow outline vs SDD | outline es state tracker, no decomposition | outline stays as-is, SDD es parallel path opt-in |
| SDD persistence | Adaptado a MCP memory de tmux_fork | No se usa engram/openspec. Solo mem_save/search/get_observation. |

## 7. Qué Sigue Abierto

| Ítem | Estado | Bloquea? |
|------|--------|----------|
| R6: SDD persistence mode mismatch | **RESUELTO** — SDD no se usa literal. Se adapta al MCP memory de tmux_fork. No hay fricción con engram porque engram no participa. | Cerrado |
| R7: Advisory vs imperative language | **Unresolved** — tensión entre "advisory" y lenguaje imperativo. No se resuelve con命名, se resuelve con consistencia de lenguaje. | No bloquea ejecución. |
| GateResult enforcement | **Unresolved** — la tabla existe pero nada la lee. Es documentación, no código. | No bloquea — es advisory. |
| Config system dead | **Unresolved** — ForkAgentConfig no se usa. GOVERNANCE=1 no va en config. | No bloquea v1. Work order separado. |
| .fork/init.yaml orphan | **Unresolved** — existe pero nada lo lee. | No bloquea. Work order separado. |
| sdd-archive merge conflict resolution | **Resuelto en principio** (§3 AV4) pero sin implementación | No bloquea Runs 1-4. |

---

## 8. Diff Conceptual del Plan

Cambios requeridos al implementation-plan.md antes de ejecutar Runs 1-5:

### Run 1 (governance.md)
- **AGREGAR** disclaimer: "anchor_dope gates and ANCHOR.md are planned for v2. Only infrastructure gates (6) are active in v1."
- **MOVER** anchor_dope gates (gates 1-4) a sección "Planned (v2)"
- **REDUCIR** GateResult table de 8 a 6 gates
- **CAMBIAR** "Quality Loop" → "Quality Check" en §Quality Loop header
- **CAMBIAR** lenguaje imperativo a condicional: "If governance is active AND CLOOP is available, consider using..."

### Run 2 (sdd-bridge.md)
- **AGREGAR** nota: "SDD persistence uses tmux_fork's MCP memory (mem_save/mem_search/mem_get_observation) exclusively. No engram, no openspec. The sdd-phase-common.md contract is adapted, not consumed literally."
- **SIN CAMBIOS** en phase mapping o persistence contract

### Run 3 (protocol.md update)
- **ELIMINAR** Phase 1 7c (anchor_dope stamping) — no aplica en v1
- **SIMPLIFICAR** Phase 1.6 a 6 infrastructure gates (no unified 10-gate)
- **CAMBIAR** "Governance mode (GOVERNANCE=1):" → "Governance mode (advisory, when GOVERNANCE=1):"
- **AGREGAR** a Phase 0: "CLOOP enrichment is optional. If plan-architect skill is available, its output MAY be used to inform clarification. If not available, proceed with inline clarification."

### Run 4 (SKILL.md update)
- **CAMBIAR** "Quality Check" en vez de "Quality Loop"
- **SIN CAMBIOS** en Resources Index (agregar governance.md y sdd-bridge.md, remover plannotator y sdd-integration-plan)

### Run 5 (quality check)
- **CONFIRMAR** nombre "Quality Check"
- **SIN CAMBIOS** en decision tree

### Línea 19 (secuencia)
- **CAMBIAR** `Run 5 (P2): Quality Loop` → `Run 5 (P2): Quality Check`

---

*End of authority closure. Veredicto: READY WITH CONDITIONS (4 decisions must be applied before Run 1).*
