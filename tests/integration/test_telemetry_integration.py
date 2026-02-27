"""Integration tests for telemetry integration with MemoryService.

FASE 1.5 validation: ensure telemetry is connected and recording events.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.application.services.memory_service import MemoryService
from src.application.services.telemetry.telemetry_service import TelemetryService
from src.infrastructure.persistence.container import create_container
from src.infrastructure.persistence.repositories.observation_repository import (
    ObservationRepository,
)
from src.infrastructure.persistence.repositories.telemetry_repository import (
    TelemetryRepositoryImpl,
)


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield Path(f.name)


@pytest.fixture
def container(temp_db: Path):
    """Create a container with telemetry enabled."""
    return create_container(temp_db)


@pytest.fixture
def memory_service(container) -> MemoryService:
    """Get MemoryService with telemetry injected."""
    return container.memory_service()


@pytest.fixture
def telemetry_service(container) -> TelemetryService:
    """Get TelemetryService."""
    return container.telemetry_service()


class TestTelemetryIntegration:
    """Test telemetry integration with MemoryService."""

    def test_save_records_telemetry_event(
        self,
        memory_service: MemoryService,
        telemetry_service: TelemetryService,
    ) -> None:
        """MemoryService.save() should record telemetry event."""
        # Start session
        telemetry_service.start_session("test-session-1")

        # Perform save
        obs = memory_service.save("test observation")

        # Verify observation created
        assert obs.id is not None
        assert obs.content == "test observation"

        # Verify telemetry recorded
        telemetry_service.flush()
        counts = telemetry_service.get_event_counts("24h")
        assert counts.get("memory.save", 0) >= 1, "Expected at least 1 memory.save event"

    def test_search_records_telemetry_event(
        self,
        memory_service: MemoryService,
        telemetry_service: TelemetryService,
    ) -> None:
        """MemoryService.search() should record telemetry event."""
        # Start session
        telemetry_service.start_session("test-session-2")

        # Create some data
        memory_service.save("python code")
        memory_service.save("javascript code")

        # Perform search
        results = memory_service.search("python")

        # Verify search works
        assert len(results) >= 1

        # Verify telemetry recorded
        telemetry_service.flush()
        counts = telemetry_service.get_event_counts("24h")
        assert counts.get("memory.search", 0) >= 1, "Expected at least 1 memory.search event"

    def test_delete_records_telemetry_event(
        self,
        memory_service: MemoryService,
        telemetry_service: TelemetryService,
    ) -> None:
        """MemoryService.delete() should record telemetry event."""
        # Start session
        telemetry_service.start_session("test-session-3")

        # Create and delete
        obs = memory_service.save("to be deleted")
        memory_service.delete(obs.id)

        # Verify telemetry recorded
        telemetry_service.flush()
        counts = telemetry_service.get_event_counts("24h")
        assert counts.get("memory.delete", 0) >= 1, "Expected at least 1 memory.delete event"

    def test_telemetry_disabled_no_events(
        self,
        temp_db: Path,
    ) -> None:
        """When telemetry is disabled, no events should be recorded."""
        # Use container to get proper setup with migrations
        container = create_container(temp_db)

        # Get services
        obs_repo = container.observation_repository()

        # Create TelemetryService with enabled=False
        telemetry_repo = TelemetryRepositoryImpl(container.database_connection())
        telemetry = TelemetryService(
            repository=telemetry_repo,
            enabled=False,
        )

        # Create MemoryService with disabled telemetry
        memory = MemoryService(
            repository=obs_repo,
            telemetry_service=telemetry,
        )

        # Perform operations
        memory.save("test")
        memory.search("test")

        # Verify no telemetry recorded
        telemetry.flush()
        counts = telemetry.get_event_counts("24h")
        assert counts.get("memory.save", 0) == 0, "Expected no memory.save events when disabled"
        assert counts.get("memory.search", 0) == 0, "Expected no memory.search events when disabled"

    def test_full_flow_telemetry_counts(
        self,
        memory_service: MemoryService,
        telemetry_service: TelemetryService,
    ) -> None:
        """Complete flow should produce correct telemetry counts."""
        # Start session
        telemetry_service.start_session("test-session-full")

        # Perform multiple operations
        obs1 = memory_service.save("observation 1")
        obs2 = memory_service.save("observation 2")
        memory_service.search("observation")
        memory_service.delete(obs1.id)

        # Verify counts
        telemetry_service.flush()
        counts = telemetry_service.get_event_counts("24h")

        assert counts.get("memory.save", 0) >= 2, f"Expected >= 2 saves, got {counts.get('memory.save', 0)}"
        assert counts.get("memory.search", 0) >= 1, f"Expected >= 1 search, got {counts.get('memory.search', 0)}"
        assert counts.get("memory.delete", 0) >= 1, f"Expected >= 1 delete, got {counts.get('memory.delete', 0)}"
