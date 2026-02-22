"""SQLite database connection with WAL mode and proper configuration."""

from __future__ import annotations

import sqlite3
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, field_validator


class JournalMode(str, Enum):
    """Valid SQLite journal modes."""

    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"
    PERSIST = "PERSIST"
    MEMORY = "MEMORY"
    WAL = "WAL"
    OFF = "OFF"


class DatabaseConfig(BaseModel):
    """Configuration for SQLite database connection.

    Attributes:
        db_path: Path to the SQLite database file.
        journal_mode: SQLite journal mode (default: WAL).
        busy_timeout_ms: Busy timeout in milliseconds (default: 5000).
        foreign_keys: Enable foreign key constraints (default: True).
    """

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
    """Context manager for SQLite database connections.

    Provides automatic commit/rollback, WAL mode, and proper configuration.
    """

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

    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
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
