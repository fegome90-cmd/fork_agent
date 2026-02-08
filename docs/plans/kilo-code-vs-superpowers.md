# Kilo Code vs superpowers: Análisis Comparativo

## Basado en documentación oficial de kilo.ai

## Sistemas de Kilo Code

### 1. Custom Modes (`.kilocodemodes`)
✅ **Equivalente parcial a Agents de superpowers**

| Kilo Code | superpowers |
|-----------|-------------|
| Modes personalizados | Agents |
| slug, name, roleDefinition | name, description |
| groups (herramientas) | - |

### 2. Custom Rules (`.kilocode/rules/`)
❓ **Posible equivalente a Hooks?**

```
~/.kilocode/rules/          # Global
.kilocode/rules/           # Project
```

**Características:**
- Se carg- Aplican automáticamente
an a todas las interacciones
- markdown format

### 3. Custom Instructions (UI)
❓ **Posible equivalente a contexto inicial?**

## LO QUE NO EXISTE EN KILO CODE

| superpowers | Kilo Code |
|-------------|-----------|
| `/slash commands` | ❌ NO ENCONTRADO |
| `SessionStart hooks` | ❌ NO ENCONTRADO |
| `Workflows` | ❌ NO ENCONTRADO |
| `.claude-plugin/` | ❌ NO ENCONTRADO |

## Comparativa de Automatización

### superpowers
```
/brainstorm "idea"          → Automático
SessionStart hook           → Automático
```

### Kilo Code
```
Custom Rules               → Se cargan pero no se ejecutan
Custom Instructions        → UI-based, no automatización
```

## Conclusión

Kilo Code tiene **Custom Rules** que se cargan automáticamente, pero **NO tiene** automatización como:
- Slash commands automáticos
- Hooks de sesión
- Workflows

### Lo que SÍ podemos hacer:

1. **Custom Modes** → Adaptar agents de superpowers
2. **Custom Rules** → Crear reglas de superpowers
3. **Custom Instructions** → Inyectar contexto inicial

### Lo que NO podemos replicar:

1. `/slash commands`
2. SessionStart hooks
3. Workflows
