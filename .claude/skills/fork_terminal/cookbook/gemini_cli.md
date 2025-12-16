# Purpose

Ejecuta un agente de Gemini CLI nuevo para ejecutar el comando.

## Variables

DEFAULT_MODEL: gemini-3.0-pro-preview
FAST_MODEL: gemini-2.5-flash
HEAVY_MODEL: gemini-3.0-pro-preview

## Instructions

- Antes de ejecutar el comando, corre "gemini --help" para entender el comando y sus opciones.
- Siempre usa terminales interactivas (no uses -p/--prompt).
- Para el -m/--model, usa el DEFAULT_MODEL a menos que el usuario especifique lo contrario. Si el usuario pide rapido, usa FAST_MODEL. Si el usuario pide grande, usa HEAVY_MODEL.
- Siempre corre con "-y" o "--yolo".

## Workflow

qqq
