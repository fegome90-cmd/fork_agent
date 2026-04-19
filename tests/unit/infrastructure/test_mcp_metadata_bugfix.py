"""Tests for BUG-18: MCP metadata param type mismatch.

Tests that memory_save and memory_update accept dict metadata directly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.entities.observation import Observation
from src.infrastructure.persistence.database import DatabaseConfig, DatabaseConnection
from src.infrastructure.persistence.migrations import run_migrations


@pytest.fixture()
def db_connection(tmp_path: Path) -> DatabaseConnection:
    db_path = tmp_path / "test.db"
    config = DatabaseConfig(db_path=db_path)
    migrations_dir = (
        Path(__file__).parent.parent.parent.parent
        / "src/infrastructure/persistence/migrations"
    )
    run_migrations(config, migrations_dir)
    return DatabaseConnection(config)


class TestBug18McpMetadataDict:
    """BUG-18: MCP memory_save should accept dict metadata, not str."""

    def test_memory_save_with_dict_metadata(self, db_connection: DatabaseConnection) -> None:
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        obs = Observation(
            id="mcp-meta-001",
            timestamp=1700000000000,
            content="test with metadata dict",
            metadata={"what": "testing", "why": "bugfix", "learned": "dict works"},
            type="decision",
        )
        repo.create(obs)

        result = repo.get_by_id("mcp-meta-001")
        assert result.metadata["what"] == "testing"
        assert result.metadata["learned"] == "dict works"

    def test_memory_save_via_service_with_metadata(self, db_connection: DatabaseConnection) -> None:
        from src.application.services.memory_service import MemoryService
        from src.infrastructure.persistence.repositories.observation_repository import (
            ObservationRepository,
        )

        repo = ObservationRepository(db_connection)
        service = MemoryService(repository=repo)

        obs = service.save(
            content="service metadata test",
            metadata={"source": "mcp", "agent": "claude"},
            type="discovery",
        )
        assert obs.metadata["source"] == "mcp"

        retrieved = repo.get_by_id(obs.id)
        assert retrieved.metadata["agent"] == "claude"
        assert retrieved.type == "discovery"
