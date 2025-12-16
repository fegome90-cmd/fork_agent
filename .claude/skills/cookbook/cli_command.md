# Cookbook: Ejecutar comandos CLI seguros

Descripción: patrón para exponer comandos de sistema a través de un agente.

Puntos clave:
- Validación y saneamiento de entrada.
- Modo `--dry-run` por defecto en pruebas.
- Lista blanca o negra de comandos permitidos.

Ejemplo breve:

```
# el agente pregunta al usuario, construye el comando y llama a fork_terminal.py --dry-run --cmd "..."
```
