# Integration Analysis: `.claude/skills/fork_terminal/skills.md`

- **Skill purpose**: abre una nueva ventana de terminal a partir del flujo actual, ejecutando comandos directamente o delegando a agentes de código (Gemini CLI, Codex CLI, Claude Code). Se apalanca de un resumen YAML compartido para traspasar contexto.
- **Contexto de shell**: se asume fish como shell del usuario, pero las rutas indicadas (`/workspaces/fork_agent/...`) no corresponden al repo local (`Developer/fork_agent-main`), lo que puede romper la persistencia de contexto si no se alinea.

## Protocolo de orquestación

- **Historial obligatorio**: antes de forkar, se exige generar un resumen YAML de la conversación y escribirlo a `/workspaces/fork_agent/.claude/skills/fork_terminal/prompts/fork_summary_user_prompts.md`, luego releerlo y pasarlo como prompt a `fork_terminal`.
- **Tooling**: el flujo indica llamar al módulo `.claude/skills/fork_terminal/tools/fork_terminal.py:fork_terminal(command: str)` como punto de entrada, tras seleccionar la receta adecuada.
- **Dependencias implícitas**: el protocolo depende de `write_file` y lectura posterior del mismo path; si el path no existe en la máquina actual, la integración con el agente bifurcado fallará silenciosamente o perderá contexto.

## Selección de agente y rutas

- **Raw CLI**: usar cuando se pida una herramienta no-agéntica y `ENABLE_RAW_CLI_COMMANDS=true`; receta en `/fork_agent/.claude/skills/fork_terminal/cookbook/cli_command.md`.
- **Claude Code**: disparar cuando se solicite explícitamente Claude y `ENABLE_CLAUDE_CODE=true`; receta en `/fork_agent/.claude/skills/fork_terminal/cookbook/claude_code.md`.
- **Codex CLI**: usar para flujos de generación asistida y `ENABLE_CODEX_CLI=true`; receta en `/fork_agent/.claude/skills/fork_terminal/cookbook/codex_cli.md`.
- **Gemini CLI**: usar para flujos Gemini y `ENABLE_GEMINI_CLI=true`; receta en `/fork_agent/.claude/skills/fork_terminal/cookbook/gemini_cli.md`.
- **Variables**: se listan banderas ENABLE_* y dos nombres para el set de herramientas (`AGENTIC_CODING_TOOLS` y `AGENTIG_CODING_TOOLS`), generando posible ambigüedad sobre cuál consumir.

## Riesgos y brechas de integración

- **Desalineación de paths**: la ruta fija `/workspaces/fork_agent/...` difiere del repo local (`/Users/felipe_gonzalez/Developer/fork_agent-main`); el fork heredará un prompt vacío o fallará si no se corrige/parametriza.
- **Ambigüedad de variables**: la dualidad `AGENTIC_CODING_TOOLS` vs `AGENTIG_CODING_TOOLS` y mezcla de idiomas puede llevar a que un agente no resuelva correctamente el conjunto de herramientas habilitadas.
- **Cobertura de errores**: no se define qué hacer si la escritura/lectura del resumen falla, ni fallback cuando una receta no está disponible; falta instrucción para validar existencia de paths antes de forkar.
- **Fish vs recetas**: se declara fish como shell, pero no se especifican ajustes en las recetas para compatibilidad de sintaxis (p. ej. `set` vs `export`), lo que puede romper comandos generados por agentes.
- **Typos en ejemplos**: ejemplos de matching contienen errores (“temrinal”, “terminmal”) que pueden afectar lógica de detección si se usan coincidencias literales.

## Recomendaciones

- Parametrizar la raíz del workspace (ej. variable de entorno) y validar/crear `prompts/fork_summary_user_prompts.md` antes de invocar `fork_terminal`.
- Consolidar el nombre de la lista de herramientas (`AGENTIC_CODING_TOOLS`), documentar el formato esperado y cómo un agente debe leerlo.
- Añadir manejo de errores y mensajes claros cuando la persistencia de historial falle o falten recetas.
- Revisar recetas para fish y documentar diferencias de shell para agentes generadores de comandos.
- Corregir typos y referencias de ruta (`/fork_agent/...` vs `.claude/skills/...`) para reducir fricción de matching y descubrimiento.
