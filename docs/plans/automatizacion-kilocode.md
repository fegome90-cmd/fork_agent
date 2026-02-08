# Automatización en Kilo Code: Opciones y Limitaciones

## Conclusión: NO es una limitación del sistema, es un tradeoff de diseño

Kilo Code **sí soporta automatización**, pero de forma diferente a Claude Code.

## Formas de Automatización en Kilo Code

### 1. Scripts Python (YA EXISTE)

```bash
python3 .claude/skills/fork_terminal/tools/fork_terminal.py [comando]
```

**Ventajas:**
- ✅ Total control
- ✅ Cualquier funcionalidad

**Desventajas:**
- ❌ Requiere invocación manual
- ❌ No es automático

### 2. @Commands (YA EXISTE)

```markdown
@prime  # Lee contexto y reporta
@all_skills  # Lista skills
```

**Cómo funcionan:**
- Kilo Code lee archivos `.claude/commands/*.md`
- Cuando usas `@nombre`, ejecuta el contenido

### 3. MCP Servers (PLANIFICADO)

Según `docs/investigacion/diff.md`:
> "Definir MCP interno para exponer herramientas"

**Esto permitiría:**
- Herramientas automatizadas como en Claude Code
- Coordinación multi-agente
- Storage filesystem

### 4. Modes (YA EXISTE)

Definir roles personalizados en `.kilocodemodes/`

## Comparación con superpowers/Claude Code

| Feature | Claude Code | Kilo Code |
|---------|-------------|-----------|
| Slash Commands | `/cmd` automático | @cmd manual |
| Hooks | SessionStart automático | Script manual |
| MCP Servers | Nativo | Planificado |
| Modes/Agents | Limitado | Nativo |

## Solución: Automatización mediante Wrapper Script

Crear un wrapper que automatice la experiencia:

```bash
# kilo-code-wrapper.sh
#!/bin/bash
echo "Inyectando contexto superpowers..."

# Iniciar Kilo Code con contexto
kilo-code --prompt "$(cat .claude/prompts/superpowers_context.md)"
```

## Recomendación

Para replicar superpowers en Kilo Code:

1. **@Commands** para invocar skills (inmediato)
2. **Script de inicialización** para contexto (manual)
3. **MCP Server propio** para herramientas avanzadas (requiere desarrollo)
