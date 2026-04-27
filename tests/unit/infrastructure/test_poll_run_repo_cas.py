"""Tests for CAS update and count_by_status in PollRunRepository."""

from __future__ import annotations

from pathlib import Path

from src.domain.entities.poll_run import PollRunStatus
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.repositories.poll_run_repository import (
    SqlitePollRunRepository,
)


def _make_repo(tmp_path: Path) -> SqlitePollRunRepository:
    db_path = tmp_path / "test.db"
    config = DatabaseConfig(db_path=db_path)
    conn = DatabaseConnection(config=config)
    # Create the poll_runs table manually (migrations not available in unit tests)
    with conn as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS poll_runs (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at INTEGER,
                ended_at INTEGER,
                poll_run_dir TEXT,
                error_message TEXT
            );
        """)
    return SqlitePollRunRepository(connection=conn)


class TestCasUpdate:
    """SM-H3: cas_update_status must verify current status before updating."""

    def test_cas_succeeds_when_status_matches(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        with repo._connection as conn:
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status, started_at) VALUES (?, ?, ?, ?, ?)",
                ("r1", "t1", "poll-agent", "RUNNING", 0),
            )

        result = repo.cas_update_status("r1", PollRunStatus.RUNNING, PollRunStatus.COMPLETED)
        assert result is True

    def test_cas_fails_when_status_mismatch(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        with repo._connection as conn:
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status, started_at) VALUES (?, ?, ?, ?, ?)",
                ("r1", "t1", "poll-agent", "COMPLETED", 0),
            )

        result = repo.cas_update_status("r1", PollRunStatus.RUNNING, PollRunStatus.FAILED)
        assert result is False

    def test_cas_fails_when_run_missing(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)

        result = repo.cas_update_status("nonexistent", PollRunStatus.RUNNING, PollRunStatus.FAILED)
        assert result is False

    def test_cas_returns_true_on_terminal_status(self, tmp_path: Path) -> None:
        """CAS can transition RUNNING -> CANCELLED (terminal)."""
        repo = _make_repo(tmp_path)
        with repo._connection as conn:
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status, started_at) VALUES (?, ?, ?, ?, ?)",
                ("r1", "t1", "poll-agent", "RUNNING", 1000),
            )

        result = repo.cas_update_status("r1", PollRunStatus.RUNNING, PollRunStatus.CANCELLED)
        assert result is True


class TestCountByStatus:
    """Q-H3: count_by_status returns grouped counts in a single query."""

    def test_count_by_status_basic(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        with repo._connection as conn:
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status, started_at) VALUES ('r1', 't1', 'a', 'RUNNING', 0)"
            )
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status, started_at) VALUES ('r2', 't2', 'a', 'RUNNING', 0)"
            )
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status, started_at) VALUES ('r3', 't3', 'a', 'COMPLETED', 0)"
            )

        result = repo.count_by_status()
        assert result.get("RUNNING") == 2
        assert result.get("COMPLETED") == 1
        assert result.get("QUEUED", 0) == 0

    def test_count_by_status_empty(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)

        result = repo.count_by_status()
        assert result == {}
