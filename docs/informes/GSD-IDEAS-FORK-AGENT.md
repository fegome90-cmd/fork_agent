# Ideas de GSD para fork_agent
## Enfoque: Conceptos, no productos

> Este documento identifica ideas concepto de GSD que podrían mejorar fork_agent.
> No es un copy-paste, sino una síntesis de patrones transferibles.

---

## 1. Context Fidelity (Preservar Decisiones del Usuario)

### El Concepto
GSD tiene un sistema explícito para preservar decisiones del usuario a través del workflow:

```
<context_fidelity>
## CRITICAL: User Decision Fidelity

1. **Locked Decisions** — Implementar EXACTAMENTE como el usuario decidió
2. **Deferred Ideas** — NO implementar ideas diferidas por el usuario
3. **Claude's Discretion** — Documentar decisiones tomadas por Claude
</context_fidelity>
```

### Estado Actual en fork_agent
- El workflow state guarda tareas y estado
- NO hay forma de marcar decisiones "locked" vs "deferred"
- Las decisiones del usuario se pierden entre fases

### Idea para fork_agent
Añadir un campo `decisions` al workflow state que diferencie:
- `locked`: El usuario decidió X, NO se puede cambiar
- `deferred`: El usuario dijo "después", NO incluir en plan actual
- `discretion`: Queda a criterio de Claude

```python
@dataclass
class UserDecision:
    key: str
    value: str
    status: Literal["locked", "deferred", "discretion"]
    rationale: str | None = None
```

---

## 2. Goal-Backward Planning (Planificación Inversa)

### El Concepto
En GSD, el planner no parte de "qué hacer" sino de "qué resultado quiero":
- Derivar "must-haves" desde el objetivo
- Identificar qué es necesario para lograr el resultado
- No es top-down, es goal-driven

### Estado Actual en fork_agent
- El workflow outline genera tareas desde cero
- No hay backwards chaining desde el objetivo

### Idea para fork_agent
Añadir fase de **goal analysis** al comando outline:
1. Definir resultado final esperado
2. Derivar requisitos mínimos (must-haves)
3. Identificar dependencias entre tareas
4. Generar plan desde el objetivo hacia atrás

Esto填补 la gap: `GAP-WF-002 State Validation` porque hace explícito el goal.

---

## 3. Verificación Sistemática (Agente gsd-verifier)

### El Concepto
GSD tiene un agente dedicado a verificar que el trabajo cumple specs:
- No es auto-verificación (el executor no se verifica a sí mismo)
- Usa evidencia objetiva
- Reporta gaps de forma estructurada

### Estado Actual en fork_agent
- El comando `verify` corre tests pero no valida contra specs explícitos
- No hay "evidence collection" estructurada

### Idea para fork_agent
Separar la verificación en dos pasos:
1. **Evidence collection** — Recopilar outputs, test results, logs
2. **Spec validation** — Comparar evidencia contra requirements

Esto填补: `GAP-WF-002 State Validation` + `GAP-WF-003 Phase Skip Prevention`

---

## 4. Meta-Prompting como Configuración

### El Concepto
GSD define agentes como prompts estructurados con frontmatter:
```yaml
---
name: gsd-planner
description: Creates executable phase plans...
tools: Read, Write, Bash, Glob, Grep
color: green
---
<role>...</role>
```

### Estado Actual en fork_agent
- Los agentes están hardcodeados en Python (AgentManager)
- Para añadir un agente, hay que editar código

### Idea para fork_agent
Crear un sistema de **agent definitions** como archivos de configuración:
- Agents definidos en JSON/YAML
- tools permitidas configurables
- Código Python solo ejecuta, no define comportamiento

Esto填补: `GAP-PT-001 Multi-Agent Platform Support`

---

## 5. Phase Research (Investigación de Contexto)

### El Concepto
GSD tiene fases de "research" antes de planificar:
- Investigar el codebase existente
- Investigar tecnologías/dependencies
- Documentar contexto antes de actuar

### Estado Actual en fork_agent
- El workflow tiene: outline → execute → verify → ship
- NO hay fase de investigación obligatoria

### Idea para fork_agent
Añadir fase **research** antes de outline:
- Auto-detectar stack tecnológico
- Analizar estructura del proyecto
- Identificar skills y conventions disponibles
- Generar contexto para el planner

Esto填补: `GAP-WF-001 State Schema Versioning` (context auto-discovery)

---

## 6. Context Rot Prevention

### El Concepto
GSD resuelve el "context rot" — degradación de calidad cuando el contexto se llena:
- Prompts estructurados con XML
- Información condensada
- Contexto relevante فقط

### Estado Actual en fork_agent
- Memoria es un SQLite con search FTS5
- NO hay sistema de resumen/compresión de contexto
- El contexto crece sin límite

### Idea para fork_agent
Implementar **context summarization**:
- Detect when context window is filling up
- Generate condensed summary of previous work
- Keep only actionable context for current phase

Esto es un **nuevo feature** no cubierto por gaps actuales.

---

## 7. Pattern: Commands as Prompts

### El Concepto
En GSD, los comandos (`/gsd:plan-phase`) son prompts que invocan agentes:
- No es CLI tradicional
- Es un prompt estructurado que pasa contexto al agente

### Estado Actual en fork_agent
- Comandos CLI en Typer
- Lógica de negocio en Use Cases
-分离

### Idea para fork_agent
Híbrido: mantener CLI pero permitir que commands pasen contexto enriquecido:
- El command pre-procesa el contexto
- Pasa información estructurada al agente
- No cambiar la arquitectura, cambiar el contenido

---

## Resumen de Mejoras Identificadas

| # | Idea | Gaps que填补 | Complejidad |
|---|------|-------------|-------------|
| 1 | User decisions tracking | GAP-WF-002 | Media |
| 2 | Goal-backward planning | GAP-WF-001, GAP-WF-002 | Alta |
| 3 | Separate verification agent | GAP-WF-002, GAP-WF-003 | Media |
| 4 | Agent definitions as config | GAP-PT-001 | Alta |
| 5 | Phase research | GAP-WF-001 | Media |
| 6 | Context summarization | (nuevo) | Alta |

---

## Recomendaciones Prioritarias

### Inmediato (1 sprint)
1. **User decisions tracking** — Bajo impacto, alta utilidad
2. **Goal analysis en outline** — Mejora calidad de planes

### Corto plazo (2 sprints)
3. **Evidence collection** — Mejora verification
4. **Phase research** — Mejora contexto

### Largo plazo
5. Agent definitions as config
6. Context summarization

---

*Documento generado: 2026-02-25*
*Inspiración: GSD (get-shit-done) + fork_agent codebase audit*
