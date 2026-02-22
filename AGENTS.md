# fork_agent - AGENTS.md

> Guía para agentes de codificación autónomos.

---

## OVERVIEW

CLI de gestión de memoria para agentes AI. Python 3.11+ con arquitectura DDD (Puertos y Adaptadores), Typer para CLI, SQLite para persistencia.

**Commit:** 2026-02-22 | **Stack:** Python 3.11, Typer, SQLite, Pydantic

---

## STRUCTURE

```
src/
├── domain/           # Entidades inmutables, Protocol (ports)
├── application/      # Services, Use Cases, excepciones
├── infrastructure/   # DB, DI Container, platform-specific
└── interfaces/       # CLI (Typer), adaptadores

tests/
├── unit/             # Mirror de src/
├── integration/      # Tests de integración
└── e2e/              # End-to-end (sufijo _e2e.py)
```

---

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Añadir comando CLI | `src/interfaces/cli/commands/` |
| Modificar entidad | `src/domain/entities/` |
| Añadir servicio | `src/application/services/` |
| Cambiar DB schema | `src/infrastructure/persistence/` |
| Nuevo repository | `src/domain/ports/` + implementación en infrastructure |
| Tests unitarios | `tests/unit/` (mirror de src/) |

---

## ENTRY POINTS

- **CLI:** `memory` → `src.interfaces.cli.main:app` (pyproject.toml console_scripts)
- **Comandos:** save, search, list, get, delete (en `src/interfaces/cli/commands/`)
- **Workflow:** outline, execute, verify, ship, status (en `src/interfaces/cli/commands/workflow.py`)
- **Schedule:** add, list, show, cancel (en `src/interfaces/cli/commands/schedule.py`)
- **Workspace:** create, list, enter, detect (en `src/interfaces/cli/workspace_commands.py`)

---

## CONVENTIONS

### Imports (orden obligatorio)
1. `from __future__ import annotations`
2. Standard library
3. Third-party
4. Local (`from src.*`)

### Entidades
```python
@dataclass(frozen=True)  # SIEMPRE frozen=True
class Observation:
    id: str
    content: str
```

### Config (Pydantic)
```python
class DatabaseConfig(BaseModel):
    db_path: Path
    model_config = {"frozen": True}  # Inmutable
```

### Type Hints
- OBLIGATORIOS en todas las funciones
- Usar `X | None` en lugar de `Optional[X]`

### Nombrado
- Archivos: `snake_case.py`
- Clases: `PascalCase`
- Funciones: `snake_case`
- Constantes: `UPPER_SNAKE_CASE`

---

## ANTI-PATTERNS (ESTE PROYECTO)

```python
# ❌ NO usar
as any, @ts-ignore, type: ignore
value = get_value() as any

# ❌ NO mutar argumentos
def process(items: list) -> None:
    items.append("new")

# ❌ NO catch vacíos
try:
    do_something()
except:
    pass

# ❌ NO docstrings redundantes
def add(a: int, b: int) -> int:
    """Add two numbers."""  # Eliminar
    return a + b
```

---

## COMMANDS

```bash
# Setup
uv sync --all-extras

# Testing
uv run pytest tests/ -v
uv run pytest tests/unit/domain/ -v
uv run pytest tests/ --cov=src --cov-report=term-missing

# Calidad
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy src/

# Pre-commit
uv run pre-commit run --all-files
```

---

## TESTING CONVENTIONS

- **Estructura:** `tests/unit/`, `tests/integration/`, `tests/e2e/`
- **Naming:** `test_*.py`, funciones `test_*`
- **E2E suffix:** `_e2e.py` para end-to-end
- **Fixtures:** `tests/conftest.py` (comunes), `tests/e2e/conftest.py` (E2E)

---

## TOOL CONFIG

| Herramienta | Config | Valor |
|-------------|--------|-------|
| mypy | strict mode | 100% typed |
| ruff | py311, line-length 100 | - |
| coverage | fail_under | **95%** |
| pytest | -v --tb=short | - |

Ver `pyproject.toml` para configuración completa.

---

## ARCHITECTURE NOTES

- **DDD/Clean Architecture:** domain → application → infrastructure → interfaces
- **Dependency Injection:** `src/infrastructure/persistence/container.py`
- **MemoryService:** Fachada de lógica de negocio (`src/application/services/`)
- **Repository Pattern:** Protocol en `domain/ports/`, implementación en `infrastructure/`
- **Orchestration:** Eventos, acciones y hooks (`src/application/services/orchestration/`)
- **Workflow:** Estado persistente (`src/application/services/workflow/`)
