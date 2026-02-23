---
description: "Continúa desde el último handoff guardado"
---

# Resume - Continue Last Session

Lee el handoff más reciente y presenta resumen para continuar.

## ACCIÓN

1. Buscar archivos con `ls -t .claude/sessions/*.md` (ordena por fecha)
2. Ordenar por fecha (más reciente primero)
3. Leer el más reciente
4. Presentar resumen estructurado

## FORMATO DE PRESENTACIÓN

```
📋 HANDOFF: YYYY-MM-DD - [Tópico]
==================================

## GOAL
[Objetivo]

## CURRENT STATE
- Tests: X/Y
- Coverage: X%
- Bloqueos: [...]

## PENDING TASKS
1. [HIGH] Tarea 1
2. [MEDIUM] Tarea 2

## KEY FILES
- `archivo.py`

## CONSTRAINTS
- [Restricción]

## CONTINUATION POINT
[Punto de entrada para retomar]

==================================

¿Continuar con las tareas pendientes?
```

## SI NO HAY HANDOFFS

```
❌ No se encontraron handoffs en .claude/sessions/

Para crear uno: /fork-checkpoint
```

## DESPUÉS DE MOSTRAR

Si el usuario confirma continuar:
1. Leer KEY FILES listados
2. Verificar CURRENT STATE (tests, coverage)
3. Iniciar con primera PENDING TASK
4. Respetar EXPLICIT CONSTRAINTS

NO:
- Re-leer todo el historial
- Repetir trabajo ya completado
- Ignorar las restricciones explícitas
