# Alternativas en Kilo Code para funciones de superpowers

## Hallazgo Clave

Kilo Code usa **@command syntax** en lugar de `/slash commands`:

```markdown
# En vez de:
/brainstorm "mi idea"

# Kilo Code usa:
@brainstorm "mi idea"  <- Referencia a .claude/commands/brainstorm.md
```

## Funciones de superpowers → Alternativas en Kilo Code

### 1. Slash Commands → @Commands

| superpowers | Kilo Code | Archivo |
|-------------|-----------|---------|
| `/brainstorm` | `@brainstorm` | `.claude/commands/brainstorm.md` |
| `/write-plan` | `@write-plan` | `.claude/commands/write-plan.md` |
| `/execute-plan` | `@execute-plan` | `.claude/commands/execute-plan.md` |

**Archivos de comandos ya existentes:**
- `.claude/commands/all_skills.md`
- `.claude/commands/prime.md`

### 2. Hooks SessionStart → Inicialización Manual

**En superpowers:**
- Hook `session-start.sh` ejecuta automáticamente al iniciar sesión

**En Kilo Code:**
- No hay hook automático
- **Alternativa:** Crear script de inicialización que el usuario ejecuta manualmente

```bash
# Usuario ejecuta al iniciar sesión:
python3 .claude/hooks/session_start.py
```

### 3. Plugin System → Skills + Modes

**En superpowers:**
- Plugin `.claude-plugin/plugin.json`

**En Kilo Code:**
- Skills en `.kilocode/skills/` ✅ Ya migradas
- Modes en `.kilocodemodes/` ✅ Ya disponibles

### 4. Agents → Modes

| superpowers agent | Kilo Code equivalent |
|------------------|---------------------|
| `code-reviewer` | `code-reviewer` mode ya existe |
| Custom agents | Crear nuevos modes |

## Plan de Implementación de Alternativas

### @Commands (YA FUNCIONA)

Crear archivos en `.claude/commands/`:

```markdown
# .claude/commands/brainstorm.md
---
description: Invoca superpowers-brainstorming skill
---
Usa la skill @superpowers-brainstorming para esta tarea.
```

### Hooks de Sesión (Workaround)

**Opción A: Script manual**
```bash
# .claude/hooks/session_start.py
#!/usr/bin/env python3
print("Inyectando contexto de superpowers...")
```

**Opción B: Incluir en prompt del agent**
- Agregar contexto de superpowers en la configuración inicial

### Workflow de Usuario

```
1. Iniciar sesión
2. Ejecutar: python3 .claude/hooks/session_start.py  (opcional)
3. Usar: @brainstorm "idea" para invocar comandos
4. Las skills se activan automáticamente según el contexto
```

## Conclusión

| Función superpowers | Alternativa Kilo Code | Estado |
|--------------------|----------------------|--------|
| Slash Commands | @Commands | ✅ Implementable |
| SessionStart Hooks | Script manual | ⚠️ Workaround |
| Plugin System | Skills + Modes | ✅ Ya funciona |
| Agents | Modes | ✅ Ya existe |
