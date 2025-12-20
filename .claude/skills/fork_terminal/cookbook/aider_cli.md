# Purpose

Ejecuta un agente de Aider CLI nuevo para ejecutar el comando.

## Variables

DEFAULT_MODEL: ollama_chat/qwen3-coder:30b
FAST_MODEL: ollama_chat/qwen3-coder:7b
HEAVY_MODEL: anthropic/claude-3-7-sonnet-20250219
OPENAI_MODEL: gpt-4o
LOCAL_MODEL: ollama_chat/qwen3-coder:30b

## Instructions

- Antes de ejecutar el comando, corre "aider --help" para entender el comando y sus opciones.
- Siempre usa terminales interactivas (no uses -m/--message para modo no-interactivo a menos que el usuario lo solicite explícitamente).
- Para el --model, usa el DEFAULT_MODEL a menos que el usuario especifique lo contrario. Si el usuario pide rápido, usa FAST_MODEL. Si el usuario pide grande/potente, usa HEAVY_MODEL. Si el usuario pide OpenAI, usa OPENAI_MODEL.
- Siempre corre con "--yes-always" para evitar prompts interactivos en modo fork.
- Si el usuario solicita generar un repomap, usa "--show-repo-map".
- Si el usuario quiere modo lectura, usa "--read" para archivos de solo lectura.
- Para editar archivos específicos, usa "--file" para agregarlos al chat.

## Workflow

1. Consultar las opciones disponibles con `aider --help` para validar parámetros y modelos.
2. Determinar el modelo adecuado:
   - `ollama_chat/qwen3-coder:30b` (DEFAULT_MODEL) - Modelo local balanceado
   - `ollama_chat/qwen3-coder:7b` (FAST_MODEL) - Modelo local rápido
   - `anthropic/claude-3-7-sonnet-20250219` (HEAVY_MODEL) - Modelo cloud potente
   - `gpt-4o` (OPENAI_MODEL) - Modelo OpenAI
3. Construir el comando según el caso de uso:
   - **Modo interactivo**: `aider --model <modelo> --yes-always`
   - **Generar repomap**: `aider --model <modelo> --yes-always --show-repo-map > docs/repomap.txt`
   - **Editar archivos**: `aider --model <modelo> --yes-always --file <archivo1> --file <archivo2>`
   - **Modo lectura**: `aider --model <modelo> --yes-always --read <archivo>`
   - **Mensaje único**: `aider --model <modelo> --yes-always --message "<instrucciones>"`
4. Ejecutar la herramienta `fork_terminal` pasando el comando construido como argumento.
5. Confirmar al usuario que se ha iniciado la sesión de Aider en una nueva ventana de terminal o sesión Zellij.

## Examples

### Ejemplo 1: Modo Interactivo con Modelo Local
```bash
aider --model ollama_chat/qwen3-coder:30b --yes-always
```

### Ejemplo 2: Generar Repomap
```bash
aider --model ollama_chat/qwen3-coder:30b --yes-always --show-repo-map > docs/repomap.txt
```

### Ejemplo 3: Editar Archivos Específicos
```bash
aider --model ollama_chat/qwen3-coder:30b --yes-always --file README.md --file src/main.py
```

### Ejemplo 4: Mensaje Único (No Interactivo)
```bash
aider --model ollama_chat/qwen3-coder:30b --yes-always --message "Refactoriza la función main() para mejor manejo de errores"
```

### Ejemplo 5: Usar Modelo Cloud (Claude Sonnet)
```bash
aider --model anthropic/claude-3-7-sonnet-20250219 --yes-always
```

## Notes

- Aider requiere que Ollama esté corriendo para modelos locales (`ollama serve`).
- Para modelos cloud (Claude, GPT-4), asegúrate de tener las API keys configuradas:
  - `ANTHROPIC_API_KEY` para Claude
  - `OPENAI_API_KEY` para GPT-4
- El flag `--yes-always` es crucial en modo fork para evitar que aider se quede esperando confirmaciones.
- Aider automáticamente detecta el repositorio Git y genera un repomap si es necesario.
- Para mejor rendimiento con modelos locales, usa `--no-show-model-warnings` para suprimir advertencias.
