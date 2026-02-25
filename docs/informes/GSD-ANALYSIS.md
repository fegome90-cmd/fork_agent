# Análisis: get-shit-done (GSD)

**Repositorio:** https://github.com/gsd-build/get-shit-done  
**Stars:** 20,024+  
**Versión:** 1.21.0  
**Fecha de análisis:** 2026-02-25

---

## 1. Overview

**Get Shit Done (GSD)** es un sistema de **meta-prompting, context engineering y spec-driven development** para agentes AI como Claude Code, OpenCode, Gemini CLI y Codex.

Fue creado por **TÂCHES** para resolver el problema del "context rot" — la degradación de calidad que ocurre cuando Claude llena su ventana de contexto.

### Problema que resuelve

- **Vibecoding** tradicional produce código inconsistente que se desmorona a escala
- GSD proporciona la capa de ingeniería de contexto que hace a Claude Code confiable
- Enfocado en desarrolladores individuales, no en equipos enterprise

### Filosofía

> *"La complejidad está en el sistema, no en tu workflow."*

- Sin ceremonias enterprise (sprints, story points, syncs, retros)
- Enfoque en obtener resultados efectivos con mínima fricción

---

## 2. Arquitectura del Sistema

### 2.1 Componentes Principales

```
get-shit-done/
├── agents/              # Agentes especializados (meta-prompts)
├── commands/gsd/        # Comandos CLI (/gsd:*)
├── get-shit-done/       
│   ├── bin/            # Scripts de instalación
│   ├── references/     # Referencias de contexto
│   ├── templates/      # Plantillas para proyectos
│   └── workflows/      # Workflows predefinidos
├── hooks/              # Git hooks
├── scripts/            # Scripts de build
└── tests/             # Tests
```

### 2.2 Agentes Especializados (11 agentes)

| Agente | Descripción |
|--------|-------------|
| `gsd-planner` | Crea planes ejecutables con breakdown de tareas y análisis de dependencias |
| `gsd-executor` | Implementa planes generados por el planner |
| `gsd-verifier` | Verifica el trabajo completado contra specs |
| `gsd-debugger` | Debugging sistemático con enfoque científico |
| `gsd-phase-researcher` | Investigación de contexto para fases |
| `gsd-project-researcher` | Investigación de contexto a nivel proyecto |
| `gsd-codebase-mapper` | Mapeo de arquitectura y estructura del codebase |
| `gsd-plan-checker` | Valida planes antes de ejecución |
| `gsd-roadmapper` | Crea roadmap de alto nivel |
| `gsd-integration-checker` | Verifica integraciones |
| `gsd-research-synthesizer` | Sintetiza investigaciones |

### 2.3 Comandos CLI (30+ comandos)

```
/gsd:new-project    - Crear nuevo proyecto
/gsd:plan-phase    - Planificar fase
/gsd:execute-phase - Ejecutar fase
/gsd:verify-work   - Verificar trabajo
/gsd:debug         - Modo debug sistemático
/gsd:research-phase - Investigar contexto
/gsd:add-phase     - Añadir nueva fase
/gsd:new-milestone - Crear milestone
/gsd:map-codebase  - Mapear estructura
... (30+ más)
```

---

## 3. Tecnologías y Dependencias

### 3.1 Stack Técnico

| Tecnología | Uso |
|------------|-----|
| **Node.js** | Runtime (>=16.7.0) |
| **esbuild** | Bundling de hooks |
| **npm** | Package manager |

### 3.2 Dependencias

```json
{
  "devDependencies": {
    "esbuild": "^0.24.0"
  }
}
```

**Notable:** El paquete NO tiene dependencias de runtime — es extremadamente lightweight.

### 3.3 Plataformas Soportadas

- Claude Code
- OpenCode
- Gemini CLI
- Codex CLI

---

## 4. Patrones de Diseño

### 4.1 Meta-Prompting

Cada agente es un **prompt estructurado** con:
- Frontmatter YAML para metadatos (name, description, tools, color)
- Secciones XML (`<role>`, `<project_context>`, `<context_fidelity>`, etc.)
- Instrucciones específicas para cada tipo de tarea

### 4.2 Context Engineering

```
┌─────────────────────────────────────────┐
│           CONTEXT.md                     │
├─────────────────────────────────────────┤
│ • User decisions (locked/deferred)      │
│ • Project context                       │
│ • Skills del proyecto                   │
│ • Previous work state                   │
└─────────────────────────────────────────┘
```

### 4.3 Spec-Driven Development

1. **User describe** → Qué quiere construir
2. **GSD extract** → Extrae todo lo necesario
3. **Claude build** → Implementa con verificación continua
4. **GSD verify** → Verifica contra specs

### 4.4 Goal-Backward Planning

- Planificar desde el resultado deseado hacia atrás
- Derivar "must-haves" desde el objetivo final
- Análisis de dependencias entre tareas

---

## 5. Comparativa con fork_agent

| Aspecto | fork_agent | get-shit-done |
|---------|------------|---------------|
| **Arquitectura** | DDD (Python/Typer) | Meta-prompting (Node.js) |
| **Persistencia** | SQLite | Archivos locales |
| **Agentes** | AgentManager (Python) | Prompts markdown |
| **CLI** | Typer (Python) | Claude Code commands |
| **Testing** | pytest | node --test |
| **Scope** | Memoria + Orquestación | Spec-driven development |

### Similitudes

- Ambos resuelven problemas de contexto en agentes AI
- Orquestación de subagentes/tareas
- Sistema de hooks para automatización
- Enfoque en developer experience

### Diferencias Clave

- **GSD**: Enfoque en workflow de desarrollo (plan → execute → verify)
- **fork_agent**: Enfoque en memoria persistente y coordinación de agentes

---

## 6. Instalación y Uso

### Instalación

```bash
npx get-shit-done-cc@latest
```

El instalador pregunta:
1. **Runtime** — Claude Code, OpenCode, Gemini, Codex
2. **Location** — Global o local

### Verificación

- Claude Code / Gemini: `/gsd:help`
- OpenCode: `/gsd-help`
- Codex: `$gsd-help`

---

## 7.Insights para fork_agent

### 7.1 Patrones Adoptar

1. **Frontmatter en prompts** — Metadatos estructurados para agentes
2. **Context fidelity** — Preservar decisiones del usuario a través del workflow
3. **Goal-backward planning** — Planificar desde el resultado
4. **Verificación sistemática** — Agentes dedicados a verificar trabajo
5. **Phase-based workflow** — Dividir trabajo en fases ejecutables

### 7.2 Estructura de Agentes GSD

```markdown
---
name: gsd-planner
description: Creates executable phase plans...
tools: Read, Write, Bash, Glob, Grep, WebFetch, mcp__context7__*
color: green
---

<role>
You are a GSD planner...
</role>

<project_context>
Before planning, discover project context...
</project_context>

<context_fidelity>
## CRITICAL: User Decision Fidelity
...
</context_fidelity>

<philosophy>
## Solo Developer + Claude Workflow
...
</philosophy>
```

### 7.3 Estado Persistente

GSD usa `CLAUDE.md` (o `.claude.md`) para mantener contexto entre sesiones.

---

## 8. Conclusión

**get-shit-done** es un sistema elegante y efectivo para hacer que agentes AI construyan software de manera confiable. Su éxito (20k+ stars) se basa en:

1. **Simplicidad aparente** — El usuario ve few commands, no complejidad
2. **Profundidad interna** — Context engineering sofisticado debajo
3. **Enfoque en resultados** — Sin enterprise theater
4. **Multi-plataforma** — Soporta múltiples runtimes de AI

Para **fork_agent**, GSD ofrece patrones valiosos especialmente en:
- Diseño de agentes como prompts estructurados
- Workflow de verificación sistemática
- Preservación de contexto y decisiones de usuario

---

*Análisis generado el 2026-02-25*
