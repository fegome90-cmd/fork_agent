"""Verify exact N observations after N concurrent saves.

This test catches lost-update bugs that exception-only tests miss.
Pattern adapted from pi-teams lock.race.test.ts.
WAL mode + busy_timeout=5000ms must prevent data loss under contention.
"""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from src.domain.entities.observation import Observation
from src.infrastructure.persistence.database import (
    DatabaseConfig,
    DatabaseConnection,
)
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "infrastructure" / "persistence" / "migrations"
)


@pytest.fixture()
def db(tmp_path):
    """Create a fresh DB with all migrations applied."""
    db_path = tmp_path / "race_test.db"
    config = DatabaseConfig(db_path=db_path)
    run_migrations(config, MIGRATIONS_DIR)
    conn = DatabaseConnection(config=config)
    yield conn
    conn.close_all()


def _make_observation(content: str) -> Observation:
    return Observation(
        id=str(uuid.uuid4()),
        timestamp=int(time.time() * 1000),
        content=content,
    )


class TestConcurrentSavesExactCount:
    """N concurrent saves must produce exactly N observations."""

    def test_concurrent_saves_exact_count(self, db):
        """N concurrent saves must produce exactly N observations.

        Uses a threading.Barrier to synchronize all threads so they
        hit the database at the same instant, maximising contention.
        """
        N = 100
        repo = ObservationRepository(connection=db)
        barrier = threading.Barrier(N)

        def save_one(i: int) -> None:
            barrier.wait(timeout=30)
            obs = _make_observation(f"concurrent observation {i}")
            repo.create(obs)

        with ThreadPoolExecutor(max_workers=N) as pool:
            futures = [pool.submit(save_one, i) for i in range(N)]
            for f in futures:
                f.result()  # propagate exceptions

        results = repo.search("concurrent observation")
        assert len(results) == N, f"Lost {N - len(results)} observations!"

    def test_concurrent_saves_different_content(self, db):
        """Each of N concurrent saves must preserve its unique content."""
        N = 50
        repo = ObservationRepository(connection=db)
        barrier = threading.Barrier(N)

        def save_one(i: int) -> None:
            barrier.wait(timeout=30)
            obs = _make_observation(f"unique-content-{i}-payload")
            repo.create(obs)

        with ThreadPoolExecutor(max_workers=N) as pool:
            futures = [pool.submit(save_one, i) for i in range(N)]
            for f in futures:
                f.result()

        all_obs = repo.get_all()
        contents = {o.content for o in all_obs}
        expected = {f"unique-content-{i}-payload" for i in range(N)}
        assert contents == expected, f"Content mismatch: {len(expected) - len(contents)} missing"

    def test_concurrent_save_and_read(self, db):
        """Reads during writes must not crash or return corrupt data."""
        N_WRITERS = 30
        N_READERS = 10
        TOTAL = N_WRITERS + N_READERS
        repo = ObservationRepository(connection=db)

        # Seed one observation so readers always find something
        seed = _make_observation("seed-observation")
        repo.create(seed)

        barrier = threading.Barrier(TOTAL)
        errors: list[Exception] = []

        def writer(i: int) -> None:
            barrier.wait(timeout=30)
            obs = _make_observation(f"writer-{i}-content")
            repo.create(obs)

        def reader(i: int) -> None:  # noqa: ARG001
            barrier.wait(timeout=30)
            for _ in range(20):
                try:
                    results = repo.search("observation")
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
        total = repo.count()
        # seed + N_WRITERS
        assert total == 1 + N_WRITERS, f"Expected {1 + N_WRITERS}, got {total}"
