---
description: "Elimina handoffs antiguos (default: 30 días)"
---

# Prune Sessions - Clean Old Handoffs

Elimina archivos handoff antiguos para mantener el directorio limpio.

## ACCIÓN

1. Obtener límite de días (default: 30, o argumento del usuario)
2. Listar archivos en `.claude/sessions/*.md`
3. Calcular antigüedad de cada archivo
4. Mostrar resumen antes de eliminar
5. Eliminar SOLO después de confirmación

## CÁLCULO DE ANTIGÜEDAD

```bash
# Por cada archivo, calcular días desde modificación
for file in .claude/sessions/*.md; do
    file_date=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file")
    age_days=$(( (today - file_date) / 86400 ))
done
```

## FORMATO DE PRESENTACIÓN

```
🧹 ANÁLISIS DE HANDOFFS
=======================

Total archivos: X
Antiguos (>$DAYS días): Y

Archivos a eliminar:
┌─────────────────────────────┬───────┐
│ Archivo                     │ Días  │
├─────────────────────────────┼───────┤
│ 2025-12-15-feature-x.md     │ 68    │
└─────────────────────────────┴───────┘

Archivos a conservar:
┌─────────────────────────────┬───────┐
│ 2026-02-22-memory-cli.md    │ 0     │
└─────────────────────────────┴───────┘

¿Eliminar Y archivos antiguos?
```

## ARGUMENTOS OPCIONALES

- `/prune-sessions 7` - Eliminar mayores a 7 días
- `/prune-sessions 60` - Eliminar mayores a 60 días
- `/prune-sessions --dry-run` - Solo mostrar, no eliminar
- `/prune-sessions --all` - Eliminar todos menos el último

## REGLA DE SEGURIDAD

**Siempre conservar al menos los 3 handoffs más recientes**, sin importar antigüedad.

## EJECUCIÓN

Solo eliminar después de confirmación del usuario:
```bash
rm -f archivo1.md archivo2.md ...
echo "✅ Eliminados Y archivos antiguos"
```
