---
name: Fork Terminal Skill
description: Bifurca una sesion de terminal a una nueva ventana de terminal. Usala cuando el ususario pida "fork terminal" o "crea una nueva terminal" o "nueva terminal: <command>".
---

# Purpose

Bifurca una sesion de terminal a una nueva ventana de terminal. Usando una herramienta agentica de codigo o un comando de cli crudo
Sigue las "Instructions" y el "Workflow", basado en el "Cookbook".

## Variables

ENABLE_RAW_CLI_COMMANDS: "true"
ENABLE_GEMINI_CLI: "true"
ENABLE_CODEX_CLI: "true"
ENABLE_CLAUDE_CODE: "true"

## Instructions

- Basado en las preferencias del usuario y el contexto, decide cual herramientas usar. Usa el cookbook para guiar tu decision.


## Workflow

1. Entiende las solicitudes del usuario.
2. Lee: "/workspaces/fork_agent/.claude/skills/fork_terminal/tools/fork_terminal.py" para entender la herramienta.
3. Sigue las instrucciones del "cookbook" para decidir cual herramienta usar.
4. Ejecuta la herramienta ".claude/skills/fork_terminal/tools/fork_terminal.py: fork_terminal(command: str)".

## Cookbook


### Raw CLI Commands

- If: Si el usuario pide una herramienta no-agentica de codigo AND "ENABLE_RAW_CLI_COMMANDS" es true.
- Then: Lee y ejecuta el "/fork_agent/.claude/skills/fork_terminal/cookbook/cli_command.md" archivo para determinar que codigo usar.
- Examples:
    -  "Crea una nueva temrinal a <xyz> con ffmpeg"
    - "Crea una nueva terminmal a <abc> con curl"
    - "Crea una nueva terminal a <xyz> con python"
