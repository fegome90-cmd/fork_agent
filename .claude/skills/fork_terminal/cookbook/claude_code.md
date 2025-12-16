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

qqq

#