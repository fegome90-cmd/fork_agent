"""Unit tests for database migration system.

TDD Red Phase: These tests define the expected behavior BEFORE implementation.
"""

from pathlib import Path

import pytest

from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import Migration, MigrationRunner


class TestMigration:
    """Tests for Migration dataclass."""

    def test_create_migration(self) -> None:
        """Test creating a migration."""
        migration = Migration(
            version=1,
            name="create_observations_table",
            sql="CREATE TABLE observations (id TEXT PRIMARY KEY);",
        )

        assert migration.version == 1
        assert migration.name == "create_observations_table"
        assert "CREATE TABLE" in migration.sql

    def test_migration_is_immutable(self) -> None:
        """Test that Migration is immutable (frozen dataclass)."""
        from dataclasses import FrozenInstanceError

        migration = Migration(
            version=1,
            name="test",
            sql="SELECT 1;",
        )

        with pytest.raises(FrozenInstanceError):
            migration.version = 2


class TestMigrationRunner:
    """Tests for MigrationRunner."""

    def test_create_migration_runner(self, tmp_path: Path) -> None:
        """Test creating a migration runner."""
        db_path = tmp_path / "test.db"
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        config = DatabaseConfig(db_path=db_path)
        runner = MigrationRunner(config=config, migrations_dir=migrations_dir)

        assert runner.config.db_path == db_path
        assert runner.migrations_dir == migrations_dir

    def test_ensure_migrations_table(self, tmp_path: Path) -> None:
        """Test that migrations table is created on first run."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        runner = MigrationRunner(config=config, migrations_dir=tmp_path / "migrations")

        runner.ensure_migrations_table()

        with DatabaseConnection(config) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'"
            )
            result = cursor.fetchone()

        assert result is not None

    def test_get_applied_migrations_empty(self, tmp_path: Path) -> None:
        """Test getting applied migrations when none have been applied."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        runner = MigrationRunner(config=config, migrations_dir=tmp_path / "migrations")

        runner.ensure_migrations_table()
        applied = runner.get_applied_versions()

        assert applied == set()

    def test_apply_single_migration(self, tmp_path: Path) -> None:
        """Test applying a single migration."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        runner = MigrationRunner(config=config, migrations_dir=tmp_path / "migrations")

        migration = Migration(
            version=1,
            name="create_test_table",
            sql="CREATE TABLE test_table (id INTEGER PRIMARY KEY);",
        )

        runner.ensure_migrations_table()
        runner.apply_migration(migration)

        applied = runner.get_applied_versions()
        assert 1 in applied

        with DatabaseConnection(config) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
            )
            result = cursor.fetchone()

        assert result is not None

    def test_migration_records_timestamp(self, tmp_path: Path) -> None:
        """Test that migration records include timestamp."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        runner = MigrationRunner(config=config, migrations_dir=tmp_path / "migrations")

        migration = Migration(version=1, name="test", sql="SELECT 1;")

        runner.ensure_migrations_table()
        runner.apply_migration(migration)

        with DatabaseConnection(config) as conn:
            cursor = conn.execute(
                "SELECT version, name, applied_at FROM _migrations WHERE version = 1"
            )
            row = cursor.fetchone()

        assert row is not None
        assert row["version"] == 1
        assert row["name"] == "test"
        assert row["applied_at"] is not None

    def test_cannot_apply_same_migration_twice(self, tmp_path: Path) -> None:
        """Test that the same migration cannot be applied twice."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)
        runner = MigrationRunner(config=config, migrations_dir=tmp_path / "migrations")

        migration = Migration(version=1, name="test", sql="SELECT 1;")

        runner.ensure_migrations_table()
        runner.apply_migration(migration)

        from src.infrastructure.persistence.migrations import MigrationAlreadyAppliedError

        with pytest.raises(MigrationAlreadyAppliedError):
            runner.apply_migration(migration)


class TestMigrationLoader:
    """Tests for loading migrations from files."""

    def test_load_migrations_from_directory(self, tmp_path: Path) -> None:
        """Test loading migration files from directory."""
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        (migrations_dir / "001_initial.sql").write_text("CREATE TABLE test1 (id INTEGER);")
        (migrations_dir / "002_add_column.sql").write_text(
            "ALTER TABLE test1 ADD COLUMN name TEXT;"
        )

        from src.infrastructure.persistence.migrations import load_migrations

        migrations = load_migrations(migrations_dir)

        assert len(migrations) == 2
        assert migrations[0].version == 1
        assert migrations[0].name == "initial"
        assert migrations[1].version == 2
        assert migrations[1].name == "add_column"

    def test_migrations_sorted_by_version(self, tmp_path: Path) -> None:
        """Test that migrations are sorted by version number."""
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        (migrations_dir / "003_third.sql").write_text("SELECT 3;")
        (migrations_dir / "001_first.sql").write_text("SELECT 1;")
        (migrations_dir / "002_second.sql").write_text("SELECT 2;")

        from src.infrastructure.persistence.migrations import load_migrations

        migrations = load_migrations(migrations_dir)

        assert migrations[0].version == 1
        assert migrations[1].version == 2
        assert migrations[2].version == 3

    def test_skip_non_sql_files(self, tmp_path: Path) -> None:
        """Test that non-SQL files are skipped."""
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        (migrations_dir / "001_valid.sql").write_text("SELECT 1;")
        (migrations_dir / "README.md").write_text("# Migrations")
        (migrations_dir / "002_valid.sql").write_text("SELECT 2;")

        from src.infrastructure.persistence.migrations import load_migrations

        migrations = load_migrations(migrations_dir)

        assert len(migrations) == 2

    def test_invalid_filename_format_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid filename format raises error."""
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        (migrations_dir / "invalid_name.sql").write_text("SELECT 1;")

        from src.infrastructure.persistence.migrations import MigrationLoadError, load_migrations

        with pytest.raises(MigrationLoadError):
            load_migrations(migrations_dir)


class TestRunPendingMigrations:
    """Tests for running pending migrations."""

    def test_run_pending_migrations(self, tmp_path: Path) -> None:
        """Test running pending migrations."""
        db_path = tmp_path / "test.db"
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        (migrations_dir / "001_create_table.sql").write_text(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);"
        )
        (migrations_dir / "002_insert_data.sql").write_text(
            "INSERT INTO items (id, name) VALUES (1, 'test');"
        )

        config = DatabaseConfig(db_path=db_path)
        from src.infrastructure.persistence.migrations import run_migrations

        run_migrations(config, migrations_dir)

        with DatabaseConnection(config) as conn:
            cursor = conn.execute("SELECT name FROM items WHERE id = 1")
            row = cursor.fetchone()

        assert row is not None
        assert row["name"] == "test"

    def test_only_pending_migrations_are_applied(self, tmp_path: Path) -> None:
        """Test that only pending migrations are applied."""
        db_path = tmp_path / "test.db"
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        (migrations_dir / "001_first.sql").write_text("CREATE TABLE test (id INTEGER PRIMARY KEY);")

        config = DatabaseConfig(db_path=db_path)
        from src.infrastructure.persistence.migrations import (
            MigrationRunner,
            run_migrations,
        )

        run_migrations(config, migrations_dir)

        (migrations_dir / "002_second.sql").write_text("ALTER TABLE test ADD COLUMN name TEXT;")

        run_migrations(config, migrations_dir)

        runner = MigrationRunner(config, migrations_dir)
        runner.ensure_migrations_table()
        applied = runner.get_applied_versions()

        assert applied == {1, 2}

    def test_empty_migrations_dir(self, tmp_path: Path) -> None:
        """Test running with empty migrations directory."""
        db_path = tmp_path / "test.db"
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        config = DatabaseConfig(db_path=db_path)
        from src.infrastructure.persistence.migrations import run_migrations

        run_migrations(config, migrations_dir)

        runner = MigrationRunner(config, migrations_dir)
        runner.ensure_migrations_table()
        applied = runner.get_applied_versions()

        assert applied == set()

    def test_load_migrations_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test that nonexistent directory returns empty list."""
        from src.infrastructure.persistence.migrations import load_migrations

        nonexistent = tmp_path / "does_not_exist"
        result = load_migrations(nonexistent)

        assert result == []

    def test_run_migrations_idempotent_under_race(self, tmp_path: Path) -> None:
        """BUG-14: Concurrent run_migrations calls don't raise errors.

        Simulates a race where another process already applied a migration
        between the check and apply steps.
        """
        db_path = tmp_path / "test.db"
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()

        (migrations_dir / "001_create_table.sql").write_text(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);"
        )

        config = DatabaseConfig(db_path=db_path)
        from src.infrastructure.persistence.migrations import (
            MigrationRunner,
            run_migrations,
        )

        # First run succeeds
        run_migrations(config, migrations_dir)

        # Simulate race: manually apply the migration tracking
        # (it's already applied, but add another pending one)
        (migrations_dir / "002_add_col.sql").write_text(
            "ALTER TABLE items ADD COLUMN extra TEXT;"
        )

        # Pre-apply migration 002 tracking to simulate concurrent process
        runner = MigrationRunner(config, migrations_dir)
        runner.ensure_migrations_table()
        with DatabaseConnection(config) as conn:
            conn.execute(
                "INSERT INTO _migrations (version, name, applied_at) VALUES (2, 'add_col', '2026-01-01T00:00:00')"
            )

        # Second run should NOT raise MigrationAlreadyAppliedError
        run_migrations(config, migrations_dir)

        runner2 = MigrationRunner(config, migrations_dir)
        applied = runner2.get_applied_versions()
        assert applied == {1, 2}
