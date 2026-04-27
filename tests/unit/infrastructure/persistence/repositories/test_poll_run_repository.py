"""Unit tests for SqlitePollRunRepository.

Focuses on transition validation in update_status (H5):
  - valid transition succeeds
  - invalid transition raises ValueError
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.entities.poll_run import PollRun, PollRunStatus
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.poll_run_repository import (
    SqlitePollRunRepository,
)


@pytest.fixture
def db(tmp_path: Path) -> DatabaseConnection:
    """In-memory-ish SQLite with migrations applied."""
    db_path = tmp_path / "test.db"
    config = DatabaseConfig(db_path=db_path)
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
    migrations_dir = project_root / "src" / "infrastructure" / "persistence" / "migrations"
    run_migrations(config, migrations_dir)
    return DatabaseConnection(config=config)


@pytest.fixture
def repo(db: DatabaseConnection) -> SqlitePollRunRepository:
    return SqlitePollRunRepository(connection=db)


def _make_run(status: PollRunStatus = PollRunStatus.QUEUED) -> PollRun:
    return PollRun(id="run-1", task_id="t-1", agent_name="agent-x", status=status)


class TestUpdateStatusValidTransition:
    """Valid transitions should succeed."""

    def test_queued_to_spawning(self, repo: SqlitePollRunRepository) -> None:
        run = _make_run(PollRunStatus.QUEUED)
        repo.save(run)
        repo.update_status("run-1", PollRunStatus.SPAWNING)
        updated = repo.get_by_id("run-1")
        assert updated is not None
        assert updated.status == PollRunStatus.SPAWNING

    def test_queued_to_quarantined(self, repo: SqlitePollRunRepository) -> None:
        run = _make_run(PollRunStatus.QUEUED)
        repo.save(run)
        repo.update_status("run-1", PollRunStatus.QUARANTINED)
        updated = repo.get_by_id("run-1")
        assert updated is not None
        assert updated.status == PollRunStatus.QUARANTINED

    def test_queued_to_cancelled(self, repo: SqlitePollRunRepository) -> None:
        run = _make_run(PollRunStatus.QUEUED)
        repo.save(run)
        repo.update_status("run-1", PollRunStatus.CANCELLED)
        updated = repo.get_by_id("run-1")
        assert updated is not None
        assert updated.status == PollRunStatus.CANCELLED


class TestUpdateStatusInvalidTransition:
    """Invalid transitions should raise ValueError."""

    def test_queued_to_running_raises(self, repo: SqlitePollRunRepository) -> None:
        run = _make_run(PollRunStatus.QUEUED)
        repo.save(run)
        with pytest.raises(ValueError, match="Invalid poll run transition"):
            repo.update_status("run-1", PollRunStatus.RUNNING)

    def test_queued_to_completed_raises(self, repo: SqlitePollRunRepository) -> None:
        run = _make_run(PollRunStatus.QUEUED)
        repo.save(run)
        with pytest.raises(ValueError, match="Invalid poll run transition"):
            repo.update_status("run-1", PollRunStatus.COMPLETED)

    def test_completed_to_running_raises(self, repo: SqlitePollRunRepository) -> None:
        run = _make_run(PollRunStatus.COMPLETED)
        repo.save(run)
        with pytest.raises(ValueError, match="Invalid poll run transition"):
            repo.update_status("run-1", PollRunStatus.RUNNING)

    def test_terminal_to_anything_raises(self, repo: SqlitePollRunRepository) -> None:
        """All terminal states should reject any transition."""
        for terminal in (PollRunStatus.COMPLETED, PollRunStatus.FAILED, PollRunStatus.CANCELLED):
            run = _make_run(terminal)
            run_id = f"run-{terminal.value}"
            run = PollRun(id=run_id, task_id="t-1", agent_name="a", status=terminal)
            repo.save(run)
            for target in PollRunStatus:
                if target == terminal:
                    continue
                with pytest.raises(ValueError, match="Invalid poll run transition"):
                    repo.update_status(run_id, target)
