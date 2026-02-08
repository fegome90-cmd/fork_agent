# Workflows: La alternativa a Slash Commands en Kilo Code

## Hallazgo Clave

Kilo Code tiene **Workflows** que funcionan igual que los `/commands` de superpowers:

```markdown
# superpowers:
/brainstorm "mi idea"

# Kilo Code:
/brainstorm.md  # Invoca .kilocode/workflows/brainstorm.md
```

## Ubicación de Workflows

```
.kilocode/workflows/          # Project-specific
~/.kilocode/workflows/        # Global (todos los proyectos)
```

## Implementación para superpowers

### Workflows a crear:

| superpowers command | Kilo Code workflow | Archivo |
|--------------------|-------------------|---------|
| `/brainstorm` | `/brainstorm.md` | `.kilocode/workflows/brainstorm.md` |
| `/write-plan` | `/write-plan.md` | `.kilocode/workflows/write-plan.md` |
| `/execute-plan` | `/execute-plan.md` | `.kilocode/workflows/execute-plan.md` |

### Ejemplo: brainstorm.md

```markdown
# Brainstorm Workflow

You are using the superpowers-brainstorming skill.

1. First, understand the user's idea by asking clarifying questions
2. Explore 2-3 different approaches with trade-offs
3. Present the design in sections (200-300 words each)
4. Validate each section with the user
5. Write the design document to `docs/plans/YYYY-MM-DD-<topic>-design.md`

Ask the user: What would you like to brainstorm today?
```

## Hooks de Sesión

**Pregunta abierta:** ¿Kilo Code tiene equivalente a SessionStart hooks?

Según la documentación de workflows, no hay mención de hooks de sesión automáticos.

**Posible solución:**
- Incluir contexto de superpowers en un workflow de inicialización `/init.md`
- El usuario ejecuta `/init.md` al comenzar sesión

## Plan de Implementación

1. [ ] Crear `.kilocode/workflows/brainstorm.md`
2. [ ] Crear `.kilocode/workflows/write-plan.md`
3. [ ] Crear `.kilocode/workflows/execute-plan.md`
4. [ ] Crear `.kilocode/workflows/init.md` (contexto superpowers)
