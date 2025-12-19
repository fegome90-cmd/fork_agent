# Purpose

Ejecuta un agente de Codex CLI nuevo para ejecutar el comando.

## Variables

DEFAULT_MODEL: gpt-5.2-codex
FAST_MODEL: gpt-5.1-codex-max
HEAVY_MODEL: GPT-5.2- high

## Instructions

- Antes de ejecutar el comando, corre "codex --help" para entender el comando y sus opciones.
- Siempre usa terminales interactivas (no uses el sub-comando 'exec').
- Para el -m/--model, usa el DEFAULT_MODEL a menos que el usuario especifique lo contrario. Si el usuario pide rapido, usa FAST_MODEL. Si el usuario pide grande, usa HEAVY_MODEL.
- Siempre corre con "--dangerously-bypass-approvals-and-sandbox".

## Workflow

1. Consultar la ayuda de Codex con `codex --help` para validar parámetros.
2. Escoger el modelo (`gpt-5.2-codex`, `gpt-5.1-codex-max`, etc.) basándose en si se requiere velocidad o capacidad.
3. Construir el comando: `codex "<instrucciones>" --model <modelo> --dangerously-bypass-approvals-and-sandbox`.
4. Ejecutar `fork_terminal` pasando el comando de Codex resultante.
5. Notificar al usuario que la ventana de terminal ha sido bifurcada con Codex CLI.
