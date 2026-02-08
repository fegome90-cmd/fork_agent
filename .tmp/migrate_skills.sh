#!/bin/bash

# Script para migrar skills de superpowers a Kilo Code

SOURCE_DIR=".tmp/superpowers/skills"
DEST_DIR=".kilocode/skills"

for skill_dir in "$SOURCE_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    dest_skill_name="superpowers-$skill_name"
    dest_path="$DEST_DIR/$dest_skill_name"

    echo "Migrando: $skill_name -> $dest_skill_name"

    # Crear directorio destino
    mkdir -p "$dest_path"

    # Copiar todos los archivos del skill
    cp -r "$skill_dir"/* "$dest_path/"

    # Actualizar frontmatter del SKILL.md
    if [ -f "$dest_path/SKILL.md" ]; then
        # Extraer contenido sin frontmatter original
        content=$(tail -n +5 "$dest_path/SKILL.md")

        # Crear nuevo frontmatter para Kilo Code
        cat > "$dest_path/SKILL.md" <<EOF
---
name: $dest_skill_name
description: "$(head -n 4 "$skill_dir/SKILL.md" | grep "description:" | sed 's/description: //' | tr -d '"')"
license: MIT
metadata:
  category: development
  source:
    repository: https://github.com/obra/superpowers
    path: skills/$skill_name
---

$content
EOF
        echo "  - SKILL.md actualizado"
    fi

    echo "  - Completado: $dest_skill_name"
done

echo ""
echo "Migración completa!"
