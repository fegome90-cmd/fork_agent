# Análisis de Integración: Componentes superpowers → Kilo Code

## Estructura de Kilo Code

| Componente | Ubicación | Propósito |
|------------|-----------|-----------|
| **Modes** | `.kilocodemodes` | Define roles/agentes personalizados |
| **Skills** | `.kilocode/skills/` | Skills con procedimientos y recursos |
| **CLI Tools** | `.claude/` | Scripts ejecutables |

## Mapping de Componentes superpowers

### 1. Agents (`agents/code-reviewer.md`)
**Opción A:** Convertir en **Mode** de Kilo Code
- Ubicación: `.kilocodemodes` (como `code-reviewer` ya existe)
- Diferencia: Kilo Code usa `roleDefinition`, superpowers usa prompts

**Opción B:** Mantener como **Skill**
- Ya está cubierto por `superpowers-requesting-code-review`

### 2. Hooks (`hooks/session-start.sh`)
**Kilo Code no tiene hooks de sesión equivalentes.**
- Kilo Code usa pre-commit hooks (`.pre-commit-config.yaml`)
- SessionStart hook de superpowers inyecta contexto al iniciar
- **Adaptación:** Crear script en `.claude/` que se ejecute manualmente o configurar hook

### 3. Lib (`lib/skills-core.js`)
**Funcionalidad**: Gestión de skills (parsear frontmatter, encontrar skills, resolver paths)
- **En Kilo Code**: Esta funcionalidad es nativa
- **No necesario migrar**: Kilo Code ya tiene su propia gestión de skills

### 4. Commands (`commands/*.md`)
**Opción:** Crear CLI tools en `.claude/`
- `brainstorm` → `.claude/brainstorm`
- `write-plan` → `.claude/write-plan`
- `execute-plan` → `.claude/execute-plan`

## Propuesta de Integración

### Componentes a Migrar

| Componente | Prioridad | Esfuerzo | Tipo |
|------------|-----------|----------|------|
| CLI Commands (brainstorm, write-plan, execute-plan) | Alta | Bajo | Script CLI |
| code-reviewer como Mode | Media | Medio | Mode definition |

### Componentes No Necessarios

| Componente | Razón |
|-----------|-------|
| Hooks | Kilo Code no tiene hooks de sesión equivalentes |
| Lib/skills-core.js | Funcionalidad nativa de Kilo Code |

## Próximos Pasos

1. [ ] Crear CLI commands en `.claude/` para brainstorm/write-plan/execute-plan
2. [ ] Evaluar si crear mode adicional de code-reviewer (ya existe `code-reviewer` mode)
3. [ ] Documentar uso de skills migradas
