# Plan de Integración Completa: superpowers → Kilo Code

## Visión General

Crear un sistema en Kilo Code que replique el funcionamiento completo de superpowers:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kilo Code + Superpowers                       │
├─────────────────────────────────────────────────────────────────┤
│  Modes (agentes)    → .kilocodemodes/                          │
│  Skills             → .kilocode/skills/superpowers-*/           │
│  Hooks (sesión)     → .claude/hooks/session_start.py           │
│  CLI Commands       → .claude/commands/                         │
│  Lib Utils          → src/infrastructure/superpowers/            │
└─────────────────────────────────────────────────────────────────┘
```

## Componentes a Implementar

### 1. Hooks System (Simular SessionStart hook)

**Archivo:** `.claude/hooks/session_start.py`

```python
#!/usr/bin/env python3
"""
SessionStart hook para Kilo Code.
Inyecta contexto de superpowers:using-superpowers al iniciar sesión.
"""

def get_session_start_context():
    """Retorna el contexto a inyectar al iniciar sesión."""
    return """
<EXTREMELY_IMPORTANT>
You have superpowers.

**Below is the full content of your 'superpowers:using-superpowers' skill - your introduction to using skills:**

[SKILL_CONTENT]

</EXTREMELY_IMPORTANT>
"""
```

### 2. Agents como Modes

**Archivo:** `.kilocodemodes/superpowers-code-reviewer`

```yaml
customModes:
  - slug: superpowers-code-reviewer
    name: Superpowers Code Reviewer
    roleDefinition: |
      You are a Senior Code Reviewer based on superpowers methodology...
    groups:
      - read
      - browser
    customInstructions: |
      [Contenido del agent code-reviewer.md adaptado]
```

### 3. Skills (YA MIGRADAS)

Ubicación: `.kilocode/skills/superpowers-*/`

14 skills ya migradas:
- [x] brainstorming
- [x] writing-plans
- [x] executing-plans
- [x] subagent-driven-development
- [x] test-driven-development
- [x] systematic-debugging
- [x] verification-before-completion
- [x] requesting-code-review
- [x] receiving-code-review
- [x] using-git-worktrees
- [x] finishing-a-development-branch
- [x] dispatching-parallel-agents
- [x] using-superpowers
- [x] writing-skills

### 4. CLI Commands

**Directorio:** `.claude/commands/`

Archivos a crear:
- `.claude/commands/brainstorm` → Invoca superpowers-brainstorming
- `.claude/commands/write-plan` → Invoca superpowers-writing-plans
- `.claude/commands/execute-plan` → Invoca superpowers-executing-plans

### 5. Lib Utilities (Skills Core)

**Directorio:** `src/infrastructure/superpowers/`

Módulos a crear:
- `skills_core.py` → Utilidades para gestión de skills
- `agents.py` → Funciones para agentes
- `hooks.py` → Sistema de hooks

## Arquitectura de Integración

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Hooks      │───►│    Skills    │───►│    Modes     │
│ session_start│    │  superpowers  │    │ code-reviewer│
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  CLI Tools   │    │   Lib Utils  │
│  commands/   │    │ skills_core.py│
└──────────────┘    └──────────────┘
```

## Plan de Implementación

### Fase 1: Infrastructure (Lib Utils)
- [ ] Crear `src/infrastructure/superpowers/__init__.py`
- [ ] Implementar `skills_core.py` (parsear frontmatter, encontrar skills)
- [ ] Implementar `hooks.py` (sistema de hooks)

### Fase 2: Hooks Integration
- [ ] Crear `.claude/hooks/session_start.py`
- [ ] Configurar integración con Kilo Code

### Fase 3: Modes (Agents)
- [ ] Crear mode `superpowers-code-reviewer`
- [ ] Adaptar contenido de `agents/code-reviewer.md`

### Fase 4: CLI Commands
- [ ] Crear `.claude/commands/brainstorm`
- [ ] Crear `.claude/commands/write-plan`
- [ ] Crear `.claude/commands/execute-plan`

### Fase 5: Testing
- [ ] Verificar que todas las skills funcionan
- [ ] Testear hooks de sesión
- [ ] Probar CLI commands

## Referencias del Repo Original

- Hooks: `.tmp/superpowers/hooks/session-start.sh`
- Agents: `.tmp/superpowers/agents/code-reviewer.md`
- Skills: `.tmp/superpowers/skills/*/SKILL.md`
- Lib: `.tmp/superpowers/lib/skills-core.js`
- Commands: `.tmp/superpowers/commands/*.md`
