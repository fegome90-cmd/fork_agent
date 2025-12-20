# Purpose

Ejecuta un comando CLI crudo.

## Instructions

- Antes de ejecutar el comando, corre "<command> --help" para entender el comando y sus opciones.
- Lee la solicitud del usuario.
## Workflow

1. Verificar si WezTerm CLI está disponible con `wezterm --help` para entender sus opciones.
2. Si WezTerm está disponible, considerar usarlo directamente con `wezterm -n start -- <comando>` para máxima compatibilidad.
3. Verificar la disponibilidad y opciones del comando base usando `<command> --help`.
4. Analizar y limpiar los argumentos proporcionados para construir el comando CLI final de forma segura.
5. Ejecutar `fork_terminal` con el comando CLI resultante (WezTerm tendrá prioridad en macOS).
6. Confirmar al usuario que el comando se está ejecutando en una nueva ventana de terminal.