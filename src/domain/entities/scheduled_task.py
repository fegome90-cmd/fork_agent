from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class TaskStatus(StrEnum):
    """Task status enum with string values for database persistence."""

    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ScheduledTask:
    """Immutable scheduled task entity.

    Represents a task scheduled for future execution with action,
    timing, and status tracking.

    Attributes:
        id: Unique identifier for the scheduled task.
        scheduled_at: Unix timestamp in milliseconds when task should execute.
        action: The action/command to execute.
        context: Optional context dictionary for the task.
        status: Current status of the task (PENDING, EXECUTED, CANCELLED, FAILED).
        created_at: Unix timestamp in milliseconds when task was created.
    """

    id: str
    scheduled_at: int
    action: str
    status: TaskStatus
    created_at: int
    context: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise TypeError("id debe ser un string")
        if not self.id:
            raise ValueError("id no puede estar vacío")
        if not isinstance(self.scheduled_at, int):
            raise TypeError("scheduled_at debe ser un entero")
        if self.scheduled_at < 0:
            raise ValueError("scheduled_at debe ser no negativo")
        if not isinstance(self.action, str):
            raise TypeError("action debe ser un string")
        if not self.action:
            raise ValueError("action no puede estar vacío")
        if not isinstance(self.status, TaskStatus):
            raise TypeError("status debe ser un TaskStatus")
        if not isinstance(self.created_at, int):
            raise TypeError("created_at debe ser un entero")
        if self.created_at < 0:
            raise ValueError("created_at debe ser no negativo")
        if self.context is not None and not isinstance(self.context, dict):
            raise TypeError("context debe ser un diccionario o None")
