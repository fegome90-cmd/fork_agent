# Handoff - Sistema de Memoria fork_agent

## HANDOFF CONTEXT

USER REQUESTS (AS-IS)
---------------------
- "Actúa como un Ingeniero de Software Senior (Python/SQL) y Arquitecto de Sistemas. Eres un purista de la calidad de código, especializado en Clean Architecture, Functional Programming (FP) aplicado a Python y Test Driven Development (TDD) estricto."
- "TDD First: Prohibido escribir código de implementación sin antes escribir el test que falla (Red-Green-Refactor)."
- "Code Standards: Python 3.10+, Tipado estático estricto (typing), Pydantic para validación de datos."
- "Testing: Pytest. Cobertura mínima obligatoria: 90%."
- "Arquitectura: Clean Architecture (Entities -> Use Cases -> Interface Adapters)."

GOAL
----
Completar Fase 2 del sistema de memoria: fix tests de error handling, añadir tests de validación, alcanzar 95% coverage, e implementar MemoryService.

WORK COMPLETED
--------------
- Fase 1 (Foundation) completada al 100%
- SQLite connection con WAL mode, busy_timeout, pathlib.Path
- Sistema de migraciones secuenciales SQL (NNN_description.sql)
- DI container con dependency-injector usando Configuration provider
- FTS5 schema con triggers automáticos para full-text search
- Entidad Observation creada (frozen dataclass con validación)
- ObservationRepository con CRUD + search FTS5 implementado
- 40+ tests escritos, 69 pasando de 77
- Code review guardado en .stash/code_reviews/review_20260222_033000.md
- Configuración de OpenCode CLI creada en .claude/skills/fork_terminal/cookbook/opencode_cli.md

CURRENT STATE
-------------
- Tests: 69/77 pasando (89.6%)
- Coverage: 62.23% (target: 95%)
- Coverage repository: 86.79%
- Coverage observation entity: 63.16%
- 7 tests de error handling fallando por intentar mockear __enter__ (read-only por __slots__)
- 1 test preexistente fallando (test_get_required_success - SHELL env)

PENDING TASKS
-------------
1. [HIGH] Fix 7 tests de error handling en test_observation_repository.py
2. [HIGH] Añadir tests de validación para Observation.__post_init__
3. [HIGH] Alcanzar 95% de coverage
4. [MEDIUM] Añadir ObservationRepository al DI container
5. [MEDIUM] Implementar MemoryService para business logic
6. [LOW] Crear CLI commands: memory save/search/list

KEY FILES
---------
- src/infrastructure/persistence/database.py - SQLite connection con WAL
- src/infrastructure/persistence/migrations.py - Sistema de migraciones
- src/infrastructure/persistence/container.py - DI container
- src/domain/entities/observation.py - Entidad Observation
- src/infrastructure/persistence/repositories/observation_repository.py - Repository CRUD + FTS
- tests/unit/infrastructure/test_observation_repository.py - Tests del repository (7 failing)
- tests/unit/domain/test_observation.py - Tests de entidad
- AGENTS.md - Guía de código para agentes
- .stash/code_reviews/review_20260222_033000.md - Code review detallado

IMPORTANT DECISIONS
-------------------
- Modelos gratuitos OpenCode: glm-5-free (principal), minimax-m2.5-free (rápido), trinity-large-preview-free (pesado)
- Pydantic frozen=True para inmutabilidad
- SQLite WAL mode con busy_timeout=5000ms
- FTS5 con triggers automáticos para sync
- dependency-injector Configuration provider (NO providers.Object)
- __slots__ para optimización de memoria

EXPLICIT CONSTRAINTS
--------------------
- TDD First: Prohibido escribir código de implementación sin antes escribir el test que falla
- Cobertura mínima: 95% (pyproject.toml)
- mypy strict mode
- frozen=True para todas las entidades
- NO usar as any, @ts-ignore, type: ignore

CONTEXT FOR CONTINUATION
------------------------
- Los tests de error handling fallan porque DatabaseConnection usa __slots__ y __enter__ es read-only
- Solución: Usar subclassing o inyección de conexión que falle, NO mockear __enter__
- El code review en .stash/code_reviews/ tiene código de ejemplo para fix
- Coverage bajo en validaciones de Observation (líneas 31,33,35,37,39,41,43)
- Usar "uv run pytest tests/unit/infrastructure/ -v --cov=src" para verificar

---

## ORQUESTACIÓN CON SUBAGENTES OPENCODE

### Modelos Gratuitos Disponibles

| Modelo | Uso | Comando |
|--------|-----|---------|
| `opencode/glm-5-free` | Principal | `opencode run -m opencode/glm-5-free "prompt"` |
| `opencode/minimax-m2.5-free` | Rápido | `opencode run -m opencode/minimax-m2.5-free "prompt"` |
| `opencode/trinity-large-preview-free` | Pesado | `opencode run -m opencode/trinity-large-preview-free "prompt"` |

### Patrones de Delegación

#### 1. Tarea Rápida (quick)
```bash
opencode run -m opencode/minimax-m2.5-free -c /home/user/fork_agent "Fix simple typo in test file"
```

#### 2. Tarea Compleja (deep)
```bash
opencode run -m opencode/glm-5-free -c /home/user/fork_agent "Implement ObservationRepository error handling tests without mocking __enter__"
```

#### 3. Tarea Pesada (ultrabrain)
```bash
opencode run -m opencode/trinity-large-preview-free -c /home/user/fork_agent "Design and implement MemoryService architecture"
```

### Protocolo de Fork con Handoff

1. Crear archivo de contexto en `/tmp/handoff_context.txt`
2. Lanzar subagente con: `opencode run -m <model> "Read /tmp/handoff_context.txt and continue"`
3. Subagente trabaja y entrega resultado en `.stash/`

---

## PROMPTS PARA SUBAGENTES

### Subagente 1: Fix Error Handling Tests

```
TAREA: Fix 7 tests de error handling en test_observation_repository.py

PROBLEMA: Los tests intentan mockear __enter__ de DatabaseConnection, pero es read-only por __slots__.

SOLUCIÓN: Usar subclassing:
1. Crear FailingConnection que herede de DatabaseConnection
2. Override __enter__ para retornar conexión que falle
3. Usar side_effect en execute para simular errores

ARCHIVOS:
- tests/unit/infrastructure/test_observation_repository.py (líneas 652-750)

EJEMPLO DE FIX:
class FailingConnection(DatabaseConnection):
    def __enter__(self):
        conn = super().__enter__()
        original_execute = conn.execute
        def failing_execute(*args, **kwargs):
            if "INSERT" in str(args[0] if args else ""):
                raise sqlite3.Error("Database error")
            return original_execute(*args, **kwargs)
        conn.execute = failing_execute
        return conn

ENTREGAR: Tests pasando, guardar reporte en .stash/fix_error_tests.md
```

### Subagente 2: Tests de Validación

```
TAREA: Añadir tests de validación para Observation.__post_init__

ARCHIVO: tests/unit/domain/test_observation.py

TESTS NECESARIOS:
1. test_observation_invalid_id_type - id no es string
2. test_observation_empty_id - id vacío
3. test_observation_invalid_timestamp_type - timestamp no es int
4. test_observation_negative_timestamp - timestamp negativo
5. test_observation_empty_content - content vacío
6. test_observation_invalid_content_type - content no es string
7. test_observation_invalid_metadata_type - metadata no es dict

ENTREGAR: Tests pasando, coverage >= 95% en observation.py
```

### Subagente 3: Code Review Final

```
TAREA: Code review del código modificado

EJECUTAR:
1. uv run pytest tests/unit/infrastructure/ -v --cov=src
2. uv run mypy src/
3. uv run ruff check src/

VERIFICAR:
- Coverage >= 95%
- Sin errores de tipo
- Sin linting errors

ENTREGAR: Reporte en .stash/code_reviews/final_review_YYYYMMDD.md
```

---

## WORKFLOW DE ORQUESTACIÓN

### Paso 1: Lanzar Subagente de Fix
```bash
# Crear contexto
cat << 'EOF' > /tmp/handoff_fix_tests.txt
$(cat /home/user/fork_agent/.stash/handoff_prompt.md | head -50)
TAREA ESPECÍFICA: Fix error handling tests
EOF

# Lanzar en tmux
tmux new-session -d -s fix_tests -c /home/user/fork_agent
tmux send-keys -t fix_tests "opencode run -m opencode/glm-5-free 'Read /tmp/handoff_fix_tests.txt and fix the error handling tests. Save report to .stash/fix_report.md'" Enter
```

### Paso 2: Lanzar Subagente de Validación
```bash
tmux new-session -d -s add_tests -c /home/user/fork_agent
tmux send-keys -t add_tests "opencode run -m opencode/glm-5-free 'Add validation tests for Observation entity in tests/unit/domain/test_observation.py. Cover all __post_init__ validations. Target 95% coverage.'" Enter
```

### Paso 3: Verificar Resultados
```bash
# Esperar a que terminen
tmux list-sessions

# Ver resultados
cat .stash/fix_report.md
uv run pytest tests/unit/infrastructure/ -v --cov=src
```

---

## COMANDOS ÚTILES

```bash
# Ver sesiones activas
tmux list-sessions

# Adjuntar a sesión
tmux attach -t <session_name>

# Ver output de sesión
tmux capture-pane -t <session_name> -p

# Matar sesión
tmux kill-session -t <session_name>

# Ejecutar tests
uv run pytest tests/unit/infrastructure/ -v --cov=src

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```

---

## ENTREGA ESPERADA

Después de completar todas las tareas:

1. `.stash/fix_report.md` - Reporte del fix de tests
2. `.stash/validation_report.md` - Reporte de tests de validación
3. `.stash/code_reviews/final_review.md` - Review final
4. Coverage >= 95%
5. Todos los tests pasando
6. ObservationRepository añadido al DI container

---

TO CONTINUE IN A NEW SESSION:

1. Run: `opencode -m opencode/glm-5-free`
2. Paste the content of this file as your first message
3. Add: "Execute the orchestration workflow and complete pending tasks"

Or use directly:
```bash
opencode run -m opencode/glm-5-free "Read /home/user/fork_agent/.stash/handoff_prompt.md and execute the orchestration workflow to complete all pending tasks."
```

## TMUX ORCHESTRATOR API

### Python API

```python
from src.infrastructure.tmux_orchestrator import (
    TmuxOrchestrator,
    create_agent_session,
    send_task_to_agent,
    get_agent_output,
)

# Crear agente worker
session, window = create_agent_session(
    name="fix_tests",
    model="opencode/glm-5-free",
    prompt="Fix tests in tests/unit/infrastructure/test_observation_repository.py",
)

# Monitorear progreso
output = get_agent_output(session, window, lines=100)
```

### Bash Commands

```bash
# Crear sesión
/home/user/fork_agent/.tmux-orchestrator/send-opencode-message.sh fix_tests:0 "Continue fixing tests"

# Ver output
tmux capture-pane -t fix_tests:0 -p | tail -50

# Listar sesiones activas
tmux list-sessions
```

### Orquestación con Tmux

```bash
# Create orchestrator session
tmux new-session -d -s orchestrator -c /home/user/fork_agent

# Launch orchestrator agent
tmux send-keys -t orchestrator "opencode run -m opencode/glm-5-free 'Read .stash/handoff_prompt.md and execute the orchestration workflow.'" Enter

# Monitor
tmux capture-pane -t orchestrator:0 -p | tail -30
```
