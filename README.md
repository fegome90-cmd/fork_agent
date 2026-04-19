# fork_agent

**fork_agent** es una plataforma agéntica avanzada diseñada para transformar y optimizar la interacción con tu terminal. Su capacidad central reside en la habilidad `fork_terminal`, que permite "bifurcar" (fork) tu sesión actual a nuevas ventanas o sesiones de terminal paralelas. Esta funcionalidad es esencial para ejecutar comandos de forma controlada y auditable, gestionar flujos de trabajo complejos, aislar tareas o ejecutar operaciones concurrentes sin interrumpir tu proceso principal.

`fork_terminal` actúa como un orquestador, eligiendo la estrategia de ejecución más adecuada para cada solicitud del usuario. Puede lanzar:
- **Comandos CLI Directos**: Para ejecuciones de shell estándar.
- **Agentes de Codificación (AI Models)**: Integrando modelos como Claude Code, Codex CLI y Gemini CLI. Estos agentes permiten la generación inteligente de comandos, la ejecución de scripts y la interacción contextual, utilizando el historial de conversación para generar prompts avanzados, especialmente cuando se solicita un "resumen" de la tarea.

Un "Cookbook" interno guía a `fork_agent` para seleccionar la herramienta idónea según la preferencia del usuario y el contexto, asegurando una ejecución eficiente y adaptada. El sistema promueve un entorno seguro y auditable, con recomendaciones clave para el uso de `--dry-run` o entornos aislados.

## Características Principales

- **Orquestación de Terminal**: Bifurca sesiones para gestionar tareas complejas y concurrentes.
- **Mensajería Inter-Agente (IPC)**: Sistema de comunicación estructurado y silencioso entre sesiones de tmux con persistencia en base de datos.
- **Soporte Multi-Agente Avanzado**:

  - **Raw CLI**: Ejecución directa de comandos de shell.
  - **Claude Code**: Para interacciones programáticas asistidas por IA.
  - **Codex CLI**: Generación y ejecución de código asistida.
  - **Gemini CLI**: Integración con el potente modelo Gemini para comandos inteligentes.
- **Contexto Conversacional**: Utiliza el historial del chat para enriquecer los prompts de los agentes, permitiendo resúmenes de trabajo y una ejecución más inteligente.
- **Workflow Disciplinado**: Sistema de comandos con gates obligatorios (outline → execute → verify → ship).
- **Hooks de Integración**: Eventos para tmux, memory traces y seguridad git.
- **Multi-Plataforma Robusta**:
  - **macOS**: Abre ventanas nativas de Terminal.
  - **Windows**: Inicia nuevas ventanas de CMD.
  - **Linux**: Prioriza emuladores de terminal comunes; si no los encuentra, crea sesiones de `tmux` desconectadas, ideal para entornos headless o remotos.

## Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <repository-url>
   cd fork_agent
   ```

2. **Configurar el entorno:**
   ```bash
   # Crear un entorno virtual
   python3 -m venv .venv
   source .venv/bin/activate

   # Instalar dependencias
   uv sync --all-extras
   ```

   *Nota: La herramienta principal usa librerías estándar de Python, pero los agentes específicos (como `gemini-cli` o `claude-code`) deben estar instalados y disponibles en tu PATH.*

## Uso - Comandos CLI

### Memoria

```bash
# Guardar observación
memory save "texto a recordar"

# Buscar observaciones
memory search "query"

# Listar todas
memory list

# Obtener por ID
memory get <id>

# Eliminar
memory delete <id>
```

### Workflow ( outline → execute → verify → ship )

```bash
# 1. Crear plan
memory workflow outline "Implementar autenticación"

# 2. Ejecutar plan
memory workflow execute

# 3. Verificar (ejecuta tests)
memory workflow verify

# 4. Shipping (requiere verify)
memory workflow ship

# Ver estado
memory workflow status
```

### Programación de Tareas

```bash
# Programar tarea
memory schedule add "echo hello" 60

# Listar tareas
memory schedule list

# Ver tarea
memory schedule show <task_id>

# Cancelar
memory schedule cancel <task_id>
```

### Workspace

```bash
# Crear workspace
memory workspace create my-workspace

# Listar workspaces
memory workspace list

# Entrar a workspace
memory workspace enter my-workspace

# Detectar workspace actual
memory workspace detect
```

### Mensajería Inter-Agente (IPC)

```bash
# Enviar mensaje directo a un agente (session:window)
fork message send agent1:1 "Tarea completada"

# Broadcast a todos los agentes activos
fork message broadcast "Status update: todos los sistemas OK"

# Ver historial de mensajes de un agente
fork message history agent1:1

# Limpieza de mensajes viejos
fork message cleanup --max-age 300
```


## MCP Server

fork_agent includes a built-in MCP (Model Context Protocol) server for AI agent integrations. It exposes memory operations as MCP tools accessible from Claude Desktop, Cursor, and any MCP-compatible client.

### Install

```bash
# pip (recommended)
pip install fork_agent

# uvx (one-off, no install)
uvx fork_agent

# uv tool (global)
uv tool install fork_agent
```

### Claude Desktop Configuration

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory-mcp"
    }
  }
}
```

### Available MCP Tools (17)

| Tool | Description |
|------|-------------|
| `memory_save` | Save observation with metadata |
| `memory_search` | FTS5 full-text search |
| `memory_retrieve` | Enhanced retrieval with pipeline v2 (dedup, ranking, bridges) |
| `memory_get` | Get by ID |
| `memory_list` | List with pagination |
| `memory_update` | Update existing observation |
| `memory_delete` | Delete observation |
| `memory_context` | Recent session summaries |
| `memory_stats` | Database statistics |
| `memory_session_start` | Start session |
| `memory_session_end` | End session |
| `memory_session_summary` | Save session summary |
| `memory_suggest_topic_key` | Suggest stable topic key |
| `memory_save_prompt` | Save user prompt |
| `memory_capture_passive` | Extract learnings from text |
| `memory_merge_projects` | Consolidate projects |
| `memory_timeline` | Observations in time range |

See [docs/mcp-setup.md](docs/mcp-setup.md) for full setup guide with all clients, custom DB path, and verification steps.

## Hooks de Integración

Sistema de eventos inspirado en claudikins-kernel para automatización:

| Hook | Evento | Descripción |
|------|--------|-------------|
| `workspace-init.sh` | SessionStart | Inicializa workspace |
| `tmux-session-per-agent.sh` | SubagentStart | Crea tmux session por agente |
| `memory-trace-writer.sh` | SubagentStop | Escribe trace a `.claude/traces/` |
| `git-branch-guard.sh` | PreToolUse | Bloquea git peligroso |

### Eventos Soportados

- **SessionStart**: Nueva sesión iniciada
- **SubagentStart**: Agente comienza
- **SubagentStop**: Agente termina
- **PreToolUse**: Antes de ejecutar tool
- **UserCommand**: Comando CLI ejecutado
- **FileWritten**: Archivo escrito

### Workflow Events

Eventos del workflow (outline → execute → verify → ship):

- **WorkflowOutlineStart**: Plan 开始
- **WorkflowOutlineComplete**: Plan 完成
- **WorkflowExecuteStart**: 执行开始
- **WorkflowExecuteComplete**: 执行完成
- **WorkflowVerifyStart**: 验证开始
- **WorkflowVerifyComplete**: 验证完成
- **WorkflowShipStart**: Shipping 开始
- **WorkflowShipComplete**: Shipping 完成

### Worktree Events

Eventos de ciclo de vida de worktrees:

- **WorktreeCreated**: Worktree creado
- **WorktreeMerged**: Worktree mergeado a branch
- **WorktreeRemoved**: Worktree eliminado


### Configuración

Los hooks se configuran en `.hooks/hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [{ "matcher": ".*", "hooks": [{"type": "command", "command": ".hooks/workspace-init.sh"}] }],
    "SubagentStart": [{ "matcher": ".*", "hooks": [{"type": "command", "command": ".hooks/tmux-session-per-agent.sh"}] }]
  }
}
```

### Seguridad Git

El hook `git-branch-guard.sh` implementa allowlist de comandos:

- ✅ **Permitidos**: add, commit, status, diff, log, show, blame, branch, fetch
- ❌ **Bloqueados**: checkout, switch, reset, clean, push, pull, rebase, merge, stash, cherry-pick

## Interfaces

### API REST (FastAPI)

```bash
# Iniciar servidor
uvicorn src.interfaces.api.main:app --host 127.0.0.1 --port 8080

# Endpoints principales
POST /api/v1/memory         # Crear observación
GET  /api/v1/memory/{id}     # Obtener por ID
GET  /api/v1/memory/search   # Buscar (full-text)
GET  /api/v1/memory/query    # Query con filtros
GET  /api/v1/system/health   # Health check
```

Auth: `X-API-Key` header (configurar via `API_KEY` env var).

### MCP Server (stdio/SSE/HTTP)

```bash
# stdio (Claude Desktop, Cursor)
memory-mcp

# SSE
memory-mcp --transport sse --port 8081

# 16 herramientas: memory_save, memory_search, memory_get, memory_list,
# memory_delete, memory_context, memory_update, memory_stats, memory_timeline,
# memory_session_start/end/summary, memory_retrieve, memory_suggest_topic_key,
# memory_save_prompt, memory_capture_passive, memory_merge_projects
```

### TUI (Textual)

```bash
memory tui              # Navegador interactivo
memory tui --db /path   # DB específica
```

Teclas: `s` buscar, `a` agregar, `S` stats, `d` detalle, `q` salir.

### Trifecta Context Engine (v2)

Context engine para sub-agentes con routing automático (21 features, 110 NL triggers).

```bash
trifecta ctx plan --task "search observations" --segment .   # Route to feature
trifecta ctx search -q "database" -s . -l 5                    # Search context
trifecta index -r .                                           # Rebuild index
```

## Estado del Proyecto

| Componente | Estado | Tests |
|-----------|--------|-------|
| Memory CLI | Completo | 1876 |
| API REST | Completo | 65 |
| MCP Server | Completo (16 tools) | - |
| TUI | Completo (5 screens) | - |
| Sync Pipeline | Completo | 49 |
| Trifecta v2 | Integrado (21 features) | - |
| CI | Verde (0 failures, 0 lint errors) | - |

## Uso - Programático

```python
from src.application.services.orchestration.hook_service import HookService
from src.application.services.orchestration.events import SessionStartEvent

# Cargar hooks y dispatch eventos
service = HookService()
service.dispatch(SessionStartEvent(session_id='mi-sesion'))
```

## Estructura del Proyecto

```
src/
├── domain/              # Entidades inmutables, Protocol (ports)
├── application/         # Services, Use Cases
│   ├── services/
│   │   ├── orchestration/  # Eventos, actions, specs, hook_service
│   │   └── workflow/       # Estado persistente
├── infrastructure/     # DB, DI, platform-specific
│   └── orchestration/  # RuleLoader, ShellActionRunner
└── interfaces/         # CLI (Typer)
    └── commands/      # save, search, list, workflow, schedule

.hooks/                 # Hook scripts
.claude/               # Estado (plan-state.json, traces/)
```

## Notas por Plataforma

- **Usuarios de Linux**: Asegúrense de tener `tmux` instalado (`sudo apt install tmux`). La herramienta crea sesiones desconectadas para evitar bloquear tu shell actual.
  - Listar sesiones activas: `tmux ls`
  - Conectarse a una sesión: `tmux attach -t <nombre_sesion>`

- Este repo esta hecho en base al desarrollador indydevdan y el crédito de toda esta idea es totalmente suyo.
