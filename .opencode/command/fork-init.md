---
description: "Inicializa sesión fork_agent con tmux, memoria, hooks y workflow"
---

# Fork Init - Iniciar Sesión fork_agent

Inicializa una sesión completa de fork_agent ejecutando:
1. Hooks de SessionStart
2. Inicialización de workspace
3. Estado de workflow

## USO

```bash
/fork-init [descripcion-tarea]
```

## ACCIONES OBLIGATORIAS

### 1. Ejecutar Hook SessionStart

```bash
.hooks/workspace-init.sh
```

Esto crea:
- `.claude/traces/` directorio
- `.claude/context-memory-id` si no existe

### 2. Dispatch Evento SessionStart

```python
from src.application.services.orchestration.hook_service import HookService
from src.application.services.orchestration.events import SessionStartEvent

service = HookService()
service.dispatch(SessionStartEvent(session_id="nueva-sesion"))
```

### 3. Limpiar Estado Anterior (si existe)

```bash
rm -f .claude/plan-state.json
rm -f .claude/execute-state.json  
rm -f .claude/verify-state.json
rm -f .claude/traces/current-trace.json
```

### 4. Iniciar Workflow (si hay descripción)

Si el usuario proporcionó una descripción de tarea:

```bash
memory workflow outline "[descripcion-tarea]"
```

## OUTPUT ESPERADO

```
✅ Sesión fork_agent inicializada

Hooks ejecutados:
  - SessionStart → workspace-init.sh

Estado:
  - Workspace: [workspace-name]
  - Traces dir: .claude/traces/

Workflow:
  - Estado: listo para outline
  - Comando: memory workflow outline "[descripcion]"

Próximos pasos:
  1. memory workflow outline "[tarea]"
  2. memory workflow execute
  3. memory workflow verify
  4. memory workflow ship
```

## VERIFICACIÓN

Después de inicializar, verificar:

```bash
# Ver estado
memory workflow status

# Ver traces
ls -la .claude/traces/

# Ver workspace
cat .claude/context-memory-id
```

## EJEMPLO

```
> /fork-init Implementar autenticación OAuth

✅ Sesión fork_agent inicializada

Hooks ejecutados:
  - SessionStart → workspace-init.sh

Estado:
  - Workspace: tmux_fork
  - Traces dir: .claude/traces/

Workflow:
  - Plan creado: plan-[id]
  - Archivo: .claude/plans/plan.md

Próximos pasos:
  1. memory workflow execute
  2. memory workflow verify
  3. memory workflow ship
```

## INTEGRACIÓN CON TMUX

Para sesiones con agentes aislados, después de execute:

```bash
# Crear sesión tmux por agente
AGENT_NAME="babyclaude-1" .hooks/tmux-session-per-agent.sh

# Output:
# {
#   "sessionName": "fork-babyclaude-1-1771800114",
#   "attachCommand": "tmux attach -t fork-babyclaude-1-1771800114"
# }
```

## ARCHIVOS CLAVE

| Archivo | Propósito |
|---------|-----------|
| `.hooks/workspace-init.sh` | Hook de inicialización |
| `.claude/context-memory-id` | ID del workspace |
| `.claude/traces/` | Directorio de traces |
| `.claude/plan-state.json` | Estado del plan |
| `.hooks/hooks.json` | Configuración de hooks |

## FLAGS OPCIONALES

| Flag | Descripción |
|------|-------------|
| `--no-hooks` | Skip hooks de SessionStart |
| `--clean` | Limpiar todo estado anterior |
| `--tmux` | Crear sesión tmux inmediatamente |
