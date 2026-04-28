# Diff: Gentle-AI vs tmux_fork — Arquitectura de Instrucción Agentica

**Fecha**: 2026-04-28 | **Autor**: Fork Orchestrator | **Tipo**: Gap Analysis

---

## 1. Resumen Ejecutivo

| Dimensión                    | Gentle-AI                                                                                         | tmux_fork (nosotros)                                                                 | Gap         |
| ---------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ----------- |
| **Personalidad**             | `persona-gentleman.md` (8 secciones, anclas emocionales, diccionario de voseo)                    | `~/.pi/agent/AGENTS.md` (6 secciones, sin anclas)                                    | **MEDIO**   |
| **Inyección de identidad**   | Go binary → 11 agentes, 5 estrategias (MarkdownSections/FileReplace/Append/Instructions/Steering) | Pi carga `AGENTS.md` + SKILL.md al inicio, sin mecanismo de inyección                | **CRÍTICO** |
| **SDD Workflow**             | 9 fases, DAG, Init Guard, persistence contract (engram/openspec/hybrid/none), TDD enforcement     | 10 fases (protocol.md), sin Init Guard, sin persistence contract formal              | **ALTO**    |
| **Agent Adapters**           | Interface Go con 15+ métodos, factory, registry, detección automática, tier system                | Sin adapter formal. Prompt files manuales (`/tmp/fork-prompt-*.txt`)                 | **CRÍTICO** |
| **Skills**                   | 18 SKILL.md con frontmatter YAML, skill-resolver, registry generado, AGENTS.md como índice        | Skills externas (pi ecosystem), sin frontmatter, sin resolver, sin registry generado | **ALTO**    |
| **Component Pipeline**       | 7 componentes secuenciales: engram → persona → sdd → skills → mcp → permissions → gga             | 2 capas: AGENTS.md (global) + SKILL.md (on-demand)                                   | **ALTO**    |
| **Testing de instrucciones** | Golden tests (`testdata/golden/*.golden`) verifican output por agente                             | Sin tests de instrucciones agenticas                                                 | **MEDIO**   |
| **Sub-agent safety**         | Delegation Matrix (inline vs defer), Context Hygiene, Persistence Contract                        | Descubierto hoy: necesitamos `-nc` flag para evitar Role Confusion                   | **CRÍTICO** |

---

## 2. Persona: Diff Sección por Sección

### 2.1 Secciones que TENEMOS (alineados con Gentle-AI)

| Sección     | Gentle-AI                                                    | Nosotros                                                        | Veredicto      |
| ----------- | ------------------------------------------------------------ | --------------------------------------------------------------- | -------------- |
| Rules       | 7 reglas                                                     | 16 reglas (más estrictos)                                       | **SUPERIORES** |
| Personality | "Senior Architect, 15+, GDE & MVP, passionate teacher"       | "Senior backend architect, 15+, pragmatic"                      | **DIFERENTE**  |
| Language    | Rioplatense + English warm                                   | Rioplatense + English technical                                 | **DIFERENTE**  |
| Tone        | "Passionate, from CARING"                                    | "Direct, concise, technical prose"                              | **DIFERENTE**  |
| Philosophy  | 4 pilares (CONCEPTS>CODE, AI=TOOL, SOLID, AGAINST IMMEDIACY) | 6 pilares (+CORRECTNESS FIRST, IMPLICIT>EXPLICIT, NO SHORTCUTS) | **SUPERIORES** |
| Expertise   | Clean/Hex/Screaming, testing, Tmux, Zellij                   | Clean/Hex, Python 3.11+, TS, FastAPI, TDD, tmux, AI/ML, Nix     | **DIFERENTE**  |
| Behavior    | 4 items                                                      | 5 items (+pane splitter para paralelismo)                       | **ALINEADOS**  |
| Skills      | Tabla de auto-load                                           | Tabla de auto-load                                              | **ALINEADOS**  |

### 2.2 Secciones que NOS FALTAN

| Sección Gentle-AI                  | Descripción                                                                                                        | Por qué importa                                                                                      |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| **Ancla Emocional**                | "Gets frustrated when someone can do better but isn't — not out of anger, but because you CARE about their growth" | Define el _motivo_ del tono directo. Sin esto, el agente puede sonar arrogante en vez de preocupado. |
| **Diccionario de Voseo explícito** | Frases literales: "locura cósmica", "ponete las pilas", "hermano", "¿se entiende?"                                 | Fuerza al modelo a usar voseo real, no solo conjugaciones.                                           |
| **Speech Patterns**                | Preguntas retóricas, repetición por énfasis, anticipación de objeciones                                            | Define _cómo_ habla, no solo _en qué idioma_.                                                        |
| **Output Style**                   | Archivo separado con anti-sarcasmo, help-first default, collaborative partner                                      | Calibra el balance entre "te corrijo" y "te ayudo".                                                  |
| **Persona Neutral**                | Misma filosofía sin regionalismos                                                                                  | Para cuando se trabaja con equipos internacionales.                                                  |

### 2.3 Diferencias de Tono (Gentleman vs Pragmatist)

| Aspecto        | Gentleman                                                | Nosotros                                     | Recomendación                     |
| -------------- | -------------------------------------------------------- | -------------------------------------------- | --------------------------------- |
| **Motivación** | Caring — te corrijo porque me importa tu crecimiento     | Craft — me frustro porque la calidad importa | Adoptar Caring (es más humano)    |
| **Voseo**      | "loco", "hermano", "locura cósmica", "ponete las pilas"  | "bien", "es así", "dale", "verificá"         | Ampliar diccionario               |
| **English**    | "dude", "come on", "let me be real"                      | "here's the thing", "straight up"            | Mantener el nuestro (más técnico) |
| **Sarcasmo**   | "NEVER sarcastically or mockingly. No air quotes"        | Sin regla explícita                          | **AÑADIR**                        |
| **Help-first** | "Be helpful FIRST. You're a mentor, not an interrogator" | Sin regla explícita                          | **AÑADIR**                        |

---

## 3. Inyección de Identidad: Diff Arquitectónico

### 3.1 Gentle-AI Pipeline

```
Go Binary (gentle-ai install)
    │
    ├─ 1. Detect agents (11 adapters)
    ├─ 2. For each agent:
    │   ├─ persona/inject.go     → Strategy*: write persona to agent config
    │   ├─ sdd/inject.go         → Strategy*: write SDD orchestrator
    │   ├─ skills/inject.go      → Copy SKILL.md files to agent skills dir
    │   ├─ engram/inject.go      → Write MCP config for engram
    │   ├─ mcp/inject.go         → Write MCP config for Context7
    │   ├─ permissions/inject.go → Write security defaults
    │   └─ gga/config.go         → Write Git automation config
    └─ 3. Golden tests verify output per agent

Strategies: MarkdownSections | FileReplace | AppendToFile | InstructionsFile | SteeringFile
```

### 3.2 Nuestro Pipeline

```
Pi Session Start
    │
    ├─ 1. Load ~/.pi/agent/AGENTS.md (identity + rules)
    ├─ 2. Load project AGENTS.md (repo-specific)
    ├─ 3. Load SKILL.md (if context matches)
    ├─ 4. Load extensions (compact-memory-bridge, passive-capture, etc.)
    └─ 5. [SUB-AGENT] pi -nc -p @prompt.txt (manual, no pipeline)
```

### 3.3 Gap Analysis

| Capacidad                   | Gentle-AI                                               | Nosotros                               | Acción                                               |
| --------------------------- | ------------------------------------------------------- | -------------------------------------- | ---------------------------------------------------- |
| **Identity binding**        | Forzado por Go binary, 5 estrategias                    | Dependiente de que Pi cargue AGENTS.md | No aplicable (Pi lo hace bien)                       |
| **Sub-agent isolation**     | `-nc` equivalente nativo (cada adapter tiene su config) | Descubierto hoy: **NECESITAMOS `-nc`** | **FIX: ya documentado en plan**                      |
| **Idempotency**             | Byte comparison, managed sections, auto-heal            | Sin mecanismo                          | No crítico (Pi maneja sesiones)                      |
| **Multi-agent variants**    | 11 agentes, cada uno con adapter custom                 | 1 solo sistema (Pi)                    | No aplicable                                         |
| **Persistence enforcement** | Persistence Contract (4 modos)                          | "ALWAYS persist state to memory"       | **MEJORAR: formalizar contract**                     |
| **Golden tests**            | `testdata/golden/*.golden`                              | Sin tests de instrucciones             | **AÑADIR: test que verifique AGENTS.md parsea bien** |

---

## 4. SDD Orchestrator: Diff

### 4.1 Lo que Gentle-AI tiene y nosotros NO

| Feature                       | Gentle-AI                                                                            | Impacto                                          |
| ----------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------ |
| **Init Guard**                | Antes de CUALQUIER comando SDD, busca `sdd-init/{project}` en memoria                | Previene ejecutar fases sin contexto de proyecto |
| **Delegation Matrix**         | Tabla Inline vs Defer (read 1-3 files = inline, 4+ = defer)                          | Previene inflar contexto                         |
| **Persistence Contract**      | 4 modos: engram / openspec / hybrid / none con comportamiento por modo               | Define QUÉ hacer con artefactos                  |
| **TDD Forwarding**            | Orchestrator inyecta "STRICT TDD MODE IS ACTIVE" al sub-agente si init lo detectó    | TDD no es opcional cuando el proyecto lo soporta |
| **Model Assignment**          | Tabla por fase (opus = decisiones, sonnet = mecánico, haiku = cleanup)               | Optimiza costo/calidad por fase                  |
| **Size Classification**       | Small (<50 líneas) = directo, Medium (50-300) = spec nativa, Large (>300) = SDD full | No dispara SDD para cambios triviales            |
| **Artifact Store**            | `sdd/{change}/{artifact-type}` en engram con topic keys deterministas                | Recuperable entre sesiones                       |
| **Apply-Progress Continuity** | Merge obligatorio de progreso existente al continuar un batch                        | No pierde trabajo entre runs                     |
| **Skill Resolution Feedback** | `injected` / `fallback-registry` / `none` → self-correction si perdió contexto       | Auto-repara post-compaction                      |

### 4.2 Lo que NOSOTROS tenemos y Gentle-AI NO

| Feature                      | Nosotros                                             | Impacto                                    |
| ---------------------------- | ---------------------------------------------------- | ------------------------------------------ |
| **Trifecta context loading** | Grafo de conocimiento con búsqueda semántica         | Gentle-AI solo tiene Engram (FTS5)         |
| **tmux-live**                | Pane CRUD, visualización en vivo                     | Gentle-AI no tiene orquestación visual     |
| **Hybrid Mode**              | MCP directo (28ms) vs SDK (234ms)                    | Rendimiento superior                       |
| **10-phase protocol**        | Más fases que SDD (10 vs 9), con Plan Gate explícito | Governance más estricto                    |
| **Explorer Depth Selection** | locate vs analyze vs fallback con modelo asignado    | Optimiza costo por tipo de respuesta       |
| **Memory tools nativos**     | `memory_save/search/get/retrieve` como Pi tools      | Sin round-trip a CLI                       |
| **Sub-agent messaging**      | `fork message send/receive` para IPC                 | Gentle-AI no tiene mensajería inter-agente |

---

## 5. Skills System: Diff

### 5.1 Estructura de SKILL.md

| Aspecto                   | Gentle-AI                                              | Nosotros                                 | Gap                                    |
| ------------------------- | ------------------------------------------------------ | ---------------------------------------- | -------------------------------------- |
| **Frontmatter**           | YAML con name, description, license, metadata.version  | Sin frontmatter estándar                 | **AÑADIR**                             |
| **Trigger**               | En description: "Trigger: <when>"                      | En description del AGENTS.md skill index | **ALINEADO** (distinta ubicación)      |
| **Shared conventions**    | `_shared/` con resolver, persistence, engram, openspec | Sin shared conventions                   | **AÑADIR**                             |
| **Registry**              | `skill-registry/SKILL.md` generado por inject.go       | `skill-hub` CLI command                  | **ALINEADO** (distinta implementación) |
| **AGENTS.md como índice** | Tabla de skills con triggers                           | Tabla de skills con context              | **ALINEADO**                           |

### 5.2 Skill Resolver

| Aspecto             | Gentle-AI                                                                   | Nosotros                              |
| ------------------- | --------------------------------------------------------------------------- | ------------------------------------- |
| **Protocolo**       | `_shared/skill-resolver.md` define matching por code context + task context | `skill-hub "<query>"` busca por query |
| **Inyección**       | Compact rules → text inyectado en sub-agent prompt                          | Skill cargada on-demand por Pi        |
| **Feedback**        | `skill_resolution` field en result contract                                 | Sin feedback loop                     |
| **Self-correction** | Si `fallback-registry`, re-read registry inmediatamente                     | Sin mecanismo                         |

---

## 6. Veredicto: Lo que TENEMOS que hacer

### P0 — Crítico (rompe funcionalidad)

| #   | Acción                                                                                                    | Esfuerzo | Impacto                                  |
| --- | --------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------- |
| 1   | **Sub-agent Role Isolation**: Standardizar `pi -nc` + prompt con rol explícito para todos los sub-agentes | S        | Previene Orchestrator Hallucination      |
| 2   | **Persistence Contract**: Formalizar que TODO artefacto de sub-agente DEBE escribirse a disco via `write` | S        | Previene pérdida de hallazgos            |
| 3   | **Delegation Matrix**: Añadir tabla Inline vs Defer al AGENTS.md                                          | S        | Previene inflar contexto del orquestador |

### P1 — Alto (mejora calidad)

| #   | Acción                                                                                               | Esfuerso | Impacto                                  |
| --- | ---------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------- |
| 4   | **Persona Caring Anchor**: Adoptar "te corrijo porque me importa" como ancla emocional               | S        | Tono más humano                          |
| 5   | **Voseo Dictionary**: Ampliar con frases Gentleman ("ponete las pilas", "locura cósmica", "hermano") | S        | Personalidad más marcada                 |
| 6   | **Anti-sarcasm rule**: "NEVER sarcastically or mockingly"                                            | S        | Calibración de tono                      |
| 7   | **Help-first rule**: "Be helpful FIRST. Mentor, not interrogator"                                    | S        | Balance corrección/asistencia            |
| 8   | **Init Guard**: Antes de workflow, verificar contexto de proyecto en memoria                         | M        | Previene ejecutar sin contexto           |
| 9   | **Size Classification**: Skip workflow para cambios <50 líneas                                       | S        | No dispara maquinaria pesada para trivia |

### P2 — Medio (nice-to-have)

| #   | Acción                                                                       | Esfuerzo | Impacto                         |
| --- | ---------------------------------------------------------------------------- | -------- | ------------------------------- |
| 10  | **SKILL.md frontmatter**: Estandarizar YAML con name/description/version     | M        | Skills más descubribles         |
| 11  | **Golden tests**: Test que verifique AGENTS.md se parsea correctamente       | M        | Regression safety               |
| 12  | **Skill resolution feedback**: Añadir `skill_resolution` al result contract  | M        | Auto-reparación post-compaction |
| 13  | **Persona Neutral**: Variante sin regionalismos para equipos internacionales | S        | Flexibilidad                    |

---

## 7. Lo que NO copiamos (por diseño)

| Feature Gentle-AI          | Por qué NO                                                              |
| -------------------------- | ----------------------------------------------------------------------- |
| **Go binary injection**    | Nosotros usamos Pi, no un binario custom. No aplica.                    |
| **11 agent adapters**      | Nosotros tenemos 1 runtime (Pi). No necesitamos adapter pattern.        |
| **5 injection strategies** | Pi maneja system prompt loading nativamente. No necesitamos strategies. |
| **Auto-heal system**       | Pi no tiene versioning de prompts que migrar. No aplica.                |
| **Agent tier system**      | Solo tenemos 1 tier (Pi). No aplica.                                    |
| **MCP Context7 injection** | Ya tenemos skill `context7`. No necesitamos inyección custom.           |

---

## 8. Resumen para Refactor de AGENTS.md

Cambios concretos al archivo `~/.pi/agent/AGENTS.md`:

1. **Personality**: Cambiar "pragmatic engineer" → "passionate teacher who genuinely cares about craft"
2. **Language**: Añadir diccionario de voseo completo: "loco", "hermano", "locura cósmica", "ponete las pilas", "¿se entiende?"
3. **Tone**: Añadir "Caring, not arrogant" + anti-sarcasm rule + help-first default
4. **Orchestration**: Añadir Delegation Matrix (Inline vs Defer)
5. **Sub-agents**: Añadir Sub-agent Safety Protocol (role isolation, -nc flag, persistence enforcement)
6. **Persistence**: Formalizar Persistence Contract (write to disk before advancing)
7. **Size Classification**: Añadir decisión tree para cuando usar workflow vs direct

---

_Fuentes: `docs/research/gentle-ai/spec-{persona-injection,sdd-orchestrator,agent-adapters,skills-registry}.md`_
