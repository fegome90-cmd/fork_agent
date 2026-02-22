# OpenCode Agent Configuration for fork_terminal

## Modelos Gratuitos Disponibles

| Modelo | Uso | Características |
|--------|-----|-----------------|
| `opencode/glm-5-free` | Principal | Calidad alta, razonamiento complejo |
| `opencode/minimax-m2.5-free` | Rápido | Exploración, búsqueda, tareas simples |
| `opencode/minimax-m2.5-free` | Alternativo | Buen balance calidad/velocidad |
| `opencode/trinity-large-preview-free` | Pesado | Tareas que requieren más capacidad |

## Agentes y Asignación de Modelos

### Agentes de Orquestación (Sisyphus)

| Agente | Modelo Asignado | Propósito |
|--------|-----------------|-----------|
| `explore` | `opencode/minimax-m2.5-free` | Búsqueda contextual rápida en codebase |
| `librarian` | `opencode/minimax-m2.5-free` | Búsqueda de documentación externa |
| `oracle` | `opencode/glm-5-free` | Consultas de arquitectura y debugging |
| `metis` | `opencode/glm-5-free` | Pre-planning y análisis de ambigüedades |
| `momus` | `opencode/glm-5-free` | Revisión de calidad y completitud |

### Categorías de Tareas

| Categoría | Modelo | Descripción |
|-----------|--------|-------------|
| `quick` | `opencode/minimax-m2.5-free` | Tareas triviales, cambios simples |
| `visual-engineering` | `opencode/glm-5-free` | Frontend, UI/UX, diseño |
| `deep` | `opencode/glm-5-free` | Problemas complejos que requieren investigación |
| `ultrabrain` | `opencode/trinity-large-preview-free` | Lógica pesada, razonamiento profundo |
| `artistry` | `opencode/glm-5-free` | Soluciones creativas no convencionales |
| `writing` | `opencode/minimax-m2.5-free` | Documentación, prosa técnica |
| `unspecified-low` | `opencode/minimax-m2.5-free` | Tareas simples sin categoría |
| `unspecified-high` | `opencode/glm-5-free` | Tareas complejas sin categoría |

## Variables de Configuración

```yaml
ENABLE_OPENCODE_CLI: "true"
ENABLE_RAW_CLI_COMMANDS: "true"
ENABLE_GEMINI_CLI: "false"
ENABLE_CODEX_CLI: "false"
ENABLE_CLAUDE_CODE: "false"

DEFAULT_MODEL: opencode/glm-5-free
FAST_MODEL: opencode/minimax-m2.5-free
HEAVY_MODEL: opencode/trinity-large-preview-free
```

## Comandos OpenCode

### Ejecución Básica

```bash
# Ejecutar con modelo por defecto (glm-5-free)
opencode run "tu prompt aquí"

# Ejecutar con modelo rápido (minimax-m2.5-free)
opencode run -m opencode/minimax-m2.5-free "tu prompt aquí"

# Ejecutar con modelo pesado (trinity)
opencode run -m opencode/trinity-large-preview-free "tu prompt aquí"
```

### Continuar Sesión

```bash
# Continuar última sesión
opencode run -c "continuar con..."

# Fork de sesión existente
opencode run --fork -s <session_id> "nueva tarea"
```

### Modo Interactivo

```bash
# Iniciar TUI
opencode

# Iniciar con modelo específico
opencode -m opencode/glm-5-free
```

## Workflow para Fork Terminal

1. **Generar historial** en formato YAML
2. **Escribir** en `/tmp/handoff_context.txt`
3. **Ejecutar** `opencode run -m <model> "prompt"`

### Ejemplo de Handoff

```bash
# Crear archivo de contexto
cat << 'EOF' > /tmp/handoff_context.txt
HANDOFF CONTEXT
===============
[contenido del handoff]
EOF

# Lanzar nuevo agente
opencode run -m opencode/glm-5-free "Read /tmp/handoff_context.txt and continue."
```

## Integración con task()

Cuando uses `task()` para delegar:

```python
# Agente rápido (gemini flash)
task(subagent_type="explore", run_in_background=true, prompt="Find patterns...")

# Agente de calidad (glm-5)
task(subagent_type="oracle", run_in_background=true, prompt="Review architecture...")

# Categoría rápida
task(category="quick", load_skills=[], prompt="Simple fix...")

# Categoría profunda
task(category="deep", load_skills=["git-master"], prompt="Complex investigation...")
```
