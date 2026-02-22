# Install Superpowers for OpenCode

## TAREA

Instalar el plugin superpowers para OpenCode siguiendo las instrucciones oficiales.

## PASOS A EJECUTAR

### 1. Clone Superpowers
```bash
git clone https://github.com/obra/superpowers.git ~/.config/opencode/superpowers
```

### 2. Register the Plugin
```bash
mkdir -p ~/.config/opencode/plugins
rm -f ~/.config/opencode/plugins/superpowers.js
ln -s ~/.config/opencode/superpowers/.opencode/plugins/superpowers.js ~/.config/opencode/plugins/superpowers.js
```

### 3. Symlink Skills
```bash
mkdir -p ~/.config/opencode/skills
rm -rf ~/.config/opencode/skills/superpowers
ln -s ~/.config/opencode/superpowers/skills ~/.config/opencode/skills/superpowers
```

### 4. Verify Installation
```bash
ls -la ~/.config/opencode/plugins/superpowers.js
ls -la ~/.config/opencode/skills/superpowers
```

## ENTREGA

Guardar reporte de instalación en: .stash/superpowers_install_report.md

Incluir:
- Estado de cada paso
- Output de comandos
- Verificación final
