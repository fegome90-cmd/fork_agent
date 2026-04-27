"""Tests for CAS update and count_by_status in PollRunRepository."""

from __future__ import annotations

import time
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
                error_message TEXT,
                launch_method TEXT,
                launch_pane_id TEXT,
                launch_pid INTEGER,
                launch_pgid INTEGER,
                launch_recorded_at INTEGER,
                canonical_key TEXT
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


class TestStartedAtPreservation:
    """Fix: cas_update_status must preserve existing started_at on terminal transitions.
    Regression test for Copilot review finding: terminal UPDATE was overwriting started_at
    with now_ms when caller passed started_at=None.
    """

    def test_terminal_preserves_existing_started_at(self, tmp_path: Path) -> None:
        """RUNNING -> COMPLETED preserves started_at=1000 (not overwritten with transition time)."""
        repo = _make_repo(tmp_path)
        with repo._connection as conn:
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status, started_at) VALUES (?, ?, ?, ?, ?)",
                ("r1", "t1", "poll-agent", "RUNNING", 1000),
            )

        repo.cas_update_status("r1", PollRunStatus.RUNNING, PollRunStatus.COMPLETED)
        with repo._connection as conn:
            row = conn.execute("SELECT started_at FROM poll_runs WHERE id = ?", ("r1",)).fetchone()
        assert row is not None
        assert row[0] == 1000, f"started_at was overwritten to {row[0]}, expected 1000"

    def test_terminal_preserves_null_started_at(self, tmp_path: Path) -> None:
        """RUNNING -> COMPLETED: when started_at was NULL, COALESCE sets it (edge case).
        This is acceptable: runs that terminate without starting (QUEUED -> TERMINATING)
        should get a timestamp. The key fix is preserving EXISTING started_at values."""
        repo = _make_repo(tmp_path)
        with repo._connection as conn:
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status, started_at) VALUES (?, ?, ?, ?, ?)",
                ("r1", "t1", "poll-agent", "RUNNING", None),
            )

        before = int(time.time() * 1000)
        repo.cas_update_status("r1", PollRunStatus.RUNNING, PollRunStatus.FAILED)
        after = int(time.time() * 1000)
        with repo._connection as conn:
            row = conn.execute("SELECT started_at FROM poll_runs WHERE id = ?", ("r1",)).fetchone()
        assert row is not None
        assert row[0] is not None, "started_at should be set when NULL (edge case acceptable)"
        assert before <= row[0] <= after, (
            f"started_at {row[0]} should be near transition time ({before}-{after})"
        )

    def test_nonterminal_preserves_existing_started_at(self, tmp_path: Path) -> None:
        """QUEUED -> RUNNING preserves started_at=500 on non-terminal transition."""
        repo = _make_repo(tmp_path)
        with repo._connection as conn:
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status, started_at) VALUES (?, ?, ?, ?, ?)",
                ("r1", "t1", "poll-agent", "QUEUED", 500),
            )

        repo.cas_update_status("r1", PollRunStatus.QUEUED, PollRunStatus.RUNNING)
        with repo._connection as conn:
            row = conn.execute("SELECT started_at FROM poll_runs WHERE id = ?", ("r1",)).fetchone()
        assert row is not None
        assert row[0] == 500, f"started_at was changed to {row[0]}, expected 500"

    def test_nonterminal_sets_started_at_when_null(self, tmp_path: Path) -> None:
        """QUEUED -> RUNNING sets started_at when it was NULL (COALESCE fallback)."""
        repo = _make_repo(tmp_path)
        with repo._connection as conn:
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status, started_at) VALUES (?, ?, ?, ?, ?)",
                ("r1", "t1", "poll-agent", "QUEUED", None),
            )

        repo.cas_update_status("r1", PollRunStatus.QUEUED, PollRunStatus.RUNNING)
        with repo._connection as conn:
            row = conn.execute("SELECT started_at FROM poll_runs WHERE id = ?", ("r1",)).fetchone()
        assert row is not None
        assert row[0] is not None, "started_at should be set to transition time"

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


class TestLaunchMetadata:
    """Phase 1: launch metadata must be persisted for cleanup."""

    def test_record_launch_metadata_tmux(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        with repo._connection as conn:
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status) VALUES (?, ?, ?, ?)",
                ("r1", "t1", "poll-agent", "SPAWNING"),
            )

        saved = repo.record_launch_metadata("r1", launch_method="tmux", pane_id="%9")
        assert saved is True
        run = repo.get_by_id("r1")
        assert run is not None
        assert run.launch_method == "tmux"
        assert run.launch_pane_id == "%9"

    def test_list_launch_blocking_includes_quarantined(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        with repo._connection as conn:
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status) VALUES ('r1', 't1', 'a', 'RUNNING')"
            )
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status) VALUES ('r2', 't2', 'a', 'QUARANTINED')"
            )
            conn.execute(
                "INSERT INTO poll_runs (id, task_id, agent_name, status) VALUES ('r3', 't3', 'a', 'COMPLETED')"
            )

        runs = repo.list_launch_blocking()
        run_ids = {run.id for run in runs}
        assert run_ids == {"r1", "r2"}
