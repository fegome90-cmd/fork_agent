# Purpose

Ejecuta un agente de Gemini CLI nuevo para ejecutar el comando.

## Variables

DEFAULT_MODEL: gemini-3-pro-preview
FAST_MODEL: gemini-3-flash-preview
HEAVY_MODEL: gemini-3.0-pro-preview

## Instructions

- Antes de ejecutar el comando, corre "gemini --help" para entender el comando y sus opciones.
- Siempre usa terminales interactivas (no uses -p/--prompt).
- Para el -m/--model, usa el DEFAULT_MODEL a menos que el usuario especifique lo contrario. Si el usuario pide rapido, usa FAST_MODEL. Si el usuario pide grande, usa HEAVY_MODEL.
- Siempre corre con "-y" o "--yolo".

## Workflow

1. Revisar las opciones de comando y modelos con `gemini --help`.
2. Seleccionar el modelo (`gemini-3-pro-preview`, `gemini-3-flash-preview`, etc.) según la solicitud del usuario.
3. Construir el comando final: `gemini "<instrucciones>" -m <modelo> --yolo`.
4. Invocar `fork_terminal` con el comando de Gemini construido.
5. Informar al usuario sobre la apertura de la nueva terminal con la sesión de Gemini activa.
