---
name: fork_terminal/tmux_orchestrator
description: Orquesta múltiples sesiones de OpenCode agents via tmux. Úsalo cuando necesites coordinar tareas entre múltiples agentes, lanzar subagentes, o monitorear progreso de sesiones activas.
---

# Tmux Orchestrator Skill

Permite orquestar múltiples agentes OpenCode en sesiones tmux separadas.

## Variables

DEFAULT_MODEL: opencode/glm-5-free
FAST_MODEL: opencode/minimax-m2.5-free
HEAVY_MODEL: opencode/trinity-large-preview-free
PROJECT_ROOT: /home/user/fork_agent

## Comandos Disponibles

### Crear Sesión de Agente

```bash
# Crear nueva sesión con agente
tmux new-session -d -s <session_name> -c /home/user/fork_agent
tmux send-keys -t <session_name> "opencode run -m <model> '<prompt>'" Enter
```

### Enviar Mensaje a Agente

```bash
# Usando el script helper
/home/user/fork_agent/.tmux-orchestrator/send-opencode-message.sh <session>:<window> "<message>"

# O directamente
tmux send-keys -t <session>:<window> "<message>"
sleep 0.5
tmux send-keys -t <session>:<window> Enter
```

### Ver Output de Agente

```bash
tmux capture-pane -t <session>:<window> -p | tail -50
```

### Listar Sesiones

```bash
tmux list-sessions
tmux list-windows -t <session>
```

### Matar Sesión

```bash
tmux kill-session -t <session_name>
```

## Python API

```python
from src.infrastructure.tmux_orchestrator import (
    TmuxOrchestrator,
    create_agent_session,
    send_task_to_agent,
    get_agent_output,
)

# Crear sesión con agente
session, window = create_agent_session(
    name="test_fixer",
    model="opencode/glm-5-free",
    prompt="Fix tests in tests/unit/infrastructure/",
)

# Enviar tarea
send_task_to_agent(session, window, "Continue fixing the remaining tests")

# Ver progreso
output = get_agent_output(session, window, lines=100)
```

## Patrones de Uso

### 1. Orquestador con Subagentes

```
TAREA: Crear orquestador que coordine 2 subagentes

PASOS:
1. Crear sesión orchestrator
2. Crear ventana para subagente 1 (fix_tests)
3. Crear ventana para subagente 2 (add_validation)
4. Monitorear progreso cada 5 minutos
5. Coordinar entregas en .stash/
```

### 2. Lanzar Agente con Handoff

```bash
# Crear handoff
cat << 'EOF' > /tmp/handoff.txt
HANDOFF CONTEXT
===============
[contenido del handoff]
EOF

# Lanzar agente
tmux new-session -d -s worker1
tmux send-keys -t worker1 "opencode run -m opencode/glm-5-free 'Read /tmp/handoff.txt and continue the task'" Enter
```

### 3. Monitoreo Continuo

```python
import time
from src.infrastructure.tmux_orchestrator import TmuxOrchestrator

orchestrator = TmuxOrchestrator()

while True:
    status = orchestrator.get_status()
    for session in status["sessions"]:
        print(f"Session: {session['name']}")
        for window in session["windows"]:
            output = orchestrator.capture_content(
                session["name"], window["index"], lines=20
            )
            if "COMPLETED" in output:
                print(f"  Window {window['index']}: COMPLETED")
            elif "ERROR" in output:
                print(f"  Window {window['index']}: ERROR")
    time.sleep(300)
```

## Workflow Recomendado

1. **Preparar handoff** en `/tmp/handoff_context.txt`
2. **Crear sesión** con nombre descriptivo
3. **Lanzar agente** con modelo apropiado
4. **Monitorear** cada 5-10 minutos
5. **Recoger resultados** de `.stash/`
6. **Matar sesión** cuando termine

## Ejemplos de Prompts para Subagentes

### Agente Quick Fix

```
TAREA: Fix tests en test_observation_repository.py líneas 652-750

PROBLEMA: Tests mockean __enter__ que es read-only

SOLUCIÓN: Usar FailingConnection subclass

ENTREGAR: .stash/fix_report.md
```

### Agente Deep Implementation

```
TAREA: Implementar MemoryService con TDD

ARCHIVOS:
- src/application/services/memory_service.py (crear)
- tests/unit/application/test_memory_service.py (crear)

REQUISITOS:
- Métodos: save_observation, search_observations, get_recent
- Usar ObservationRepository inyectado
- Coverage >= 95%

ENTREGAR: Tests pasando, código documentado
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| Sesión no responde | `tmux kill-session -t <name>` y recrear |
| Agente no recibe mensaje | Verificar window index correcto |
| Output vacío | Agente puede estar en modo interactivo, usar `capture-pane` |
| Modelo no disponible | Usar `opencode models` para ver disponibles |

## Integración con Modelos

Consulta `.claude/skills/fork_terminal/cookbook/modelos.md` para guía completa.

| Modelo | Uso | Cuándo |
|--------|-----|--------|
| OpenCode (glm-5-free) | Orquestación | Planning, coordinación |
| Claude Code (sonnet) | Plan y código | Writing, refactoring |
| Codex (GPT-5.3-Codex) | Deep work | Análisis profundo |
| Gemini Flash 2.5 | Fast task | Tareas rápidas |

## Integración con Context Memory

Al finalizar sesión, ejecutar en PARALELO:

```bash
# 1. Guardar handoff
/fork-checkpoint

# 2. Guardar contexto machine-readable
cm-save <nombre-sesion>
```

Esto permite:
- `/fork-resume` - Continuar desde último handoff
- `cm-load <nombre>` - Rehidratar contexto completo
