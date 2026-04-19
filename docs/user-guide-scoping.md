# User Guide: Memory Scoping & Project Filters

En `tmux_fork`, cada memoria (observación) pertenece a un **proyecto** y tiene un **tipo**. Esto permite a los sub-agentes SDD y a ti mismo organizar el conocimiento sin colisiones.

## 1. Guardando Memorias con Scope

Puedes especificar el proyecto y el tipo manualmente o dejar que el sistema lo detecte.

```bash
# Con flags explícitos
uv run memory save "Definición de arquitectura" --project "mi-app" --type "architecture"

# Con flags cortos
uv run memory save "Bug encontrado en auth" -p "mi-app" -t "bugfix"

# Auto-detección (detecta el nombre del repo desde git remote)
uv run memory save "Nota rápida en el repo actual"
```

## 2. Buscando con Filtros

Usa los nuevos filtros estructurales para refinar tus búsquedas:

```bash
# Listar memorias solo de un proyecto
uv run memory list --project "mi-app"

# Buscar decisiones dentro de un proyecto
uv run memory search "auth" --project "mi-app" --type "decision"
```

## 3. Ergonomía de IDs (Prefix Matching)

Ya no necesitas copiar el UUID de 36 caracteres completo.

- **Listado claro**: `memory list` ahora muestra los primeros 12 caracteres: `[b5736c84-4bd]`.
- **Recuperación rápida**: Puedes usar solo el prefijo (ej. 8 caracteres) para obtener el detalle:
  ```bash
  uv run memory get b5736c84
  ```
  *(Nota: Si el prefijo es ambiguo y coincide con más de una memoria, el sistema te pedirá más caracteres por seguridad).*

## 4. Upsert Inteligente

Si usas un `topic_key` en la metadata, el sistema **sobrescribirá** la memoria existente en lugar de duplicarla:

```bash
# Primera vez crea
uv run memory save "Estado: inicial" -m '{"topic_key": "sdd/status"}'

# Segunda vez actualiza (mismo ID, contenido nuevo)
uv run memory save "Estado: actualizado" -m '{"topic_key": "sdd/status"}'
```
