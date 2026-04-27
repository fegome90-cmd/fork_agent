"""Unit tests for OrchestrationTask SQLite repository."""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from src.application.exceptions import RepositoryError
from src.domain.entities.orchestration_task import (
    OrchestrationTask,
    OrchestrationTaskStatus,
)
from src.infrastructure.persistence.database import (
    DatabaseConfig,
    DatabaseConnection,
)
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.orchestration_task_repository import (
    SqliteOrchestrationTaskRepository,
)

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[3] / "src" / "infrastructure" / "persistence" / "migrations"
)

NOW_MS = int(time.time() * 1000)


def _make_task(
    task_id: str | None = None,
    status: OrchestrationTaskStatus = OrchestrationTaskStatus.PENDING,
    owner: str | None = None,
    blocked_by: tuple[str, ...] = (),
    **overrides: object,
) -> OrchestrationTask:
    defaults: dict[str, object] = {
        "id": task_id or uuid.uuid4().hex,
        "subject": "Test task",
        "status": status,
        "owner": owner,
        "blocked_by": blocked_by,
        "created_at": NOW_MS,
        "updated_at": NOW_MS,
    }
    defaults.update(overrides)
    return OrchestrationTask(**defaults)  # type: ignore[arg-type]


@pytest.fixture()
def db(tmp_path: Path) -> Generator[DatabaseConnection, None, None]:
    """Create a fresh DB with all migrations applied."""
    db_path = tmp_path / "test_orchestration.db"
    config = DatabaseConfig(db_path=db_path)
    run_migrations(config, MIGRATIONS_DIR)
    conn = DatabaseConnection(config=config)
    yield conn
    conn.close_all()


@pytest.fixture()
def repo(db: DatabaseConnection) -> SqliteOrchestrationTaskRepository:
    return SqliteOrchestrationTaskRepository(connection=db)


# ---------------------------------------------------------------------------
# save + get_by_id round-trip
# ---------------------------------------------------------------------------


class TestSaveAndGet:
    def test_save_and_get_by_id(self, repo: SqliteOrchestrationTaskRepository) -> None:
        task = _make_task(task_id="aa" * 16)
        repo.save(task)
        result = repo.get_by_id(task.id)
        assert result is not None
        assert result.id == task.id
        assert result.subject == task.subject
        assert result.status == task.status

    def test_get_by_id_returns_none_when_not_found(
        self, repo: SqliteOrchestrationTaskRepository
    ) -> None:
        assert repo.get_by_id("nonexistent") is None

    def test_save_updates_existing_task(self, repo: SqliteOrchestrationTaskRepository) -> None:
        task = _make_task(task_id="bb" * 16, subject="Original")
        repo.save(task)

        from dataclasses import replace

        updated = replace(task, subject="Updated", updated_at=NOW_MS + 1000)
        repo.save(updated)

        result = repo.get_by_id(task.id)
        assert result is not None
        assert result.subject == "Updated"

    def test_save_with_all_fields(self, repo: SqliteOrchestrationTaskRepository) -> None:
        task = _make_task(
            task_id="cc" * 16,
            subject="Full task",
            description="A description",
            status=OrchestrationTaskStatus.PLANNING,
            owner="agent-1",
            blocked_by=("dd" * 16,),
            plan_text="# Plan",
            approved_by="reviewer",
            approved_at=NOW_MS,
            requested_by="alice",
        )
        repo.save(task)
        result = repo.get_by_id(task.id)
        assert result is not None
        assert result.description == "A description"
        assert result.owner == "agent-1"
        assert result.blocked_by == ("dd" * 16,)
        assert result.plan_text == "# Plan"
        assert result.approved_by == "reviewer"
        assert result.approved_at == NOW_MS
        assert result.requested_by == "alice"


# ---------------------------------------------------------------------------
# list_by_status
# ---------------------------------------------------------------------------


class TestListByStatus:
    def test_list_by_status_returns_correct_tasks(
        self, repo: SqliteOrchestrationTaskRepository
    ) -> None:
        repo.save(_make_task(task_id="t1" + "0" * 30, status=OrchestrationTaskStatus.PENDING))
        repo.save(_make_task(task_id="t2" + "0" * 30, status=OrchestrationTaskStatus.PENDING))
        repo.save(_make_task(task_id="t3" + "0" * 30, status=OrchestrationTaskStatus.PLANNING))

        pending = repo.list_by_status(OrchestrationTaskStatus.PENDING)
        assert len(pending) == 2
        assert all(t.status == OrchestrationTaskStatus.PENDING for t in pending)

        planning = repo.list_by_status(OrchestrationTaskStatus.PLANNING)
        assert len(planning) == 1

    def test_list_by_status_empty(self, repo: SqliteOrchestrationTaskRepository) -> None:
        result = repo.list_by_status(OrchestrationTaskStatus.COMPLETED)
        assert result == []


# ---------------------------------------------------------------------------
# list_by_owner
# ---------------------------------------------------------------------------


class TestListByOwner:
    def test_list_by_owner_returns_correct_tasks(
        self, repo: SqliteOrchestrationTaskRepository
    ) -> None:
        repo.save(_make_task(task_id="o1" + "0" * 30, owner="alice"))
        repo.save(_make_task(task_id="o2" + "0" * 30, owner="bob"))
        repo.save(_make_task(task_id="o3" + "0" * 30, owner="alice"))

        alice_tasks = repo.list_by_owner("alice")
        assert len(alice_tasks) == 2
        assert all(t.owner == "alice" for t in alice_tasks)

    def test_list_by_owner_empty(self, repo: SqliteOrchestrationTaskRepository) -> None:
        result = repo.list_by_owner("nobody")
        assert result == []


# ---------------------------------------------------------------------------
# list_blocked
# ---------------------------------------------------------------------------


class TestListBlocked:
    def test_list_blocked_returns_tasks_with_blockers(
        self, repo: SqliteOrchestrationTaskRepository
    ) -> None:
        repo.save(_make_task(task_id="b1" + "0" * 30, blocked_by=("b3" + "0" * 30,)))
        repo.save(_make_task(task_id="b2" + "0" * 30, blocked_by=()))
        repo.save(_make_task(task_id="b3" + "0" * 30, blocked_by=("b4" + "0" * 30,)))

        blocked = repo.list_blocked()
        assert len(blocked) == 2
        ids = {t.id for t in blocked}
        assert ids == {"b1" + "0" * 30, "b3" + "0" * 30}

    def test_list_blocked_empty(self, repo: SqliteOrchestrationTaskRepository) -> None:
        repo.save(_make_task(task_id="b0" + "0" * 30))
        assert repo.list_blocked() == []


# ---------------------------------------------------------------------------
# list_all (M9)
# ---------------------------------------------------------------------------


class TestListAll:
    def test_list_all_returns_all_tasks_ordered_by_created_at_desc(
        self, repo: SqliteOrchestrationTaskRepository
    ) -> None:
        repo.save(_make_task(task_id="la1" + "0" * 30, created_at=100))
        repo.save(_make_task(task_id="la2" + "0" * 30, created_at=300))
        repo.save(_make_task(task_id="la3" + "0" * 30, created_at=200))

        result = repo.list_all()
        assert len(result) == 3
        # Ordered by created_at DESC
        assert result[0].id == "la2" + "0" * 30
        assert result[1].id == "la3" + "0" * 30
        assert result[2].id == "la1" + "0" * 30

    def test_list_all_empty(self, repo: SqliteOrchestrationTaskRepository) -> None:
        assert repo.list_all() == []


# ---------------------------------------------------------------------------
# get_by_ids (M9)
# ---------------------------------------------------------------------------


class TestGetByIds:
    def test_get_by_ids_returns_matching_tasks(
        self, repo: SqliteOrchestrationTaskRepository
    ) -> None:
        repo.save(_make_task(task_id="gi1" + "0" * 30))
        repo.save(_make_task(task_id="gi2" + "0" * 30))
        repo.save(_make_task(task_id="gi3" + "0" * 30))

        result = repo.get_by_ids(["gi1" + "0" * 30, "gi3" + "0" * 30])
        assert len(result) == 2
        ids = {t.id for t in result}
        assert ids == {"gi1" + "0" * 30, "gi3" + "0" * 30}

    def test_get_by_ids_empty_list(self, repo: SqliteOrchestrationTaskRepository) -> None:
        assert repo.get_by_ids([]) == []

    def test_get_by_ids_nonexistent_ids(self, repo: SqliteOrchestrationTaskRepository) -> None:
        result = repo.get_by_ids(["nonexistent1", "nonexistent2"])
        assert result == []


# ---------------------------------------------------------------------------
# cas_save (M9)
# ---------------------------------------------------------------------------


class TestCasSave:
    def test_cas_save_with_matching_status_succeeds(
        self, repo: SqliteOrchestrationTaskRepository
    ) -> None:
        task = _make_task(task_id="cs1" + "0" * 30, status=OrchestrationTaskStatus.PENDING)
        repo.save(task)

        from dataclasses import replace

        updated = replace(task, status=OrchestrationTaskStatus.PLANNING, plan_text="# Plan")
        result = repo.cas_save(updated, OrchestrationTaskStatus.PENDING)
        assert result is True

        fetched = repo.get_by_id(task.id)
        assert fetched is not None
        assert fetched.status == OrchestrationTaskStatus.PLANNING

    def test_cas_save_with_wrong_status_fails(
        self, repo: SqliteOrchestrationTaskRepository
    ) -> None:
        task = _make_task(task_id="cs2" + "0" * 30, status=OrchestrationTaskStatus.PENDING)
        repo.save(task)

        from dataclasses import replace

        updated = replace(task, status=OrchestrationTaskStatus.PLANNING, plan_text="# Plan")
        # Simulate stale expected_status — DB has PENDING but we pass APPROVED
        result = repo.cas_save(updated, OrchestrationTaskStatus.APPROVED)
        assert result is False

        # Original task unchanged
        fetched = repo.get_by_id(task.id)
        assert fetched is not None
        assert fetched.status == OrchestrationTaskStatus.PENDING


# ---------------------------------------------------------------------------
# Corrupt data handling (M9)
# ---------------------------------------------------------------------------


class TestCorruptData:
    def test_corrupted_blocked_by_json_returns_empty_tuple(
        self, repo: SqliteOrchestrationTaskRepository
    ) -> None:
        """Malformed JSON in blocked_by column returns empty tuple, not crash."""
        # Insert a row with corrupt blocked_by via raw SQL
        import sqlite3

        db_path = repo._connection._config.db_path
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """INSERT INTO orchestration_tasks
               (id, subject, description, status, owner, blocked_by,
                plan_text, created_at, updated_at, approved_by, approved_at, requested_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "corrupt" + "0" * 26,
                "Corrupt task",
                None,
                "PENDING",
                None,
                "{not valid json!!!",
                None,
                NOW_MS,
                NOW_MS,
                None,
                None,
                None,
            ),
        )
        conn.commit()
        conn.close()

        result = repo.get_by_id("corrupt" + "0" * 26)
        assert result is not None
        assert result.blocked_by == ()

    def test_invalid_status_string_raises_repository_error(
        self, repo: SqliteOrchestrationTaskRepository
    ) -> None:
        """A row with an invalid status string in DB raises RepositoryError."""
        import sqlite3

        db_path = repo._connection._config.db_path
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """INSERT INTO orchestration_tasks
               (id, subject, description, status, owner, blocked_by,
                plan_text, created_at, updated_at, approved_by, approved_at, requested_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "badstat" + "0" * 25,
                "Bad status task",
                None,
                "INVALID_STATUS",
                None,
                "[]",
                None,
                NOW_MS,
                NOW_MS,
                None,
                None,
                None,
            ),
        )
        conn.commit()
        conn.close()

        with pytest.raises(RepositoryError, match="Invalid status"):
            repo.get_by_id("badstat" + "0" * 25)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_removes_task(self, repo: SqliteOrchestrationTaskRepository) -> None:
        task = _make_task(task_id="d1" + "0" * 30)
        repo.save(task)
        assert repo.get_by_id(task.id) is not None

        repo.remove(task.id)
        assert repo.get_by_id(task.id) is None

    def test_delete_nonexistent_raises(self, repo: SqliteOrchestrationTaskRepository) -> None:
        with pytest.raises(RepositoryError, match="not found"):
            repo.remove("nonexistent")


# ---------------------------------------------------------------------------
# blocked_by JSON serialization
# ---------------------------------------------------------------------------


class TestBlockedBySerialization:
    def test_tuple_round_trip(self, repo: SqliteOrchestrationTaskRepository) -> None:
        blockers = ("x1" + "0" * 30, "x2" + "0" * 30, "x3" + "0" * 30)
        task = _make_task(task_id="j1" + "0" * 30, blocked_by=blockers)
        repo.save(task)
        result = repo.get_by_id(task.id)
        assert result is not None
        assert result.blocked_by == blockers
        assert isinstance(result.blocked_by, tuple)

    def test_empty_tuple_round_trip(self, repo: SqliteOrchestrationTaskRepository) -> None:
        task = _make_task(task_id="j2" + "0" * 30, blocked_by=())
        repo.save(task)
        result = repo.get_by_id(task.id)
        assert result is not None
        assert result.blocked_by == ()


# ---------------------------------------------------------------------------
# Concurrent access
# ---------------------------------------------------------------------------


class TestConcurrentAccess:
    def test_concurrent_saves(self, db: DatabaseConnection) -> None:
        """Multiple threads saving tasks concurrently must not lose data."""
        repo = SqliteOrchestrationTaskRepository(connection=db)
        N = 50
        barrier = threading.Barrier(N)

        def save_one(i: int) -> None:
            barrier.wait(timeout=30)
            task = _make_task(task_id=f"concurrent-{i:04d}" + "0" * 24)
            repo.save(task)

        with ThreadPoolExecutor(max_workers=N) as pool:
            futures = [pool.submit(save_one, i) for i in range(N)]
            for f in futures:
                f.result()

        # Verify all tasks are present
        all_pending = repo.list_by_status(OrchestrationTaskStatus.PENDING)
        concurrent_ids = {t.id for t in all_pending if t.id.startswith("concurrent-")}
        assert len(concurrent_ids) == N, f"Expected {N}, got {len(concurrent_ids)}"

    def test_concurrent_save_and_read(self, db: DatabaseConnection) -> None:
        """Reads during writes must not crash."""
        repo = SqliteOrchestrationTaskRepository(connection=db)
        N_WRITERS = 20
        N_READERS = 10
        TOTAL = N_WRITERS + N_READERS
        barrier = threading.Barrier(TOTAL)
        errors: list[Exception] = []

        def writer(i: int) -> None:
            barrier.wait(timeout=30)
            task = _make_task(task_id=f"rw-writer-{i:04d}" + "0" * 20)
            repo.save(task)

        def reader(i: int) -> None:  # noqa: ARG001
            barrier.wait(timeout=30)
            for _ in range(10):
                try:
                    results = repo.list_by_status(OrchestrationTaskStatus.PENDING)
                    assert isinstance(results, list)
                except Exception as exc:
                    errors.append(exc)

        with ThreadPoolExecutor(max_workers=TOTAL) as pool:
            futures = [pool.submit(writer, i) for i in range(N_WRITERS)] + [
                pool.submit(reader, i) for i in range(N_READERS)
            ]
            for f in futures:
                f.result()

        assert not errors, f"Reader errors: {errors}"
