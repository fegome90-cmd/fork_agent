# fork_agent - AGENTS.md

> Guía de trabajo para agentes de codificación autónomos.

---

## 🚀 Comandos de Build/Test

```bash
# Setup inicial
uv sync                          # Instalar todas las dependencias
uv sync --all-extras             # Incluir dependencias de desarrollo

# Testing
uv run pytest tests/ -v                          # Todos los tests
uv run pytest tests/unit/infrastructure/ -v      # Tests de un directorio
uv run pytest tests/unit/domain/test_entities.py::TestTerminalResult::test_create_successful_result -v  # Test específico
uv run pytest tests/ --cov=src --cov-report=term-missing  # Con coverage

# Calidad
uv run ruff check src/ tests/     # Linting
uv run ruff format src/ tests/    # Formateo
uv run mypy src/                  # Type checking (strict)

# Pre-commit
uv run pre-commit run --all-files # Ejecutar todos los hooks
```

**⚠️ IMPORTANTE**: Coverage mínimo requerido: **95%**

---

## 📁 Estructura del Proyecto

```
src/
├── domain/           # Entidades inmutables, excepciones del dominio
├── application/      # Casos de uso, servicios, excepciones de aplicación
├── infrastructure/   # DB, config, platform-specific
└── interfaces/       # CLI, adaptadores de entrada/salida

tests/
├── unit/             # Tests unitarios (mirror de src/)
├── integration/      # Tests de integración
└── conftest.py       # Fixtures compartidas
```

---

## 🎨 Estilo de Código

### Imports (orden obligatorio)

```python
# 1. Future annotations (en archivos nuevos)
from __future__ import annotations

# 2. Standard library
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

# 3. Third-party
import pytest
from pydantic import BaseModel, field_validator

# 4. Local imports
from src.domain.entities.terminal import TerminalResult
from src.application.exceptions import RepositoryError
```

### Entidades (Dataclasses inmutables)

```python
from dataclasses import dataclass

@dataclass(frozen=True)  # ← SIEMPRE frozen=True
class TerminalResult:
    success: bool
    output: str
    exit_code: int

    def __post_init__(self) -> None:  # Validación opcional
        if not isinstance(self.success, bool):
            raise TypeError("success debe ser un booleano")
```

### Config (Pydantic frozen)

```python
from pydantic import BaseModel, field_validator

class DatabaseConfig(BaseModel):
    db_path: Path
    busy_timeout_ms: int = 5000

    @field_validator("busy_timeout_ms")
    @classmethod
    def validate_busy_timeout(cls, v: int) -> int:
        if v < 0:
            raise ValueError("busy_timeout_ms must be non-negative")
        return v

    model_config = {"frozen": True}  # ← Inmutable
```

### Type Hints (OBLIGATORIOS)

```python
# ✅ Correcto
def process_data(data: list[str]) -> dict[str, int]:
    ...

def get_item(id: int) -> Item | None:
    ...

# ❌ Incorrecto (mypy strict lo rechazará)
def process_data(data):
    ...
```

### Nombrado

| Elemento | Convención | Ejemplo |
|----------|------------|---------|
| Archivos | `snake_case.py` | `terminal_spawner.py` |
| Clases | `PascalCase` | `TerminalSpawner` |
| Funciones | `snake_case` | `spawn_terminal` |
| Constantes | `UPPER_SNAKE_CASE` | `MAX_RETRIES` |
| Privados | `_leading_underscore` | `_config`, `_connection` |

---

## 🧪 Testing

### Estructura de Test

```python
import pytest
from src.domain.entities.terminal import TerminalResult


class TestTerminalResult:
    """Tests para TerminalResult."""

    def test_create_successful_result(self) -> None:
        result = TerminalResult(
            success=True,
            output="test",
            exit_code=0,
        )

        assert result.success is True
        assert result.output == "test"

    def test_result_immutability(self) -> None:
        result = TerminalResult(success=True, output="", exit_code=0)

        with pytest.raises(Exception):
            result.success = False  # frozen=True previene mutación
```

### Fixtures (conftest.py)

```python
import pytest
from src.domain.entities.terminal import TerminalConfig, PlatformType


@pytest.fixture
def terminal_config_linux() -> TerminalConfig:
    return TerminalConfig(terminal="xterm", platform=PlatformType.LINUX)


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Base de datos temporal para tests."""
    return tmp_path / "test.db"
```

### Naming de Tests

```python
# Patrón: test_<función>_<escenario>
def test_create_config_with_defaults() -> None: ...
def test_create_config_with_custom_values() -> None: ...
def test_config_validates_journal_mode() -> None: ...
```

---

## ⚠️ Manejo de Errores

### Excepciones Personalizadas

```python
class MemoryError(Exception):
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        self.original_exception = original_exception


class RepositoryError(MemoryError):
    pass


class ServiceError(MemoryError):
    pass
```

### Uso

```python
# En repositorios
try:
    cursor.execute("SELECT * FROM observations")
except sqlite3.Error as e:
    raise RepositoryError("Failed to fetch observations", e)

# En servicios
if not observation:
    raise ObservationNotFoundError(f"Observation {id} not found")
```

---

## 🏗️ Patrones de Arquitectura

### Dependency Injection

```python
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    database_config = providers.Singleton(
        DatabaseConfig,
        db_path=config.db_path,
    )

    database_connection = providers.Singleton(
        DatabaseConnection,
        config=database_config,
    )
```

### Context Manager Pattern

```python
class DatabaseConnection:
    __slots__ = ("_config", "_connection")  # Memory optimization

    def __enter__(self) -> sqlite3.Connection:
        self._connection = sqlite3.connect(str(self._config.db_path))
        return self._connection

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self._connection.close()
```

---

## 🚫 Prohibiciones

```python
# ❌ NO usar as any, @ts-ignore, etc.
value = get_value() as any

# ❌ NO mutar argumentos
def process(items: list) -> None:
    items.append("new")  # Prohibido

# ❌ NO usar type: ignore sin justificación
result = dangerous_call()  # type: ignore

# ❌ NO dejar catch vacíos
try:
    do_something()
except:
    pass  # Prohibido

# ❌ NO comentarios innecesarios
x = x + 1  # increment x (eliminar)

# ❌ NO docstrings redundantes
def add(a: int, b: int) -> int:  # tipo ya documentado
    """Add two numbers."""  # Eliminar si código es autoexplicativo
    return a + b
```

---

## ✅ Checklist Pre-Commit

Antes de cada commit, verificar:

1. [ ] `uv run ruff check src/ tests/` - Sin errores
2. [ ] `uv run mypy src/` - Sin errores de tipo
3. [ ] `uv run pytest tests/` - Todos los tests pasan
4. [ ] Coverage >= 95%

---

## 🔧 Configuración de Herramientas

| Herramienta | Config | Umbral |
|-------------|--------|--------|
| mypy | strict mode | 100% typed |
| ruff | py311, line-length 100 | - |
| coverage | fail_under | 95% |
| pytest | -v --tb=short | - |

Ver `pyproject.toml` para configuración completa.
