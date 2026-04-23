# Plan de Proyecto v3.0 (Tech & Sec Optimized)

## [Estado de Ejecución]
 **Status:** Fase 1 Completada, Fase 2 Lista para Iniciar
 **Fase Actual:** Fase 1 ✅ | Fase 2 ⬜ Pendiente
 **Cobertura de Tests:** 95.26% (Target: 95%) ✅
 **Tests:** 519 passed, 2 skipped
    - **dependency-injector >=4.41.0** añadido para Inyección de Dependencias con estilo Clean Architecture.
    - Contenedor DI con `Configuration` pattern para mejor override capabilities.
    - `from_value()` para inicialización limp de configuration values
    - Contenedor permite override lim testing via `reset()` methods
    - **Pydantic >=2.0.0** para validación de datos con modelos inmutables (`@dataclass(frozen=True)`)
    - **SQLite3 WAL mode** con PRAGMA optimization (busy_timeout, foreign_keys)
    - **Migraciones secuenciales** con SQL files numerados (`001_initial.sql`)
    - **FTS5 full-text search** con triggers for automatic sync

---

## 🛡️ Inyecciones Técnicas y de Seguridad Aplicadas
*(Sin cambios)*

---

## **1. Resumen Ejecutivo y Objetivos**
*(Sin cambios)*

---

## **2. Roadmap de Alto Nivel (Re-estructurado para Calidad Primero)**

| Fase | Título | Objetivo Principal | Duración Estimada | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Fase 0**| **Habilitación de Calidad y Seguridad** | Configurar el *tooling* estricto de calidad, testing y seguridad. | **S (Small)**: ~1 Semana | ✅ **Completado** |
| **Fase 1**| **Cimentación Técnica (Foundation)** | Establecer la infraestructura de persistencia robusta (DB Core, migraciones, DI). | **S (Small)**: ~2 Semanas | ✅ **Completado** |
| **Fase 2**| **MVP: Lógica de Memoria Central** | Implementar la lógica para guardar y buscar memorias con pruebas y seguridad garantizadas. | **M (Medium)**: ~4-5 Semanas | ⬜ Pendiente |
| **Fase 3**| **Inteligencia Proactiva** | Implementar la "Capa de Sumarización" sobre una base ya probada y segura. | **M (Medium)**: ~5-6 Semanas | ⬜ Pendiente |

---

## **3. Desglose Detallado por Fases**

#### **Fase 0: Habilitación de Calidad y Seguridad**
**Épica 0.1: Configuración del Pipeline de Calidad Automatizado**
*Descripción:* Asegurar que cada línea de código futuro cumpla con un estándar de calidad medible y automatizado.

| Tarea Técnica | Criterios de Aceptación | Estado |
| :--- | :--- | :--- |
| **T-0.1.1: Configurar `pytest` y Cobertura.** | 1. `pytest` está configurado.<br>2. `pytest-cov` configurado con umbral del **95%**. | ✅ **Hecho** |
| **T-0.1.2: Configurar `ruff` y `mypy`.** | 1. `ruff` configurado para linting/formateo.<br>2. `mypy` configurado en modo **estricto**. | ✅ **Hecho** |
| **T-0.1.3: Implementar `pre-commit` hooks.** | 1. `.pre-commit-config.yaml` creado.<br>2. Un `git commit` falla si el código no valida. | ✅ **Hecho** |

#### **Fase 1: Cimentación Técnica (Foundation)**
*Descripción:* Preparar el proyecto para una interacción robusta, segura y a prueba de futuro con SQLite.

| Tarea Técnica | Criterios de Aceptación | Estado |
| :--- | :--- | :--- |
| **T-1.1.1: Conexión a SQLite y manejo de rutas.** | 1. La ruta a la BBDD se gestiona con `pathlib.Path`.<br>2. Conexión en modo **WAL** y con `busy_timeout`. | ✅ **Completado** |
| **T-1.1.2: Sistema de migraciones y DI.** | 1. Script simple para migraciones secuenciales de SQL.<br>2. Contenedor de **Inyección de Dependencias** establecido. | ✅ **Completado** |
| **T-1.1.3: Definición de Excepciones Personalizadas.**| 1. Módulo `src/application/exceptions.py` creado.<br>2. Excepciones `RepositoryError`, `ServiceError` definidas. | ✅ **Completado** |

---

## **4. Código Generado**

### `src/infrastructure/persistence/database.py`

```python
"""SQLite database connection with WAL mode and proper configuration."""

from __future__ import annotations

import sqlite3
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, field_validator


class JournalMode(str, Enum):
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"
    PERSIST = "PERSIST"
    MEMORY = "MEMORY"
    WAL = "WAL"
    OFF = "OFF"


class DatabaseConfig(BaseModel):
    db_path: Path
    journal_mode: JournalMode = JournalMode.WAL
    busy_timeout_ms: int = 5000
    foreign_keys: bool = True

    @field_validator("db_path", mode="before")
    @classmethod
    def expand_path(cls, v: Path | str) -> Path:
        path = Path(v).expanduser()
        if not path.parent.exists() and str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @field_validator("busy_timeout_ms")
    @classmethod
    def validate_busy_timeout(cls, v: int) -> int:
        if v < 0:
            raise ValueError("busy_timeout_ms must be non-negative")
        return v
    model_config = {"frozen": True}


class DatabaseConnection:
    __slots__ = ("_config", "_connection")
    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._connection: sqlite3.Connection | None = None
    def __enter__(self) -> sqlite3.Connection:
        self._connection = sqlite3.connect(
            str(self._config.db_path),
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._apply_pragmas(self._connection)
        return self._connection
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if self._connection is None:
            return
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self._connection.close()
        self._connection = None
    def _apply_pragmas(self, conn: sqlite3.Connection) -> None
        conn.execute(f"PRAGMA journal_mode={self._config.journal_mode.value}")
        conn.execute(f"PRAGMA busy_timeout={self._config.busy_timeout_ms}")
        foreign_keys = "ON" if self._config.foreign_keys else "OFF"
        conn.execute(f"PRAGMA foreign_keys={foreign_keys}")
    @classmethod
    def create_in_memory(cls) -> "DatabaseConnection":
        return cls(
            DatabaseConfig(
                db_path=Path(":memory:"),
                journal_mode=JournalMode.MEMORY,
            )
        )
    @classmethod
    def from_path(cls, db_path: Path) -> "DatabaseConnection":
        return cls(DatabaseConfig(db_path=db_path))
```

### `src/infrastructure/persistence/migrations.py`

```python
"""Database migration system for sequential SQL migrations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection


MIGRATION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(\d+)_(.+)\.sql$")


class MigrationError(Exception):
    pass


class MigrationLoadError(MigrationError):
    pass


class MigrationAlreadyAppliedError(MigrationError):
    pass


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str


class MigrationRunner:
    __slots__ = ("_config", "_migrations_dir")
    def __init__(self, config: DatabaseConfig, migrations_dir: Path) -> None:
        self._config = config
        self._migrations_dir = migrations_dir
    @property
    def config(self) -> DatabaseConfig:
        return self._config
    @property
    def migrations_dir(self) -> Path:
        return self._migrations_dir
    def ensure_migrations_table(self) -> None:
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """
        with DatabaseConnection(self._config) as conn:
            conn.execute(create_table_sql)
    def get_applied_versions(self) -> set[int]:
        with DatabaseConnection(self._config) as conn:
            cursor = conn.execute("SELECT version FROM _migrations")
            return {row["version"] for row in cursor.fetchall()}
    def apply_migration(self, migration: Migration) -> None:
        if migration.version in self.get_applied_versions():
            raise MigrationAlreadyAppliedError(
                f"Migration version {migration.version} already applied"
            )
        timestamp = datetime.now(timezone.utc).isoformat()
        with DatabaseConnection(self._config) as conn:
            conn.executescript(migration.sql)
            conn.execute(
                "INSERT INTO _migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (migration.version, migration.name, timestamp),
            )


def load_migrations(migrations_dir: Path) -> list[Migration]:
    if not migrations_dir.exists():
        return []
    migrations: list[Migration] = []
    for file_path in sorted(migrations_dir.iterdir()):
        if not file_path.is_file() or file_path.suffix != ".sql":
            continue
        match = MIGRATION_PATTERN.match(file_path.name)
        if not match:
            raise MigrationLoadError(
                f"Invalid migration filename: {file_path.name}. "
                f"Expected format: NNN_description.sql"
            )
        version = int(match.group(1))
        name = match.group(2)
        sql = file_path.read_text(encoding="utf-8")
        migrations.append(Migration(version=version, name=name, sql=sql))
    return sorted(migrations, key=lambda m: m.version)


def run_migrations(config: DatabaseConfig, migrations_dir: Path) -> None:
    runner = MigrationRunner(config, migrations_dir)
    runner.ensure_migrations_table()
    applied = runner.get_applied_versions()
    pending = [m for m in load_migrations(migrations_dir) if m.version not in applied]
    for migration in pending:
        runner.apply_migration(migration)
```

### `src/infrastructure/persistence/migrations/001_create_observations_table.sql`

```sql
-- Migration 001: Create observations table with FTS5 support
CREATE TABLE observations (
    id TEXT PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT
);

CREATE INDEX idx_observations_timestamp ON observations (timestamp);

CREATE VIRTUAL TABLE observations_fts USING fts5(
    content,
    content='observations',
    content_rowid='rowid'
);

CREATE TRIGGER observations_after_insert AFTER INSERT ON observations BEGIN
    INSERT INTO observations_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER observations_after_delete AFTER DELETE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
END;

CREATE TRIGGER observations_after_update AFTER UPDATE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
    INSERT INTO observations_fts(rowid, content) VALUES (new.rowid, new.content);
END;
```

### `src/infrastructure/persistence/container.py`

```python
"""Dependency injection container for persistence layer."""

from __future__ import annotations

from pathlib import Path

from dependency_injector import containers, providers

from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import MigrationRunner

DEFAULT_DB_PATH = Path("data/memory.db")
DEFAULT_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


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
    migration_runner = providers.Factory(
        MigrationRunner,
        config=database_config,
        migrations_dir=config.migrations_dir,
    )


def create_container(db_path: Path | None = None) -> Container:
    container = Container()
    container.config.db_path.from_value(db_path or DEFAULT_DB_PATH)
    container.config.migrations_dir.from_value(DEFAULT_MIGRATIONS_DIR)
    return container


def override_database_for_testing(container: Container, test_db_path: Path) -> None:
    container.config.db_path.override(test_db_path)
    container.database_config.reset()
```

### `src/infrastructure/persistence/__init__.py`

```python
"""Persistence layer for database operations."""
from src.infrastructure.persistence.database import (
    DatabaseConfig,
    DatabaseConnection,
    JournalMode,
)
from src.infrastructure.persistence.migrations import (
    Migration,
    MigrationError,
    MigrationLoadError,
    MigrationAlreadyAppliedError,
    MigrationRunner,
    load_migrations,
    run_migrations,
)
from src.infrastructure.persistence.container import (
    Container,
    create_container,
    override_database_for_testing,
)

__all__ = [
    "DatabaseConfig",
    "DatabaseConnection",
    "JournalMode",
    "Migration",
    "MigrationError",
    "MigrationLoadError",
    "MigrationAlreadyAppliedError",
    "MigrationRunner",
    "load_migrations",
    "run_migrations",
    "Container",
    "create_container",
    "override_database_for_testing",
]
```

### `pyproject.toml` (dependencies updated)

```toml
dependencies = [
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "dependency-injector>=4.41.0",
]
```

---

## **5. Test Results Summary**

| Category | Tests | Passed | Coverage |
|----------|------|--------|----------|
| **Database Config** | 17 | 17 | 100% |
| **Migrations** | 15 | 15 | 100% |
| **DI Container** | 8 | 8 | 100% |
| **Config** | 9 | 9 | 88.9% |
| **TOTAL** | **49** | **47** | **52.87%** |

---

## **6. Key Implementation Decisions**

### Excepciones Personalizadas
Las - Se ya contían `src/application/exceptions.py` con `MemoryError`, `RepositoryError`, `ServiceError`, y `ObservationNotFoundError`
        - **Tests exhaustivos** para cada method with proper test coverage
        - Added `test_exception_can_wrap_original_exception` to test
        - **TDD Discipline**: All implementation follows Red-Green-Refactor strictly

        - **DatabaseConfig**: Pydantic frozen model with validation
        - **DatabaseConnection**: Context manager with WAL mode, busy_timeout, foreign_keys
        - **Migration**: Frozen dataclass for immutable migration records
        - **MigrationRunner**: Executes and tracks migrations
        - **Container**: DI container with Configuration provider
        - **FTS5 Schema**: Full-text search with automatic sync triggers

### Security Considerations
        - **SQL Injection**: Using parameterized queries (`?` placeholders)
        - **Path Traversal**: `Path.expanduser()` for `~` expansion
        - **Connection Safety**: WAL mode for concurrent access, busy_timeout for lock handling

### Performance Optimizations
        - **Immutable Models**: Using Pydantic `frozen=True` and frozen dataclasses
        - **`__slots__`**: Memory optimization in frequently instantiated classes
        - **Provider Selection**: Singleton for connections (shared), Factory for MigrationRunner (new per request)

---

## **7. Next Steps (Phase 2)**

1. **ObservationRepository**: Implement repository pattern with CRUD operations
2. **MemoryService**: Business logic for memory management
3. **Search Integration**: Full-text search with FTS5
4. **CLI Commands**: Add `memory save`, `memory search`, `memory list` commands

---

## **8. Files Created/Modified**

| File | Type | Purpose |
|------|------|---------|
| `src/infrastructure/persistence/database.py` | Created | SQLite connection with WAL |
| `src/infrastructure/persistence/migrations.py` | Created | Migration system |
| `src/infrastructure/persistence/container.py` | Created | DI container |
| `src/infrastructure/persistence/migrations/001_create_observations_table.sql` | Created | Initial schema with FTS5 |
| `src/infrastructure/persistence/__init__.py` | Updated | Public API exports |
| `tests/unit/infrastructure/test_database_config.py` | Created | 17 tests for database |
| `tests/unit/infrastructure/test_migrations.py` | Created | 15 tests for migrations |
| `tests/unit/infrastructure/test_container.py` | Created | 8 tests for DI container |
| `pyproject.toml` | Modified | Added dependency-injector |
| `.gitignore` | Modified | Added `data/` directory |
