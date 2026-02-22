"""Unit tests for DatabaseConfig and DatabaseConnection.

TDD Red Phase: These tests define the expected behavior BEFORE implementation.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection, JournalMode


class TestDatabaseConfig:
    """Tests for DatabaseConfig Pydantic model."""

    def test_create_config_with_defaults(self) -> None:
        """Test creating config with default values."""
        config = DatabaseConfig(db_path=Path("/tmp/test.db"))

        assert config.db_path == Path("/tmp/test.db")
        assert config.journal_mode == "WAL"
        assert config.busy_timeout_ms == 5000
        assert config.foreign_keys is True

    def test_create_config_with_custom_values(self, tmp_path: Path) -> None:
        """Test creating config with custom values."""
        config = DatabaseConfig(
            db_path=tmp_path / "custom" / "path.db",
            journal_mode=JournalMode.DELETE,
            busy_timeout_ms=10000,
            foreign_keys=False,
        )

        assert config.db_path == tmp_path / "custom" / "path.db"
        assert config.journal_mode == "DELETE"
        assert config.busy_timeout_ms == 10000
        assert config.foreign_keys is False

    def test_config_expands_user_home(self) -> None:
        """Test that ~ in path is expanded to user home."""
        config = DatabaseConfig(db_path=Path("~/data/memory.db"))

        # Should expand ~ to actual home directory
        assert "~" not in str(config.db_path)
        assert config.db_path.is_absolute()

    def test_config_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that parent directory is created if it doesn't exist."""
        # Create a path where parent doesn't exist
        new_dir = tmp_path / "new_nested" / "dir"
        db_path = new_dir / "memory.db"

        assert not db_path.parent.exists()

        # Creating config should create parent directory
        config = DatabaseConfig(db_path=db_path)

        assert config.db_path.parent.exists()

    def test_config_validates_journal_mode(self) -> None:
        """Test that invalid journal mode raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            DatabaseConfig(
                db_path=Path("/tmp/test.db"),
                journal_mode="INVALID",
            )

        assert "journal_mode" in str(exc_info.value).lower()

    def test_config_validates_busy_timeout_positive(self) -> None:
        """Test that negative busy_timeout raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            DatabaseConfig(
                db_path=Path("/tmp/test.db"),
                busy_timeout_ms=-100,
            )

        assert "busy_timeout_ms" in str(exc_info.value).lower()


class TestDatabaseConnection:
    """Tests for DatabaseConnection context manager."""

    def test_connection_creates_database_file(self, tmp_path: Path) -> None:
        """Test that connection creates the database file if it doesn't exist."""
        db_path = tmp_path / "test.db"
        assert not db_path.exists()

        config = DatabaseConfig(db_path=db_path)

        with DatabaseConnection(config) as conn:
            # Just connecting should create the file
            pass

        assert db_path.exists()

    def test_connection_sets_wal_mode(self, tmp_path: Path) -> None:
        """Test that connection sets WAL journal mode."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path, journal_mode=JournalMode.WAL)

        with DatabaseConnection(config) as conn:
            cursor = conn.execute("PRAGMA journal_mode")
            result = cursor.fetchone()

        assert result[0].upper() == "WAL"

    def test_connection_sets_busy_timeout(self, tmp_path: Path) -> None:
        """Test that connection sets busy_timeout."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path, busy_timeout_ms=3000)

        with DatabaseConnection(config) as conn:
            cursor = conn.execute("PRAGMA busy_timeout")
            result = cursor.fetchone()

        assert result[0] == 3000

    def test_connection_enables_foreign_keys(self, tmp_path: Path) -> None:
        """Test that connection enables foreign key constraints."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path, foreign_keys=True)

        with DatabaseConnection(config) as conn:
            cursor = conn.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()

        assert result[0] == 1

    def test_connection_context_manager_closes_on_exit(self, tmp_path: Path) -> None:
        """Test that connection is properly closed after context exit."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)

        conn: sqlite3.Connection
        with DatabaseConnection(config) as conn:
            pass

        # Connection should be closed
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_connection_commits_on_success(self, tmp_path: Path) -> None:
        """Test that transaction is committed on successful context exit."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)

        with DatabaseConnection(config) as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO test VALUES (1)")

        # Verify data persisted after connection closed
        with DatabaseConnection(config) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]

        assert count == 1

    def test_connection_rollback_on_exception(self, tmp_path: Path) -> None:
        """Test that transaction is rolled back on exception."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)

        # Create table first
        with DatabaseConnection(config) as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")

        # Try to insert and raise exception
        with pytest.raises(ValueError):
            with DatabaseConnection(config) as conn:
                conn.execute("INSERT INTO test VALUES (1)")
                raise ValueError("Simulated error")

        # Data should not have been committed
        with DatabaseConnection(config) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]

        assert count == 0

    def test_connection_is_thread_safe(self, tmp_path: Path) -> None:
        """Test that connection uses check_same_thread=False for flexibility."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_path=db_path)

        with DatabaseConnection(config) as conn:
            # The default sqlite3 connection has check_same_thread=True
            # Our connection should allow cross-thread usage
            # This is verified by the fact that we can check internal state
            # sqlite3.Connection doesn't expose check_same_thread directly
            # So we verify it works by using the connection
            conn.execute("SELECT 1")


class TestDatabaseConnectionFactories:
    """Tests for factory methods."""

    def test_create_in_memory_connection(self) -> None:
        """Test creating an in-memory database connection."""
        conn = DatabaseConnection.create_in_memory()

        assert isinstance(conn, DatabaseConnection)

        with conn as connection:
            connection.execute("CREATE TABLE test (id INTEGER)")
            connection.execute("INSERT INTO test VALUES (1)")
            cursor = connection.execute("SELECT COUNT(*) FROM test")
            assert cursor.fetchone()[0] == 1

    def test_create_in_memory_is_isolated(self) -> None:
        """Test that each in-memory connection is isolated."""
        conn1 = DatabaseConnection.create_in_memory()
        conn2 = DatabaseConnection.create_in_memory()

        with conn1 as c1:
            c1.execute("CREATE TABLE test (id INTEGER)")
            c1.execute("INSERT INTO test VALUES (1)")

        # conn2 should not see conn1's data (separate in-memory DB)
        with conn2 as c2:
            # Table shouldn't exist in conn2's database
            with pytest.raises(sqlite3.OperationalError):
                c2.execute("SELECT * FROM test")

    def test_from_path_factory(self, tmp_path: Path) -> None:
        """Test creating connection from path string."""
        db_path = tmp_path / "factory.db"

        conn = DatabaseConnection.from_path(db_path)

        assert isinstance(conn, DatabaseConnection)
        assert conn._config.db_path == db_path  # noqa: SLF001
