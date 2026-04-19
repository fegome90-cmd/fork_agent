"""Template Renderer for Trifecta files."""

from src.domain.models import TrifectaConfig


class TemplateRenderer:
    """Renders Trifecta templates."""

    def render_skill(self, config: TrifectaConfig) -> str:
        return f"""---
name: {config.segment}
description: Use when working on {config.scope}
---

# {config.segment.replace("-", " ").title()}

## Overview
{config.scope}

## When to Use
Working on `{config.repo_root}/{config.segment}/`

## Core Pattern

### Session Evidence Persistence (5 Steps)

1) **Persist intention** (CLI proactive):
```bash
trifecta session append --segment . --summary "<action>" --files "<csv>" --commands "<csv>"
```

2) **Sync context**:
```bash
trifecta ctx sync --segment .
```

3) **Read** session.md (confirm objective logged)

4) **Execute** context cycle:
```bash
trifecta ctx search --segment . --query "<topic>" --limit 6
trifecta ctx get --segment . --ids "<id1>,<id2>" --mode excerpt --budget-token-est 900
```

5) **Log result**:
```bash
trifecta session append --segment . --summary "Completed <task>" --files "<touched>" --commands "<executed>"
```

### Mandatory Validation Protocol (Law V)

**STALE FAIL-CLOSED**: If `ctx validate` fails or `stale_detected=true`:
- **STOP** immediately. Do NOT guess.
- Run: `trifecta ctx sync --segment .` + `trifecta ctx validate --segment .`
- Continue ONLY if state is **VALID**.
- **Evidence**: All mutations MUST be followed by a verification command.

## Common Mistakes
- Skipping session logging (Law I violation)
- Writing before reading (Law II violation)
- Continuing with stale pack (Law VI violation)
- Model-specific bias in naming (Law VII violation)

## Resources (On-Demand)
- `@_ctx/prime_{config.segment}.md` - Reading list
- `@_ctx/agent_{config.segment}.md` - Tech stack & gates
- `@_ctx/session_{config.segment}.md` - Session log

---
**Profile**: `{config.default_profile}` | **Updated**: {config.last_verified}
"""

    def render_prime(self, config: TrifectaConfig, docs: list[str]) -> str:
        # Format docs with priority indicators
        formatted_docs = ""
        if docs:
            for i, doc in enumerate(docs):
                formatted_docs += f"{i + 1}. `{doc}`\n"
        else:
            formatted_docs = "<!-- Agregar documentos obligatorios -->"

        return f"""---
segment: {config.segment}
profile: load_only
---

# Prime {config.segment.replace("-", " ").title()} - Lista de Lectura

> **SEGMENT_ROOT**: `.` (all paths relative to segment root)
>
> **Orden de lectura**: Fundamentos -> Implementacion -> Referencias

## [HIGH] Prioridad ALTA - Fundamentos

**Leer primero para entender el contexto del segmento.**

{formatted_docs}

## [MED] Prioridad MEDIA - Implementacion

<!-- Documentacion de implementacion especifica -->

## [LOW] Prioridad BAJA - Referencias

<!-- Documentacion de referencia, archivada -->

## [MAP] Mapa Mental

```mermaid
mindmap
  root({config.segment})
    Fundamentos
    Arquitectura
    Interfaces
```

## [DICT] Glosario

| Termino | Definicion |
|---------|------------|
| <!-- Terminos clave --> | <!-- Definiciones --> |

## [NOTE] Notas

- **Fecha ultima actualizacion**: {config.last_verified}
- **Ver tambien**: [skill.md](skill.md) | [AGENTS.md](AGENTS.md)
"""

    def render_agent(self, config: TrifectaConfig) -> str:
        return f"""---
segment: {config.segment}
scope: {config.scope}
repo_root: {config.repo_root}
last_verified: {config.last_verified}
default_profile: {config.default_profile}
---

# Agent Context - {config.segment.replace("-", " ").title()}

## Source of Truth
| Seccion | Fuente |
|---------|--------|
| LLM Roles | [skill.md](../skill.md) |
| Governance | [AGENTS.md](../AGENTS.md) |

## Tech Stack
**Lenguajes:**
- <!-- Ej: Python 3.12+, TypeScript 5.x -->

**Frameworks:**
- <!-- Ej: FastAPI, Pydantic v2 -->

**Herramientas:**
- <!-- Ej: pytest, ruff, uv -->

## Gates (Comandos de Verificacion)

**Unit Tests:**
```bash
pytest tests/unit/ -v
```

**Linting:**
```bash
ruff check .
```

**Type Checking:**
```bash
mypy src/
```

## Resilience Boundaries
- **Message Cap**: 5,000 messages (Circular Buffer)
- **Disk Safety**: 60s TTL for ephemeral handoffs in `.ai/traces/`
"""

    def render_session(self, config: TrifectaConfig) -> str:
        return f"""# session.md - Trifecta Context Runbook

segment: {config.segment}

## Purpose
This file is a **runbook** for using Trifecta Context tools following the **Agentic Constitution v1.1**.

## Quick Commands (CLI)
```bash
SEGMENT="."

# [Law II] Reading before writing
trifecta ctx sync --segment "$SEGMENT"
trifecta ctx search --segment "$SEGMENT" --query "<query>" --limit 6
trifecta ctx get --segment "$SEGMENT" --ids "<id1>" --mode excerpt

# [Law V] Verification
trifecta ctx validate --segment "$SEGMENT"

# Advanced Discovery (AST)
trifecta ast build --repo .
```

## Rules (must follow)
* Max **1 ctx.search + 1 ctx.get** per user turn.
* Cite evidence using **[chunk_id]** (Law IV & XI).
* **FAIL-CLOSED**: If validate fails, STOP.

## Session Log (append-only)

### Entry Template (Law I & XI)
```md
## YYYY-MM-DD HH:MM - ctx cycle
- Segment: .
- Objective: <Law I: Intencion explicita>
- Plan: ctx sync -> ctx search -> ctx get
- Evidence: <Law IV: Evidencia obligatoria>
- Next: <1 concrete step>
```
"""

    def render_readme(self, config: TrifectaConfig) -> str:
        return f"""# {config.segment.replace("-", " ").title()} - Trifecta Documentation

> **Trifecta F1 Engine**: Repositorio blindado bajo la **Constitucion de Codigo Agentico v1.1**.

## [FILE] Estructura Neutral (Ley VII)

```
{config.segment}/
|-- AGENTS.md                    # Constitucion y Gobernanza (Vinculante)
|-- skill.md                     # Reglas y contratos (Protocolo Fail-Closed)
|-- .ai/                         # [Neutral] Infraestructura agentica
|   |-- commands/                # Comandos personalizados
|   |-- hooks/                   # Automatizacion event-driven
|   |-- plans/                   # Planes de ejecucion
|   |__ traces/                  # Evidencia y logs de sesion
|__ _ctx/                        # Context resources (PCC)
```

## [CLEAN] Repository Hygiene (Mandatory)

Para mantener el motor de Trifecta calibrado, el repositorio MUST estar limpio.

```bash
# Purga de worktrees redundantes
git worktree remove --force <path>
git worktree prune

# Limpieza de archivos huerfanos
find . -name "*.inactive" -delete
```

## [GO] Flujo de Onboarding

1. **Leer `AGENTS.md`** - Entender las 13 Leyes.
2. **Leer `skill.md`** - Activar el protocolo de validacion.
3. **Leer `_ctx/prime_{config.segment}.md`** - Cargar lista de lectura.

> [!IMPORTANT]
> **Toda mutacion sin plan previo es una violacion de la Ley I.**
"""

    def render_agents_md(self, config: TrifectaConfig) -> str:
        return f"""# {config.segment.replace("-", " ").title()} - AGENTS.md

> **Generated**: {config.last_verified} | **Governance**: Constitucion AI v1.1

## 🏛️ Gobernanza Agéntica

Este repositorio opera bajo la **Constitucion de Codigo Agentico v1.1**.
Source of Truth: `https://github.com/fegome90-cmd/constitucion-ai`

### Las 13 Leyes (Destiladas)

1. **Cambio Legitimo**: Intencion -> Plan -> Validacion -> Evidencia.
2. **Lectura Previa**: Prohibido escribir sin haber leido el contexto relevante.
3. **Arquitectura Base**: Respetar el Scope y la jerarquia del sistema.
4. **Control de Versiones**: Aislamiento total en ramas y worktrees.
5. **Verificabilidad**: Ningun cambio es real sin evidencia de ejecucion.
6. **Fuente de Verdad**: Sincronizacion obligatoria ante cualquier duda.
7. **Primacia del Sistema**: Neutralidad absoluta. Usar directorio `.ai/`.
8. **Seguridad**: Proteccion de secretos y limites de permisos.
9. **Persistencia**: Estado trazable y recuperable.
10. **Interfaces**: Respetar contratos y compatibilidad.
11. **Observabilidad**: Registro mandatorio de acciones en `_ctx/session`.
12. **Roles**: Actuar dentro de las capacidades de la Skill.
13. **Primacia Conceptual**: Priorizar el entendimiento semantico.

## 🛠️ Procedimiento de Checkpoint

Al finalizar cada tarea, el agente MUST:
1. Generar evidencia de validacion (logs/tests).
2. Actualizar el log de sesion en `_ctx/session_{config.segment}.md`.
3. Guardar un handoff en `.ai/traces/` si el trabajo continua.

---
**Neutralidad**: Este repositorio no tiene preferencia por modelos especificos.
"""

    def render_ai_settings(self) -> str:
        return """{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".ai/hooks/session-end-hook.sh"
          }
        ]
      }
    ]
  }
}
"""
