---
name: Fork Terminal Skill
description: Bifurca una sesion de terminal a una nueva ventana de terminal. Usala cuando el ususario pida "fork terminal" o "crea una nueva terminal" o "nueva terminal: <command>".
---

# Purpose

Bifurca una sesion de terminal a una nueva ventana de terminal. Usando una herramienta agentica de codigo o un comando de cli crudo
Sigue las "Instructions" y el "Workflow", basado en el "Cookbook"
El usuario utiliza fish como command line shell.

## Variables

ENABLE_RAW_CLI_COMMANDS: "true"
ENABLE_GEMINI_CLI: "true"
ENABLE_CODEX_CLI: "true"
ENABLE_CLAUDE_CODE: "true"
AGENTIC_CODING_TOOLS = HERRAMIENTAS_AGENTICAS_DE_CODIGO
AGENTIG_CODING_TOOLS: ["gemini-cli", "codex-cli", "claude-code"]

## Instructions

### CRITICAL PROTOCOL: History Persistence

Antes de ejecutar cualquier herramienta de "fork" (Gemini, Claude, Codex, CLI), DEBES seguir este estricto orden de operaciones. NO tomes atajos.

1. **GENERA** el historial y resumen de la conversación en formato YAML.
2. **ESCRIBE** (usando `write_file`) este contenido en: `/workspaces/fork_agent/.claude/skills/fork_terminal/prompts/fork_summary_user_prompts.md`.
   - _Nota:_ Este paso es obligatorio para auditoría y depuración. NO pases el contexto solo como argumento de string sin antes escribir este archivo.
3. **LEE** el contenido que acabas de preparar (o úsalo de tu memoria).
4. **EJECUTA** la herramienta `fork_terminal` pasando ese contenido como el prompt/instrucción inicial para el agente.

### Fork Summary User Prompts

- El archivo `/workspaces/fork_agent/.claude/skills/fork_terminal/prompts/fork_summary_user_prompts.md` actúa como la memoria compartida entre el agente actual y el agente bifurcado.
- DEBE ser actualizado en cada solicitud de fork.

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
  - "Crea una nueva temrinal a <xyz> con ffmpeg"
  - "Crea una nueva terminmal a <abc> con curl"
  - "Crea una nueva terminal a <xyz> con python"

### Claude Code

- If: Si el usuario solicita un agente de Claude code para ejecutar el comando AND "ENABLE_CLAUDE_CODE" es true.
- Then: Lee y ejecuta el "/fork_agent/.claude/skills/fork_terminal/cookbook/claude_code.md" archivo para determinar que codigo usar.
- Examples:
  - "Fork terminal a <xyz> con Claude Code"
  - "Abre una nueva terminal con claude code a <abc> con curl"
  - "Crea una nueva terminal a <xyz> con python"

### Codex CLI

- If: Si el usuario solicita usar un flujo tipo Codex (generación de código asistida) AND "ENABLE_CODEX_CLI" es true.
- Then: Lee y ejecuta el "/fork_agent/.claude/skills/fork_terminal/cookbook/codex_cli.md" archivo para determinar que codigo usar.
- Examples:
  - "Fork terminal a <xyz> usando Codex CLI"
  - "Genera y abre una terminal con codex-cli para ejecutar <abc>"
  - "Crea una nueva terminal y ejecuta el script generado por Codex"

### Gemini CLI

- If: Si el usuario solicita usar Gemini/agent CLI AND "ENABLE_GEMINI_CLI" es true.
- Then: Lee y ejecuta el "/fork_agent/.claude/skills/fork_terminal/cookbook/gemini_cli.md" archivo para determinar que codigo usar.
- Examples:
  - "Fork terminal a <xyz> usando Gemini CLI"
  - "Abre una nueva terminal con gemini-cli para correr <abc>"
  - "Crea una nueva terminal y ejecuta el flujo de Gemini para <xyz>"

