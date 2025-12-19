# Purpose

Ejecuta un agente de Claude Code nuevo para ejecutar el comando.

## Variables

DEFOULT_MODEL: sonnet
FAST_MODEL: haiku
BASE_MODEL: sonnet
HEAVY_MODEL: opus

## Instructions

- Antes de ejecutar el comando, corre "claude --help" para entender el comando y sus opciones.
- Siempre usa terminales interactivas(asi que deja fuera -p).
- Para el -m(model), usa el DEFOULT_MODEL a menos que el usuario especifique lo contrario. Si el usuario pide rapido, usa FAST_MODEL. Si el usuario pide grande, usa HEAVY_MODEL.
- Siempre corre con "--dangerously-skip-permissions"

## Workflow

1. Validar la sintaxis del comando solicitado y opciones disponibles con `claude --help`.
2. Determinar el modelo adecuado (`sonnet`, `haiku`, `opus`) basándose en las preferencias del usuario (FAST_MODEL para rápido, HEAVY_MODEL para grande, DEFAULT_MODEL por defecto).
3. Construir el comando completo: `claude "<instrucciones>" -m <modelo> --dangerously-skip-permissions`.
4. Ejecutar la herramienta `fork_terminal` pasando el comando construido como argumento.
5. Confirmar al usuario que se ha iniciado la sesión de Claude Code en una nueva ventana de terminal.

#