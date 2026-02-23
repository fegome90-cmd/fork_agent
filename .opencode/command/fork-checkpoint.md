---
description: "Guarda handoff compacto de sesión actual"
---

# Checkpoint - Save Compact Handoff

Guarda un handoff compacto con SOLO la información esencial para continuar en `.claude/sessions/`.

## REGLAS DE COMPACTACIÓN

| Sección | Límite | Qué Incluir |
|---------|--------|-------------|
| USER REQUESTS | 5 items | Requests originales del usuario |
| WORK COMPLETED | 10 items | Solo lo completado en ESTA sesión |
| CURRENT STATE | 3-4 líneas | Tests, coverage, bloqueos activos |
| PENDING TASKS | 5 items | Tareas priorizadas [HIGH]/[MEDIUM]/[LOW] |
| KEY FILES | 10 archivos | Solo archivos modificados/creados |
| IMPORTANT DECISIONS | 5 items | Decisiones de arquitectura/diseño |
| EXPLICIT CONSTRAINTS | Todos | Son críticas, no omitir |

## NO INCLUIR

- Historial completo de conversación
- Output de comandos (logs, diff completos)
- Código fuente completo (solo paths)
- Errores intermedios ya resueltos

## FORMATO

```markdown
# Handoff - [Tópico Principal]

## HANDOFF CONTEXT

USER REQUESTS (AS-IS)
---------------------
- "[Request 1]"

GOAL
----
[1-2 líneas máximo]

WORK COMPLETED
--------------
- [Item completado]

CURRENT STATE
-------------
- Tests: X/Y
- Coverage: X%
- Bloqueos: [ninguno | descripción]

PENDING TASKS
-------------
1. [HIGH] Tarea 1
2. [MEDIUM] Tarea 2

KEY FILES
---------
- `path/archivo.py` - [breve descripción]

IMPORTANT DECISIONS
-------------------
- [Decisión de arquitectura]

EXPLICIT CONSTRAINTS
--------------------
- [Restricción del proyecto]

CONTEXT FOR CONTINUATION
------------------------
[Punto de entrada claro, 200 palabras máximo]

---

TO CONTINUE:
opencode run -m opencode/glm-5-free "Read .claude/sessions/YYYY-MM-DD-topic.md and continue"
```

## ACCIÓN

1. Verificar existencia de `.claude/sessions/`
2. Generar archivo: `YYYY-MM-DD-[topic].md`
3. Validar tamaño < 10KB
4. Confirmar: "✅ Handoff guardado: .claude/sessions/YYYY-MM-DD-[topic].md"
