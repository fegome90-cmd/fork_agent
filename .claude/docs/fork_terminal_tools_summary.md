# Resumen de Herramientas de Fork Terminal

Este documento resume las herramientas disponibles para bifurcar sesiones de terminal, según se describe en `skills.md`.

## Herramientas Agenticas de Código

Las siguientes herramientas permiten bifurcar terminales con capacidades de agente, facilitando la ejecución de comandos o flujos de trabajo más complejos.

### Gemini CLI
- **Descripción:** Permite bifurcar una terminal utilizando el agente Gemini CLI. Ideal para ejecutar flujos de trabajo asistidos por Gemini.
- **Activación:** Cuando el usuario solicita explícitamente usar "Gemini CLI" y `ENABLE_GEMINI_CLI` es `true`.
- **Ejemplos de Uso:**
    - "Fork terminal a <xyz> usando Gemini CLI"
    - "Abre una nueva terminal con gemini-cli para correr <abc>"
    - "Crea una nueva terminal y ejecuta el flujo de Gemini para <xyz>"

### Claude Code
- **Descripción:** Facilita la bifurcación de una terminal con el agente Claude Code. Diseñado para comandos que requieren la asistencia de Claude.
- **Activación:** Cuando el usuario solicita un agente de Claude code y `ENABLE_CLAUDE_CODE` es `true`.
- **Ejemplos de Uso:**
    - "Fork terminal a <xyz> con Claude Code"
    - "Abre una nueva terminal con claude code a <abc> con curl"
    - "Crea una nueva terminal a <xyz> con python"

### Codex CLI
- **Descripción:** Proporciona un flujo de trabajo asistido para la generación de código, permitiendo la bifurcación de una terminal para ejecutar scripts generados por Codex.
- **Activación:** Cuando el usuario solicita un flujo tipo Codex y `ENABLE_CODEX_CLI` es `true`.
- **Ejemplos de Uso:**
    - "Fork terminal a <xyz> usando Codex CLI"
    - "Genera y abre una terminal con codex-cli para ejecutar <abc>"
    - "Crea una nueva terminal y ejecuta el script generado por Codex"

## Herramientas No-Agenticas

### Raw CLI Commands
- **Descripción:** Permite bifurcar una terminal para ejecutar comandos de línea de comandos directamente, sin la intervención de un agente de código.
- **Activación:** Cuando el usuario pide una herramienta no-agentica de código y `ENABLE_RAW_CLI_COMMANDS` es `true`.
- **Ejemplos de Uso:**
    - "Crea una nueva terminal a <xyz> con ffmpeg"
    - "Crea una nueva terminal a <abc> con curl"
    - "Crea una nueva terminal a <xyz> con python"