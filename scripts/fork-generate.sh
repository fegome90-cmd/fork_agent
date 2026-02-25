#!/usr/bin/env bash
# fork-generate.sh - Genera fork de configuración de agente
# Uso: ./scripts/fork-generate.sh <target_agent> [target_dir]
# Ejemplo: ./scripts/fork-generate.sh .claude ../nuevo-proyecto

set -euo pipefail

# Configuración
TARGET_AGENT="${1:-.claude}"
TARGET_DIR="${2:-.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de utilidad
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Validar agente soportado
validate_agent() {
    case "$TARGET_AGENT" in
        .claude|.opencode|.kilocode|.gemini)
            return 0
            ;;
        *)
            log_error "Agente no soportado: $TARGET_AGENT"
            echo "Agentes soportados: .claude, .opencode, .kilocode, .gemini"
            exit 1
            ;;
    esac
}

# Crear estructura de directorios
create_structure() {
    local agent="$1"
    local dest="$2"
    
    case "$agent" in
        .claude)
            mkdir -p "$dest/.claude"/{commands,skills,sessions,hooks,traces,context_memory/bundles,plans,docs}
            ;;
        .opencode)
            mkdir -p "$dest/.opencode"/{command,plugin}
            ;;
        .kilocode)
            mkdir -p "$dest/.kilocode"/{skills,rules,sessions}
            ;;
        .gemini)
            mkdir -p "$dest/.gemini/skills"
            ;;
    esac
    log_success "Estructura creada para $agent"
}

# Copiar commands
copy_commands() {
    local agent="$1"
    local dest="$2"
    
    local commands=(
        "fork-checkpoint.md"
        "fork-resume.md"
        "fork-prune-sessions.md"
    )
    
    case "$agent" in
        .claude)
            for cmd in "${commands[@]}"; do
                if [[ -f "$PROJECT_ROOT/.opencode/command/$cmd" ]]; then
                    cp "$PROJECT_ROOT/.opencode/command/$cmd" "$dest/.claude/commands/"
                    log_info "Copiado command: $cmd"
                fi
            done
            # Commands adicionales de .claude
            if [[ -d "$PROJECT_ROOT/.claude/commands" ]]; then
                for cmd in "$PROJECT_ROOT/.claude/commands"/*.md; do
                    [[ -f "$cmd" ]] && cp "$cmd" "$dest/.claude/commands/"
                done
            fi
            ;;
        .opencode)
            for cmd in "${commands[@]}" "fork-init.md"; do
                if [[ -f "$PROJECT_ROOT/.opencode/command/$cmd" ]]; then
                    cp "$PROJECT_ROOT/.opencode/command/$cmd" "$dest/.opencode/command/"
                    log_info "Copiado command: $cmd"
                fi
            done
            ;;
    esac
}

# Copiar hooks/plugins
copy_hooks() {
    local agent="$1"
    local dest="$2"
    
    case "$agent" in
        .claude)
            # Copiar hooks shell
            if [[ -d "$PROJECT_ROOT/.hooks" ]]; then
                cp "$PROJECT_ROOT/.hooks"/*.sh "$dest/.claude/hooks/" 2>/dev/null || true
                log_info "Copiados hooks shell"
            fi
            
            # Crear settings.json con hooks
            cat > "$dest/.claude/settings.json" << 'EOF'
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/session-end-hook.sh"
          }
        ]
      }
    ]
  }
}
EOF
            log_success "Creado settings.json con hooks"
            
            # Crear settings.local.json template
            cat > "$dest/.claude/settings.local.json" << 'EOF'
{
  "enabledMcpjsonServers": [],
  "enableAllProjectMcpServers": true
}
EOF
            ;;
        .opencode)
            # Copiar plugins TypeScript
            if [[ -d "$PROJECT_ROOT/.opencode/plugin" ]]; then
                cp "$PROJECT_ROOT/.opencode/plugin"/*.ts "$dest/.opencode/plugin/" 2>/dev/null || true
                log_info "Copiados plugins TypeScript"
            fi
            
            # Crear opencode.json template
            cat > "$dest/opencode.json" << 'EOF'
{
  "model": "opencode/glm-5-free",
  "plugins": ["./.opencode/plugin/session-end.ts"]
}
EOF
            log_success "Creado opencode.json"
            ;;
    esac
}

# Copiar skills custom
copy_skills() {
    local agent="$1"
    local dest="$2"
    
    case "$agent" in
        .claude)
            # Copiar skill fork_terminal completa
            if [[ -d "$PROJECT_ROOT/.claude/skills/fork_terminal" ]]; then
                cp -r "$PROJECT_ROOT/.claude/skills/fork_terminal" "$dest/.claude/skills/"
                log_success "Copiada skill fork_terminal"
            fi
            # Copiar skill fork_agent_session
            if [[ -f "$PROJECT_ROOT/.claude/skills/fork_agent_session.md" ]]; then
                cp "$PROJECT_ROOT/.claude/skills/fork_agent_session.md" "$dest/.claude/skills/"
                log_success "Copiada skill fork_agent_session"
            fi
            ;;
        .opencode|.kilocode|.gemini)
            # Los skills se heredan del directorio skills/ raíz
            log_info "Skills heredados de skills/ raíz"
            ;;
    esac
}

# Crear archivos de estado inicial
create_state_files() {
    local agent="$1"
    local dest="$2"
    
    case "$agent" in
        .claude)
            # Context memory ID
            echo "fork-$(date +%Y%m%d%H%M%S)" > "$dest/.claude/context-memory-id"
            
            # State files vacíos
            for state in plan execute verify; do
                echo '{"status": "idle", "created_at": "'$(date -Iseconds)'"}' > "$dest/.claude/${state}-state.json"
            done
            log_success "Creados archivos de estado"
            ;;
    esac
}

# Crear CLAUDE.md / GEMINI.md template
create_agent_md() {
    local agent="$1"
    local dest="$2"
    local project_name
    project_name=$(basename "$dest")
    
    case "$agent" in
        .claude)
            cat > "$dest/CLAUDE.md" << EOF
# $project_name - CLAUDE.md

> Configuración generada por fork-generate.sh

## Quick Start

\`\`\`bash
# Iniciar workflow
/fork-init [descripción de tarea]

# Workflow completo
memory workflow outline "tarea"
memory workflow execute
memory workflow verify
memory workflow ship
\`\`\`

## Estructura

- \`.claude/commands/\` - Comandos personalizados
- \`.claude/skills/\` - Skills del proyecto
- \`.claude/hooks/\` - Hooks de eventos
- \`.claude/sessions/\` - Handoffs guardados

## Comandos Disponibles

| Comando | Descripción |
|---------|-------------|
| /fork-checkpoint | Guarda handoff de sesión |
| /fork-resume | Continúa desde handoff |
| /fork-prune-sessions | Limpia sesiones antiguas |

---
Generado: $(date -Iseconds)
EOF
            log_success "Creado CLAUDE.md"
            ;;
        .opencode)
            cat > "$dest/OPENCODE.md" << EOF
# $project_name - OPENCODE.md

> Configuración generada por fork-generate.sh

## Comandos

\`\`\`bash
/fork-init        # Inicializar sesión
/fork-checkpoint  # Guardar handoff
/fork-resume      # Continuar desde handoff
\`\`\`

## Plugins

- \`session-end.ts\` - Hook de fin de sesión

---
Generado: $(date -Iseconds)
EOF
            log_success "Creado OPENCODE.md"
            ;;
    esac
}

# Generar resumen
print_summary() {
    local agent="$1"
    local dest="$2"
    
    echo ""
    echo "========================================"
    echo -e "${GREEN}✅ Fork generado exitosamente${NC}"
    echo "========================================"
    echo ""
    echo "Agente: $agent"
    echo "Destino: $dest/$agent"
    echo ""
    echo "Estructura creada:"
    case "$agent" in
        .claude)
            echo "  .claude/"
            echo "  ├── commands/     # Comandos fork"
            echo "  ├── skills/       # Skills custom"
            echo "  ├── hooks/        # Hooks shell"
            echo "  ├── sessions/     # Handoffs"
            echo "  ├── traces/       # Traces"
            echo "  └── *.json        # Estado y config"
            ;;
        .opencode)
            echo "  .opencode/"
            echo "  ├── command/      # Comandos fork"
            echo "  └── plugin/       # Plugins TS"
            echo "  opencode.json     # Config"
            ;;
        .kilocode)
            echo "  .kilocode/"
            echo "  ├── skills/       # Skills"
            echo "  └── rules/        # Reglas"
            ;;
        .gemini)
            echo "  .gemini/"
            echo "  └── skills/       # Skills"
            ;;
    esac
    echo ""
    echo "Próximos pasos:"
    echo "  1. cd $dest"
    echo "  2. Revisar $agent/settings.json (o opencode.json)"
    echo "  3. Personalizar skills/commands según necesidad"
    echo ""
}

# Main
main() {
    log_info "Iniciando fork generation..."
    log_info "Agente: $TARGET_AGENT"
    log_info "Destino: $TARGET_DIR"
    
    validate_agent
    
    # Crear destino si no existe
    mkdir -p "$TARGET_DIR"
    
    # Ejecutar pasos
    create_structure "$TARGET_AGENT" "$TARGET_DIR"
    copy_commands "$TARGET_AGENT" "$TARGET_DIR"
    copy_hooks "$TARGET_AGENT" "$TARGET_DIR"
    copy_skills "$TARGET_AGENT" "$TARGET_DIR"
    create_state_files "$TARGET_AGENT" "$TARGET_DIR"
    create_agent_md "$TARGET_AGENT" "$TARGET_DIR"
    
    print_summary "$TARGET_AGENT" "$TARGET_DIR"
}

main "$@"
