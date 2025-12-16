# fork_agent

**fork_agent** es una plataforma agéntica avanzada diseñada para transformar y optimizar la interacción con tu terminal. Su capacidad central reside en la habilidad `fork_terminal`, que permite "bifurcar" (fork) tu sesión actual a nuevas ventanas o sesiones de terminal paralelas. Esta funcionalidad es esencial para ejecutar comandos de forma controlada y auditable, gestionar flujos de trabajo complejos, aislar tareas o ejecutar operaciones concurrentes sin interrumpir tu proceso principal.

`fork_terminal` actúa como un orquestador, eligiendo la estrategia de ejecución más adecuada para cada solicitud del usuario. Puede lanzar:
- **Comandos CLI Directos**: Para ejecuciones de shell estándar.
- **Agentes de Codificación (AI Models)**: Integrando modelos como Claude Code, Codex CLI y Gemini CLI. Estos agentes permiten la generación inteligente de comandos, la ejecución de scripts y la interacción contextual, utilizando el historial de conversación para generar prompts avanzados, especialmente cuando se solicita un "resumen" de la tarea.

Un "Cookbook" interno guía a `fork_agent` para seleccionar la herramienta idónea según la preferencia del usuario y el contexto, asegurando una ejecución eficiente y adaptada. El sistema promueve un entorno seguro y auditable, con recomendaciones clave para el uso de `--dry-run` o entornos aislados.

## Características Principales

- **Orquestación de Terminal**: Bifurca sesiones para gestionar tareas complejas y concurrentes.
- **Soporte Multi-Agente Avanzado**:
  - **Raw CLI**: Ejecución directa de comandos de shell.
  - **Claude Code**: Para interacciones programáticas asistidas por IA.
  - **Codex CLI**: Generación y ejecución de código asistida.
  - **Gemini CLI**: Integración con el potente modelo Gemini para comandos inteligentes.
- **Contexto Conversacional**: Utiliza el historial del chat para enriquecer los prompts de los agentes, permitiendo resúmenes de trabajo y una ejecución más inteligente.
- **Multi-Plataforma Robusta**:
  - **macOS**: Abre ventanas nativas de Terminal.
  - **Windows**: Inicia nuevas ventanas de CMD.
  - **Linux**: Prioriza emuladores de terminal comunes; si no los encuentra, crea sesiones de `tmux` desconectadas, ideal para entornos headless o remotos.

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

- Para mejor resultado usar terminos consisos, por ejemplo: fork nueva terminal, gemini-cli, fast model, summary history " analiza el "@/workspaces/fork_agent/.claude/skills/fork_terminal/prompts/fork_summary_user_prompts.md " y haz un resumen en .claude/docs