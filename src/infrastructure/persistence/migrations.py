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
    """Base exception for migration errors."""

    pass


class MigrationLoadError(MigrationError):
    """Raised when a migration file cannot be loaded."""

    pass


class MigrationAlreadyAppliedError(MigrationError):
    """Raised when attempting to apply an already-applied migration."""

    pass


@dataclass(frozen=True)
class Migration:
    """Represents a single database migration."""

    version: int
    name: str
    sql: str


class MigrationRunner:
    """Executes and tracks database migrations."""

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
