#!/usr/bin/env python3
"""Quick performance baseline for fork_agent.

Run: uv run python scripts/benchmark.py

Measures key operations against a temp DB and prints results.
Does NOT require any external dependencies beyond the project itself.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from src.application.services.memory_service import MemoryService
from src.domain.entities.observation import Observation
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)


def _bench(label: str, iterations: int, fn) -> float:
    """Run fn() iterations times, return avg ms per op."""
    start = time.perf_counter()
    for _ in range(iterations):
        fn()
    elapsed = (time.perf_counter() - start) * 1000
    avg = elapsed / iterations
    print(f"  {label:30s} {avg:8.2f}ms/op  ({iterations} ops, {elapsed:.0f}ms total)")
    return avg


def main() -> None:
    import tempfile

    tmp = Path(tempfile.mkdtemp()) / "bench.db"
    config = DatabaseConfig(db_path=tmp)
    migrations_dir = Path(__file__).parent.parent / "src" / "infrastructure" / "persistence" / "migrations"
    run_migrations(config, migrations_dir)
    conn = DatabaseConnection(config)
    repo = ObservationRepository(conn)
    service = MemoryService(repository=repo)

    print("fork_agent Performance Baseline")
    print("=" * 50)
    print(f"DB: {tmp}")
    print(f"Python: {sys.version.split()[0]}")
    print()

    # Insert
    ids: list[str] = []
    _bench("save (single)", 100, lambda: (
        ids.append(service.save(content=f"bench obs {len(ids)}", type="discovery").id)
    ))

    # Search
    _bench("search (full-text)", 50, lambda: service.search(query="bench", limit=10))

    # List
    _bench("get_recent (limit=20)", 50, lambda: service.get_recent(limit=20))

    # Get by ID
    _bench("get_by_id", 50, lambda: service.get_by_id(ids[0]) if ids else None)

    # Count
    count = len(repo.get_all())
    print(f"\n  Total observations: {count}")
    print(f"  DB size: {tmp.stat().st_size / 1024:.1f} KB")

    # Cleanup
    tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
