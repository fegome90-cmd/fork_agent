"""Memory event metadata contract for structured observations.

This module defines the canonical metadata schema for events stored
in the memory system. All workflow/agent events MUST use this contract
to ensure consistent querying capabilities.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EventType(StrEnum):
    """Canonical event types for memory observations."""

    # Agent lifecycle
    AGENT_SPAWNED = "agent_spawned"
    AGENT_STOPPED = "agent_stopped"
    AGENT_HEALTH_CHECK = "agent_health_check"

    # Task lifecycle
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Workflow lifecycle
    WORKFLOW_OUTLINE = "workflow_outline"
    WORKFLOW_EXECUTE = "workflow_execute"
    WORKFLOW_VERIFY = "workflow_verify"
    WORKFLOW_SHIP = "workflow_ship"
    WORKFLOW_ABORT = "workflow_abort"

    # Ship events
    SHIP_STARTED = "ship_started"
    SHIP_COMPLETED = "ship_completed"
    SHIP_FAILED_RUNTIME = "ship_failed_runtime"
    SHIP_PREFLIGHT_FAILED = "ship_preflight_failed"
    SHIP_FORCED = "ship_forced"

    # Memory operations
    MEMORY_SAVE = "memory_save"
    MEMORY_SEARCH = "memory_search"
    MEMORY_DELETE = "memory_delete"

    # Messaging
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_IMPORTANT = "message_important"


class ExecutionMode(StrEnum):
    """Execution mode for tasks/agents."""

    WORKTREE = "worktree"
    INPLACE = "inplace"
    CHECKOUT = "checkout"


class MemoryEventMetadata(BaseModel):
    """Canonical metadata contract for memory events.

    This schema defines the REQUIRED fields that all events must include
    to enable consistent querying across the system.

    Required fields ensure:
    - Traceability (run_id, task_id, agent_id)
    - Temporal ordering (timestamp_ms)
    - Idempotency (idempotency_key)
    - Context (session_name, mode)

    Extensibility is provided via the 'extra' field and Pydantic's
    extra='allow' configuration.
    """

    # === Required Core Fields ===
    event_type: str = Field(..., description="Event type from EventType enum")
    run_id: str = Field(..., description="UUID of the current run/session")
    task_id: str = Field(..., description="Task identifier (e.g., WO-XXXX or task-uuid)")
    agent_id: str = Field(..., description="Agent identifier in session:window format")
    session_name: str = Field(..., description="Tmux session name")
    timestamp_ms: int = Field(..., description="Unix timestamp in milliseconds", ge=0)
    mode: str = Field(..., description="Execution mode from ExecutionMode enum")
    idempotency_key: str = Field(..., description="Unique key for deduplication")

    # === Optional Context Fields ===
    branch: str | None = Field(None, description="Git branch name")
    target_branch: str | None = Field(None, description="Target branch for merge/ship")
    worktree_path: str | None = Field(None, description="Path to git worktree")
    pid: int | None = Field(None, description="Process ID of agent", ge=0)
    correlation_id: str | None = Field(None, description="Correlation ID for request/response")
    parent_event_id: str | None = Field(None, description="Parent event ID for causality")

    # === Status Fields ===
    success: bool | None = Field(None, description="Operation success status")
    error_message: str | None = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retries", ge=0)

    # === Extensibility ===
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"extra": "allow", "frozen": True}

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Ensure event_type is a known type."""
        try:
            EventType(v)
        except ValueError:
            # Allow custom event types but warn via validation
            pass
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Ensure mode is a known type."""
        try:
            ExecutionMode(v)
        except ValueError:
            pass
        return v

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: str) -> str:
        """Ensure idempotency_key is not empty."""
        if not v or not v.strip():
            raise ValueError("idempotency_key cannot be empty")
        return v

    @staticmethod
    def generate_idempotency_key(
        run_id: str,
        task_id: str,
        event_type: str,
        sequence: int = 0,
    ) -> str:
        """Generate a deterministic idempotency key.

        Format: run_id:task_id:event_type:sequence

        Args:
            run_id: Run/session UUID
            task_id: Task identifier
            event_type: Event type string
            sequence: Optional sequence number for duplicate events

        Returns:
            Deterministic idempotency key
        """
        return f"{run_id}:{task_id}:{event_type}:{sequence}"


def create_event_metadata(
    event_type: EventType | str,
    run_id: str,
    task_id: str,
    agent_id: str,
    session_name: str,
    mode: ExecutionMode | str,
    **extra: Any,
) -> MemoryEventMetadata:
    """Factory function to create MemoryEventMetadata with defaults.

    This helper automatically generates timestamp and idempotency_key.

    Args:
        event_type: Type of event
        run_id: Run/session UUID
        task_id: Task identifier
        agent_id: Agent identifier
        session_name: Tmux session name
        mode: Execution mode
        **extra: Additional metadata fields

    Returns:
        MemoryEventMetadata instance
    """
    import time

    timestamp_ms = int(time.time() * 1000)
    event_type_str = event_type.value if isinstance(event_type, EventType) else event_type
    mode_str = mode.value if isinstance(mode, ExecutionMode) else mode

    idempotency_key = MemoryEventMetadata.generate_idempotency_key(
        run_id=run_id,
        task_id=task_id,
        event_type=event_type_str,
    )

    return MemoryEventMetadata(
        event_type=event_type_str,
        run_id=run_id,
        task_id=task_id,
        agent_id=agent_id,
        session_name=session_name,
        timestamp_ms=timestamp_ms,
        mode=mode_str,
        idempotency_key=idempotency_key,
        **extra,
    )
