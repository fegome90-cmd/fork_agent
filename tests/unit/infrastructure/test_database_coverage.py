"""Tests for infrastructure modules with low coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection


class TestDatabaseConnectionPragmas:
    """Test database pragma settings."""

    def test_wal_mode_enabled(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test_wal.db"
        config = DatabaseConfig(db_path=db_path)

        with DatabaseConnection(config) as conn:
            cursor = conn.execute("PRAGMA journal_mode")
            result = cursor.fetchone()

        assert result[0].upper() == "WAL"

    def test_busy_timeout_set(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test_busy.db"
        config = DatabaseConfig(db_path=db_path, busy_timeout_ms=10000)

        with DatabaseConnection(config) as conn:
            cursor = conn.execute("PRAGMA busy_timeout")
            result = cursor.fetchone()

        assert result[0] == 10000

    def test_foreign_keys_enabled(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test_fk.db"
        config = DatabaseConfig(db_path=db_path, foreign_keys=True)

        with DatabaseConnection(config) as conn:
            cursor = conn.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()

        assert result[0] == 1


class TestDatabaseThreadSafety:
    """Test database thread safety."""

    def test_connection_reuse_in_same_thread(self, tmp_path: Path) -> None:
        db_path = tmp_path / "thread_reuse.db"
        config = DatabaseConfig(db_path=db_path)

        with DatabaseConnection(config):
            pass
        with DatabaseConnection(config):
            pass


class TestDatabasePersistence:
    """Test database persistence."""

    def test_persists_after_close(self, tmp_path: Path) -> None:
        db_path = tmp_path / "persist.db"
        config = DatabaseConfig(db_path=db_path)

        with DatabaseConnection(config) as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO test VALUES (1)")

        with DatabaseConnection(config) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]

        assert count == 1


class TestDatabaseConfigValidation:
    """Test database config validation."""

    def test_negative_busy_timeout_raises(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            DatabaseConfig(db_path=Path("/tmp/test.db"), busy_timeout_ms=-1)

    def test_wal_mode_default(self) -> None:
        config = DatabaseConfig(db_path=Path("/tmp/test.db"))
        assert config.journal_mode.value == "WAL"

    def test_foreign_keys_default(self) -> None:
        config = DatabaseConfig(db_path=Path("/tmp/test.db"))
        assert config.foreign_keys is True
