"""SQLite database connection with WAL mode and proper configuration."""

from __future__ import annotations

import contextlib
import sqlite3
import threading
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, field_validator


_thread_local = threading.local()


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
    """Thread-safe SQLite database connection using thread-local storage.

    Each thread gets its own connection, ensuring thread safety while
    maintaining SQLite's check_same_thread=False for performance with WAL mode.
    For in-memory databases, each context manager creates a new connection
    to maintain isolation between instances.
    """

    __slots__ = ("_config", "_is_in_memory", "_local_conn")

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._is_in_memory = str(config.db_path) == ":memory:"
        self._local_conn: sqlite3.Connection | None = None

    def _get_connection_key(self) -> str:
        return f"db_connection_{self._config.db_path}"

    def __enter__(self) -> sqlite3.Connection:
        key = self._get_connection_key()
        if self._is_in_memory:
            # In-memory: create new connection, track locally for __exit__
            conn = sqlite3.connect(
                str(self._config.db_path),
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            self._apply_pragmas(conn)
            self._local_conn = conn
            return conn
        # File-backed: use thread-local cache
        if not hasattr(_thread_local, key):
            conn = sqlite3.connect(
                str(self._config.db_path),
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            self._apply_pragmas(conn)
            setattr(_thread_local, key, conn)
        return getattr(_thread_local, key)  # type: ignore[no-any-return]

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if self._is_in_memory:
            # In-memory: commit/close the local connection
            conn = self._local_conn
            self._local_conn = None
            if conn is None:
                return
            if exc_type is None:
                conn.commit()
            else:
                conn.rollback()
            with contextlib.suppress(Exception):
                conn.close()
            return

        # File-backed: commit but keep cached connection
        key = self._get_connection_key()
        conn = getattr(_thread_local, key, None)
        if conn is None:
            return
        if exc_type is None:
            conn.commit()
        else:
            conn.rollback()

    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
        conn.execute(f"PRAGMA journal_mode={self._config.journal_mode.value}")
        conn.execute(f"PRAGMA busy_timeout={self._config.busy_timeout_ms}")
        foreign_keys = "ON" if self._config.foreign_keys else "OFF"
        conn.execute(f"PRAGMA foreign_keys={foreign_keys}")

    def close(self) -> None:
        """Explicitly close the connection for the current thread."""
        key = self._get_connection_key()
        conn = getattr(_thread_local, key, None)
        if conn is not None:
            with contextlib.suppress(Exception):
                conn.close()
            delattr(_thread_local, key)

    @staticmethod
    def close_all() -> None:
        """Close all cached connections in current thread."""
        for attr in list(dir(_thread_local)):
            if attr.startswith("db_connection_"):
                conn = getattr(_thread_local, attr, None)
                if conn is not None:
                    with contextlib.suppress(Exception):
                        conn.close()
                delattr(_thread_local, attr)

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
