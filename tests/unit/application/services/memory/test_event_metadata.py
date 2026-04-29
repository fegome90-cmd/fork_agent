"""Unit tests for MemoryEventMetadata contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.application.services.memory.event_metadata import (
    EventType,
    ExecutionMode,
    MemoryEventMetadata,
    create_event_metadata,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_event_type_values(self) -> None:
        """Test that EventType has expected values."""
        assert EventType.AGENT_SPAWNED == "agent_spawned"
        assert EventType.TASK_STARTED == "task_started"
        assert EventType.SHIP_COMPLETED == "ship_completed"
        assert EventType.MEMORY_SAVE == "memory_save"

    def test_event_type_from_string(self) -> None:
        """Test creating EventType from string."""
        assert EventType("agent_spawned") == EventType.AGENT_SPAWNED


class TestExecutionMode:
    """Tests for ExecutionMode enum."""

    def test_mode_values(self) -> None:
        """Test that ExecutionMode has expected values."""
        assert ExecutionMode.WORKTREE == "worktree"
        assert ExecutionMode.INPLACE == "inplace"
        assert ExecutionMode.CHECKOUT == "checkout"


class TestMemoryEventMetadata:
    """Tests for MemoryEventMetadata model."""

    def test_create_minimal_metadata(self) -> None:
        """Test creating metadata with required fields only."""
        metadata = MemoryEventMetadata(
            event_type="agent_spawned",
            run_id="run-123",
            task_id="task-456",
            agent_id="agent:0",
            session_name="session-1",
            timestamp_ms=1234567890000,
            mode="worktree",
            idempotency_key="run-123:task-456:agent_spawned:0",
        )
        assert metadata.event_type == "agent_spawned"
        assert metadata.run_id == "run-123"
        assert metadata.idempotency_key == "run-123:task-456:agent_spawned:0"

    def test_create_with_optional_fields(self) -> None:
        """Test creating metadata with optional fields."""
        metadata = MemoryEventMetadata(
            event_type="ship_completed",
            run_id="run-123",
            task_id="task-456",
            agent_id="agent:0",
            session_name="session-1",
            timestamp_ms=1234567890000,
            mode="worktree",
            idempotency_key="run-123:task-456:ship_completed:0",
            branch="feat/test",
            target_branch="main",
            pid=12345,
            success=True,
        )
        assert metadata.branch == "feat/test"
        assert metadata.target_branch == "main"
        assert metadata.pid == 12345
        assert metadata.success is True

    def test_create_with_extra_fields(self) -> None:
        """Test that extra fields are allowed."""
        metadata = MemoryEventMetadata(
            event_type="task_started",
            run_id="run-123",
            task_id="task-456",
            agent_id="agent:0",
            session_name="session-1",
            timestamp_ms=1234567890000,
            mode="inplace",
            idempotency_key="run-123:task-456:task_started:0",
            custom_field="custom_value",
            another_field=42,
        )
        assert metadata.custom_field == "custom_value"  # type: ignore[attr-defined]
        assert metadata.another_field == 42  # type: ignore[attr-defined]

    def test_frozen_model(self) -> None:
        """Test that metadata is immutable."""
        metadata = MemoryEventMetadata(
            event_type="agent_spawned",
            run_id="run-123",
            task_id="task-456",
            agent_id="agent:0",
            session_name="session-1",
            timestamp_ms=1234567890000,
            mode="worktree",
            idempotency_key="run-123:task-456:agent_spawned:0",
        )
        with pytest.raises(ValidationError):
            metadata.run_id = "modified"  # type: ignore[mutable]

    def test_empty_idempotency_key_rejected(self) -> None:
        """Test that empty idempotency_key is rejected."""
        with pytest.raises(ValidationError, match="idempotency_key cannot be empty"):
            MemoryEventMetadata(
                event_type="agent_spawned",
                run_id="run-123",
                task_id="task-456",
                agent_id="agent:0",
                session_name="session-1",
                timestamp_ms=1234567890000,
                mode="worktree",
                idempotency_key="",
            )

    def test_negative_timestamp_rejected(self) -> None:
        """Test that negative timestamp is rejected."""
        with pytest.raises(ValidationError):
            MemoryEventMetadata(
                event_type="agent_spawned",
                run_id="run-123",
                task_id="task-456",
                agent_id="agent:0",
                session_name="session-1",
                timestamp_ms=-1,
                mode="worktree",
                idempotency_key="run-123:task-456:agent_spawned:0",
            )

    def test_negative_pid_rejected(self) -> None:
        """Test that negative pid is rejected."""
        with pytest.raises(ValidationError):
            MemoryEventMetadata(
                event_type="agent_spawned",
                run_id="run-123",
                task_id="task-456",
                agent_id="agent:0",
                session_name="session-1",
                timestamp_ms=1234567890000,
                mode="worktree",
                idempotency_key="run-123:task-456:agent_spawned:0",
                pid=-1,
            )

    def test_invalid_launch_id_hex_rejected(self) -> None:
        """Test that invalid launch_id hex is rejected."""
        with pytest.raises(ValidationError, match="must be a 32-character hex string"):
            MemoryEventMetadata(
                event_type="agent_spawned",
                run_id="run-123",
                task_id="task-456",
                agent_id="agent:0",
                session_name="session-1",
                timestamp_ms=1234567890000,
                mode="worktree",
                idempotency_key="run-123:task-456:agent_spawned:0",
                launch_id="invalid-uuid-with-xyz",
            )


class TestGenerateIdempotencyKey:
    """Tests for idempotency key generation."""

    def test_generate_basic_key(self) -> None:
        """Test basic key generation."""
        key = MemoryEventMetadata.generate_idempotency_key(
            run_id="run-123",
            task_id="task-456",
            event_type="agent_spawned",
        )
        assert key == "run-123:task-456:agent_spawned:0"

    def test_generate_key_with_sequence(self) -> None:
        """Test key generation with sequence."""
        key = MemoryEventMetadata.generate_idempotency_key(
            run_id="run-123",
            task_id="task-456",
            event_type="agent_spawned",
            sequence=5,
        )
        assert key == "run-123:task-456:agent_spawned:5"

    def test_keys_are_deterministic(self) -> None:
        """Test that same inputs produce same key."""
        key1 = MemoryEventMetadata.generate_idempotency_key(
            run_id="run-123",
            task_id="task-456",
            event_type="agent_spawned",
        )
        key2 = MemoryEventMetadata.generate_idempotency_key(
            run_id="run-123",
            task_id="task-456",
            event_type="agent_spawned",
        )
        assert key1 == key2


class TestCreateEventMetadata:
    """Tests for create_event_metadata factory function."""

    def test_create_with_defaults(self) -> None:
        """Test creating metadata with factory function."""
        metadata = create_event_metadata(
            event_type=EventType.AGENT_SPAWNED,
            run_id="run-123",
            task_id="task-456",
            agent_id="agent:0",
            session_name="session-1",
            mode=ExecutionMode.WORKTREE,
        )
        assert metadata.event_type == "agent_spawned"
        assert metadata.run_id == "run-123"
        assert metadata.mode == "worktree"
        assert metadata.timestamp_ms > 0
        assert metadata.idempotency_key == "run-123:task-456:agent_spawned:0"

    def test_create_with_string_types(self) -> None:
        """Test creating metadata with string types."""
        metadata = create_event_metadata(
            event_type="custom_event",
            run_id="run-123",
            task_id="task-456",
            agent_id="agent:0",
            session_name="session-1",
            mode="custom_mode",
        )
        assert metadata.event_type == "custom_event"
        assert metadata.mode == "custom_mode"

    def test_create_with_extra_fields(self) -> None:
        """Test creating metadata with extra fields."""
        metadata = create_event_metadata(
            event_type=EventType.SHIP_COMPLETED,
            run_id="run-123",
            task_id="task-456",
            agent_id="agent:0",
            session_name="session-1",
            mode=ExecutionMode.WORKTREE,
            branch="feat/test",
            target_branch="main",
            success=True,
        )
        assert metadata.branch == "feat/test"
        assert metadata.target_branch == "main"
        assert metadata.success is True
