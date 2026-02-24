#!/usr/bin/env bash
# fork-verify.sh - Verifica integridad de fork de agente
# Uso: ./scripts/fork-verify.sh <target_dir> [--strict]
# Ejemplo: ./scripts/fork-verify.sh .claude
#          ./scripts/fork-verify.sh .claude --strict

set -uo pipefail

# Configuración
TARGET_DIR="${1:-.}"
STRICT="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Contadores
ERRORS=0
WARNINGS=0

# Funciones
log_error() { echo -e "${RED}[ERROR]${NC} $1"; ((ERRORS++)); }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; ((WARNINGS++)); }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }

# Normalizar path
normalize_path() {
    local path="$1"
    if [[ "$path" != /* ]]; then
        path="$(pwd)/$path"
    fi
    echo "$path"
}

TARGET_DIR=$(normalize_path "$TARGET_DIR")

# Validar agente (detectar tipo)
detect_agent_type() {
    local dir="$TARGET_DIR"
    
    # Si el directorio mismo es .claude, .opencode, etc.
    local basename
    basename=$(basename "$dir")
    case "$basename" in
        .claude|.opencode|.kilocode|.gemini)
            echo "$basename"
            return
            ;;
    esac
    
    # Buscar como subdirectorio
    if [[ -d "$dir/.claude" ]]; then
        echo ".claude"
    elif [[ -d "$dir/.opencode" ]]; then
        echo ".opencode"
    elif [[ -d "$dir/.kilocode" ]]; then
        echo ".kilocode"
    elif [[ -d "$dir/.gemini" ]]; then
        echo ".gemini"
    else
        echo "unknown"
    fi
}

get_agent_dir() {
    local agent="$1"
    local dir="$TARGET_DIR"
    
    # Si el directorio mismo es el agente, usar directo
    local basename
    basename=$(basename "$dir")
    if [[ "$basename" == "$agent" ]]; then
        echo "$dir"
    else
        echo "$dir/$agent"
    fi
}

# Validar estructura de directorios
validate_structure() {
    local agent="$1"
    local agent_dir
    agent_dir=$(get_agent_dir "$agent")
    
    log_info "Validando estructura de directorios..."
    
    case "$agent" in
        .claude)
            local required_dirs=(
                "commands"
                "skills"
                "hooks"
                "sessions"
            )
            for dir in "${required_dirs[@]}"; do
                if [[ -d "$agent_dir/$dir" ]]; then
                    log_ok "Directorio: $agent/$dir"
                else
                    log_error "Falta directorio: $agent/$dir"
                fi
            done
            ;;
        .opencode)
            local required_dirs=(
                "command"
                "plugin"
            )
            for dir in "${required_dirs[@]}"; do
                if [[ -d "$agent_dir/$dir" ]]; then
                    log_ok "Directorio: $agent/$dir"
                else
                    log_error "Falta directorio: $agent/$dir"
                fi
            done
            ;;
        .kilocode)
            local required_dirs=(
                "skills"
                "rules"
            )
            for dir in "${required_dirs[@]}"; do
                if [[ -d "$agent_dir/$dir" ]]; then
                    log_ok "Directorio: $agent/$dir"
                else
                    log_error "Falta directorio: $agent/$dir"
                fi
            done
            ;;
        .gemini)
            if [[ -d "$agent_dir/skills" ]]; then
                log_ok "Directorio: $agent/skills"
            else
                log_error "Falta directorio: $agent/skills"
            fi
            ;;
    esac
}

# Validar JSON
validate_json() {
    local file="$1"
    local description="$2"
    
    if [[ ! -f "$file" ]]; then
        log_error "$description: archivo no existe ($file)"
        return 1
    fi
    
    if python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
        log_ok "$description: JSON válido"
        return 0
    else
        log_error "$description: JSON inválido ($file)"
        return 1
    fi
}

# Validar archivos JSON requeridos
validate_json_files() {
    local agent="$1"
    local agent_dir
    agent_dir=$(get_agent_dir "$agent")
    
    log_info "Validando archivos JSON..."
    
    case "$agent" in
        .claude)
            validate_json "$agent_dir/settings.json" "settings.json"
            if [[ -f "$agent_dir/settings.local.json" ]]; then
                validate_json "$agent_dir/settings.local.json" "settings.local.json"
            fi
            ;;
        .opencode)
            validate_json "$TARGET_DIR/opencode.json" "opencode.json"
            ;;
    esac
}

# Validar hooks
validate_hooks() {
    local agent="$1"
    local agent_dir
    agent_dir=$(get_agent_dir "$agent")
    
    log_info "Validando hooks..."
    
    case "$agent" in
        .claude)
            local hooks_json="$agent_dir/settings.json"
            if [[ ! -f "$hooks_json" ]]; then
                log_warn "No hay settings.json para validar hooks"
                return 0
            fi
            
            local hook_cmds
            hook_cmds=$(python3 -c "
import json
import sys
try:
    data = json.load(open('$hooks_json'))
    commands = []
    if 'hooks' in data:
        for event, hooks_list in data['hooks'].items():
            for hook in hooks_list:
                if 'hooks' in hook:
                    for h in hook['hooks']:
                        if h.get('type') == 'command':
                            commands.append(h.get('command', ''))
    for cmd in commands:
        print(cmd)
except:
    sys.exit(1)
" 2>/dev/null) || true
            
            if [[ -z "$hook_cmds" ]]; then
                log_warn "No se pudieron extraer comandos de hooks"
                return 0
            fi
            
            while IFS= read -r cmd; do
                [[ -z "$cmd" ]] && continue
                # Normalize: remove leading "./" if present
                local normalized_cmd="${cmd#./}"
                # Get agent basename (e.g., ".claude") and remove that prefix
                local agent_basename
                agent_basename=$(basename "$agent_dir")
                local hook_file="${normalized_cmd#${agent_basename}/}"
                if [[ -f "$agent_dir/$hook_file" ]] || [[ -f "$agent_dir/hooks/$hook_file" ]]; then
                    log_ok "Hook existente: $hook_file"
                else
                    log_error "Hook referenciado no existe: $hook_file"
                fi
            done <<< "$hook_cmds"
            ;;
    esac
}

# Validar comandos requeridos
validate_commands() {
    local agent="$1"
    local agent_dir
    agent_dir=$(get_agent_dir "$agent")
    
    log_info "Validando comandos..."
    
    case "$agent" in
        .claude)
            local required_commands=(
                "fork-checkpoint.md"
                "fork-resume.md"
            )
            for cmd in "${required_commands[@]}"; do
                if [[ -f "$agent_dir/commands/$cmd" ]]; then
                    log_ok "Comando presente: $cmd"
                else
                    log_error "Falta comando: $cmd"
                fi
            done
            ;;
        .opencode)
            local required_commands=(
                "fork-checkpoint.md"
                "fork-resume.md"
            )
            for cmd in "${required_commands[@]}"; do
                if [[ -f "$agent_dir/command/$cmd" ]]; then
                    log_ok "Comando presente: $cmd"
                else
                    log_error "Falta comando: $cmd"
                fi
            done
            ;;
    esac
}

# Validar skills requeridas
validate_skills() {
    local agent="$1"
    local agent_dir
    agent_dir=$(get_agent_dir "$agent")
    
    log_info "Validando skills..."
    
    case "$agent" in
        .claude)
            if [[ -d "$agent_dir/skills" ]]; then
                local skill_count
                skill_count=$(find "$agent_dir/skills" -maxdepth 1 -type f -name "*.md" 2>/dev/null | wc -l)
                local dir_count
                dir_count=$(find "$agent_dir/skills" -maxdepth 1 -type d 2>/dev/null | wc -l)
                local total=$((skill_count + dir_count - 1))
                if [[ $total -gt 0 ]]; then
                    log_ok "Skills encontradas: $total"
                else
                    log_warn "No hay skills en $agent/skills"
                fi
            else
                log_warn "Directorio de skills no existe"
            fi
            ;;
    esac
}

# Validar archivos de estado
validate_state_files() {
    local agent="$1"
    local agent_dir
    agent_dir=$(get_agent_dir "$agent")
    
    log_info "Validando archivos de estado..."
    
    case "$agent" in
        .claude)
            local state_files=(
                "plan-state.json"
                "execute-state.json"
                "verify-state.json"
            )
            for state in "${state_files[@]}"; do
                if [[ -f "$agent_dir/$state" ]]; then
                    if validate_json "$agent_dir/$state" "$state" >/dev/null 2>&1; then
                        log_ok "Estado válido: $state"
                    fi
                else
                    log_warn "Estado no existe: $state"
                fi
            done
            ;;
    esac
}

# Main
main() {
    echo "========================================"
    echo "fork-verify.sh - Verificador de integridad"
    echo "========================================"
    echo ""
    log_info "Target: $TARGET_DIR"
    
    if [[ ! -d "$TARGET_DIR" ]]; then
        log_error "Directorio no existe: $TARGET_DIR"
        echo ""
        echo "========================================"
        echo "RESULTADO: INVALID"
        echo "========================================"
        exit 2
    fi
    
    local agent
    agent=$(detect_agent_type)
    
    if [[ "$agent" == "unknown" ]]; then
        log_error "No se detectó tipo de agente válido"
        log_info "Buscando: .claude, .opencode, .kilocode, .gemini"
        echo ""
        echo "========================================"
        echo "RESULTADO: INVALID"
        echo "========================================"
        exit 2
    fi
    
    log_info "Tipo de agente detectado: $agent"
    echo ""
    
    # Ejecutar validaciones
    validate_structure "$agent"
    echo ""
    
    validate_json_files "$agent"
    echo ""
    
    validate_hooks "$agent"
    echo ""
    
    validate_commands "$agent"
    echo ""
    
    validate_skills "$agent"
    echo ""
    
    validate_state_files "$agent"
    echo ""
    
    # Resumen
    echo "========================================"
    echo "RESUMEN"
    echo "========================================"
    echo "Errores: $ERRORS"
    echo "Warnings: $WARNINGS"
    echo ""
    
    if [[ $ERRORS -gt 0 ]]; then
        echo "RESULTADO: INVALID"
        echo "========================================"
        exit 2
    elif [[ $WARNINGS -gt 0 && "$STRICT" == "--strict" ]]; then
        echo "RESULTADO: WARNINGS (strict mode)"
        echo "========================================"
        exit 1
    elif [[ $WARNINGS -gt 0 ]]; then
        echo "RESULTADO: OK con warnings"
        echo "========================================"
        exit 0
    else
        echo "RESULTADO: OK"
        echo "========================================"
        exit 0
    fi
}

main "$@"
