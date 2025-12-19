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

## Prerequisitos

Antes de instalar fork_agent, asegúrate de tener:

### Python
- **Python 3.8+** requerido

### Herramientas CLI de Agentes (Opcional)
Dependiendo de qué agentes quieras usar, instala:

- **Gemini CLI**: [Instrucciones de instalación](https://github.com/google/generative-ai-python)
- **Claude Code**: [Instrucciones de instalación](https://docs.anthropic.com/claude/docs)
- **Codex CLI**: [Instrucciones de instalación](https://openai.com/codex)

### Multiplexores de Terminal (Linux)
- **tmux**: `sudo apt install tmux` (recomendado)
- **zellij**: `cargo install zellij` (opcional)

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

### Instalación con Nix (Recomendado para Reproducibilidad)

**fork_agent** ahora soporta instalación declarativa con Nix, ofreciendo reproducibilidad total y gestión de dependencias aislada.

#### Ventajas de Usar Nix

- ✅ **Reproducibilidad Total**: Misma configuración en todas tus máquinas
- ✅ **Aislamiento Completo**: No contamina el sistema global
- ✅ **Rollback Automático**: Vuelve a versiones anteriores instantáneamente
- ✅ **Configuración Declarativa**: Todo definido en `flake.nix`
- ✅ **Gestión de Dependencias**: Python y todas las herramientas incluidas

#### Quick Start con Nix

1. **Habilitar Nix Flakes** (una sola vez):
   ```bash
   mkdir -p ~/.config/nix
   echo "experimental-features = nix-command flakes" > ~/.config/nix/nix.conf
   ```

2. **Probar sin instalar**:
   ```bash
   cd fork_agent-main
   nix run . -- "echo 'Hello from fork_agent!'"
   ```

3. **Build local**:
   ```bash
   nix build .#fork-agent
   ./result/bin/fork-terminal-wrapper "echo 'Test!'"
   ```

4. **Instalación global con home-manager**:
   
   Agregar a `~/.config/home-manager/home.nix`:
   ```nix
   let
     fork-agent = (builtins.getFlake "/path/to/fork_agent-main").packages.${pkgs.system}.default;
   in
   {
     home.packages = [ fork-agent ];
     
     home.sessionVariables = {
       FORK_AGENT_HOME = "${fork-agent}/share/fork_agent";
     };
   }
   ```
   
   Luego ejecutar:
   ```bash
   home-manager switch
   ```

#### Testing Validado

La instalación Nix ha sido probada exitosamente en macOS (aarch64-darwin) con:
- ✅ Build completo sin errores
- ✅ Fork terminal funcional
- ✅ Variables de entorno configuradas automáticamente
- ✅ Binarios `fork-terminal` y `fork-terminal-wrapper` creados

Ver [`docs/nix_installation_test_report.md`](docs/nix_installation_test_report.md) para detalles completos del testing.

#### Documentación Adicional

- **Guía completa de instalación global**: [`docs/global_usage_analysis.md`](docs/global_usage_analysis.md)
- **Configuración Nix**: [`flake.nix`](flake.nix) y [`default.nix`](default.nix)
- **Reporte de testing**: [`docs/nix_installation_test_report.md`](docs/nix_installation_test_report.md)

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

### Uso Avanzado con Zellij (Recomendado para Multi-Agentes)

**Zellij** es un multiplexor de terminal moderno que permite supervisar múltiples fork agents en tiempo real desde una sola ventana.

#### Instalación de Zellij

```bash
# macOS
brew install zellij

# Linux (Cargo)
cargo install zellij

# Linux (binario)
wget https://github.com/zellij-org/zellij/releases/latest/download/zellij-x86_64-unknown-linux-musl.tar.gz
tar -xvf zellij-x86_64-unknown-linux-musl.tar.gz
sudo mv zellij /usr/local/bin/
```

#### Comandos Básicos de Zellij

```bash
# Listar sesiones activas
zellij list-sessions

# Crear nueva sesión
zellij --session mi_sesion

# Attacharse a sesión existente
zellij attach mi_sesion

# Attacharse o crear si no existe
zellij attach --create mi_sesion

# Crear sesión en background (sin attacharse)
zellij attach --create-background mi_sesion

# Eliminar sesión
zellij delete-session mi_sesion -f
```

#### Controles de Teclado en Zellij

| Acción | Atajo |
|--------|-------|
| **Modo de comandos** | `Ctrl + p` |
| Detach (salir sin cerrar) | `Ctrl + p` + `d` |
| Siguiente pane | `Ctrl + p` + `n` |
| Pane anterior | `Ctrl + p` + `p` |
| Cerrar pane actual | `Ctrl + p` + `x` |
| Nuevo pane (horizontal) | `Ctrl + p` + `h` |
| Nuevo pane (vertical) | `Ctrl + p` + `v` |
| Modo scroll | `Ctrl + p` + `s` |
| Salir de Zellij | `Ctrl + p` + `q` |

#### Workflow: Supervisar Fork Agents con Zellij

**Paso 1: Crear sesión de Zellij**
```bash
# En tu terminal principal
zellij --session fork_agents
```

**Paso 2: Lanzar fork agents en la sesión**
```bash
# Desde otra terminal, lanzar agentes en panes de la sesión
zellij --session fork_agents action new-pane -- \
  python3 .claude/skills/fork_terminal/tools/fork_terminal.py \
  "gemini -y -m gemini-3-flash-preview 'Analiza el código'"

# Lanzar segundo agente
zellij --session fork_agents action new-pane -- \
  python3 .claude/skills/fork_terminal/tools/fork_terminal.py \
  "gemini -y -m gemini-3-flash-preview 'Genera tests'"

# Lanzar tercer agente
zellij --session fork_agents action new-pane -- \
  python3 .claude/skills/fork_terminal/tools/fork_terminal.py \
  "gemini -y -m gemini-3-flash-preview 'Documenta funciones'"
```

**Paso 3: Supervisar desde otra terminal**
```bash
# Attacharse a la sesión para ver todos los agentes
zellij attach fork_agents
```

**Paso 4: Navegar entre panes**
- Usa `Ctrl + p` + `n` para ver cada agente
- Usa `Ctrl + p` + `s` para hacer scroll y revisar output
- Usa `Ctrl + p` + `d` para detach sin cerrar

#### Ejemplo Completo: 3 Agentes Concurrentes

```bash
# Terminal 1: Crear sesión
zellij --session analisis_proyecto

# Terminal 2: Lanzar 3 agentes
for task in "analizar código" "generar tests" "crear docs"; do
  zellij --session analisis_proyecto action new-pane -- \
    python3 .claude/skills/fork_terminal/tools/fork_terminal.py \
    "gemini -y 'Tarea: $task'"
done

# Terminal 1 o 3: Supervisar
zellij attach analisis_proyecto
# Ahora ves los 3 agentes ejecutándose en paralelo
```

#### Verificar Resultados con Agent Checkout System

El sistema de checkout automático registra todos los agentes:

```bash
# Ver log de checkout
tail -f .claude/logs/agent_checkout.log

# Generar resumen de agentes
python3 .claude/scripts/generate_agent_summary.py

# Monitoreo en tiempo real
.claude/scripts/monitor_agents.sh
```

#### Troubleshooting Zellij

**Problema**: "Session already exists"
```bash
# Solución: Attacharse en lugar de crear
zellij attach nombre_sesion
```

**Problema**: "Can't find session"
```bash
# Solución: Listar sesiones activas
zellij list-sessions
```

**Problema**: "Pane no se crea"
```bash
# Solución: Verificar que la sesión existe primero
zellij attach --create-background nombre_sesion
# Luego crear pane
zellij --session nombre_sesion action new-pane -- comando
```

**Problema**: "No puedo salir de Zellij"
```bash
# Solución: Detach con Ctrl+p + d
# O forzar cierre: Ctrl+p + q
```



- Para mejor resultado usar terminos consisos, por ejemplo: fork nueva terminal, gemini-cli, fast model, summary history " analiza el "@/workspaces/fork_agent/.claude/skills/fork_terminal/prompts/fork_summary_user_prompts.md " y haz un resumen en .claude/docs
  
- Este repo esta hecho en base al desarrolador indydevdan y el credito de toda esta idea es totalmente suyo.
