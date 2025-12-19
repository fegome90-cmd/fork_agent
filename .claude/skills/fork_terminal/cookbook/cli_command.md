# Purpose

Ejecuta un comando CLI crudo.

## Instructions

- Antes de ejecutar el comando, corre "<command> --help" para entender el comando y sus opciones.
- Lee la solicitud del usuario.
## Workflow

1. Verificar la disponibilidad y opciones del comando base usando `<command> --help`.
2. Analizar y limpiar los argumentos proporcionados para construir el comando CLI final de forma segura.
3. Ejecutar `fork_terminal` con el comando CLI crudo resultante.
4. Confirmar al usuario que el comando se está ejecutando en una nueva ventana de terminal.