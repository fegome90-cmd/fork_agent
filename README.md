# fork_agent

**fork_agent** es un kit de herramientas para construir y gestionar flujos de trabajo agénticos que interactúan directamente con tu terminal. Su capacidad principal es la habilidad de "bifurcar" (fork) tu sesión actual en nuevas ventanas o sesiones de terminal paralelas, permitiéndote ejecutar múltiples agentes o comandos de larga duración simultáneamente sin bloquear tu flujo de trabajo principal.

## Características Principales

- **Fork Terminal**: Abre instantáneamente nuevas ventanas de terminal para ejecutar comandos.
- **Soporte Multi-Agente**: "Cookbooks" especializados para lanzar diferentes agentes de IA en sus propios entornos:
  - **Raw CLI**: Comandos de shell estándar.
  - **Claude Code**: Lanza una instancia del agente Claude Code.
  - **Codex CLI**: Lanza un agente Codex CLI.
  - **Gemini CLI**: Lanza un agente Gemini.
- **Multi-Plataforma**:
  - **macOS**: Abre ventanas nativas de Terminal.
  - **Windows**: Abre nuevas ventanas de CMD.
  - **Linux**: Crea sesiones de `tmux` desconectadas (ideal para entornos headless/remotos).

## Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <repository-url>
   cd fork_agent
   ```

2. **Configurar el entorno:**
   ```bash
   # Crear un entorno virtual
   python3 -m venv .venv
   source .venv/bin/activate

   # Instalar dependencias (si aplica)
   # pip install -r requirements.txt
   ```

   *Nota: La herramienta principal usa librerías estándar de Python, pero los agentes específicos (como `gemini-cli` o `claude-code`) deben estar instalados y disponibles en tu PATH.*

## Uso

El punto de entrada principal es la herramienta `fork_terminal.py`.

### Sintaxis Básica

```bash
python3 .claude/skills/fork_terminal/tools/fork_terminal.py [comando]
```

La herramienta está diseñada para ser invocada programáticamente por un agente supervisor, pero también puede usarse manualmente.

### Ejemplos

**1. Ejecutar un comando de shell genérico:**
Esto abrirá una nueva terminal y ejecutará el comando.
```bash
python3 .claude/skills/fork_terminal/tools/fork_terminal.py "ping google.com"
```

**2. Lanzar un Agente Gemini (ejemplo completo):**
```bash
python3 .claude/skills/fork_terminal/tools/fork_terminal.py gemini -i "Resumen del README.md" -m gemini-2.5-flash -y
```

**3. Lanzar una sesión de Claude Code:**
```bash
python3 .claude/skills/fork_terminal/tools/fork_terminal.py claude "Refactoriza este archivo"
```

## Estructura del Proyecto

- `.claude/skills/fork_terminal/`: Contiene la lógica del skill de bifurcación.
  - `tools/`: Los scripts de Python que realizan las operaciones del sistema.
  - `cookbook/`: Configuración y estrategias de prompts para diferentes agentes.
  - `prompts/`: Prompts del sistema reutilizables.

## Notas por Plataforma

- **Usuarios de Linux**: Asegúrense de tener `tmux` instalado (`sudo apt install tmux`). La herramienta crea sesiones desconectadas para evitar bloquear tu shell actual.
  - Listar sesiones activas: `tmux ls`
  - Conectarse a una sesión: `tmux attach -t <nombre_sesion>`