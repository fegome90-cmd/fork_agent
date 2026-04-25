"""Poll run entity for autonomous agent polling."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PollRunStatus(StrEnum):
    """Status of an autonomous poll run."""

    QUEUED = "QUEUED"
    SPAWNING = "SPAWNING"
    RUNNING = "RUNNING"
    TERMINATING = "TERMINATING"
    QUARANTINED = "QUARANTINED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


_VALID_TRANSITIONS: dict[PollRunStatus, set[PollRunStatus]] = {
    PollRunStatus.QUEUED: {
        PollRunStatus.SPAWNING,
        PollRunStatus.CANCELLED,
        PollRunStatus.QUARANTINED,
    },
    PollRunStatus.SPAWNING: {
        PollRunStatus.RUNNING,
        PollRunStatus.QUARANTINED,
        PollRunStatus.FAILED,
        PollRunStatus.CANCELLED,
    },
    PollRunStatus.RUNNING: {
        PollRunStatus.TERMINATING,
        PollRunStatus.COMPLETED,
        PollRunStatus.FAILED,
        PollRunStatus.CANCELLED,
    },
    PollRunStatus.TERMINATING: {
        PollRunStatus.COMPLETED,
        PollRunStatus.FAILED,
        PollRunStatus.CANCELLED,
    },
    PollRunStatus.QUARANTINED: {PollRunStatus.CANCELLED},
    PollRunStatus.COMPLETED: set(),
    PollRunStatus.FAILED: set(),
    PollRunStatus.CANCELLED: set(),
}


@dataclass(frozen=True)
class PollRun:
    """Immutable poll run entity tracking autonomous agent execution.

    Attributes:
        id: Unique identifier (UUID4 hex).
        task_id: Reference to the OrchestrationTask being executed.
        agent_name: Name of the agent assigned to this run.
        status: Current run status.
        started_at: Unix epoch milliseconds when run started, or None.
        ended_at: Unix epoch milliseconds when run ended, or None.
        poll_run_dir: Path to the run directory, or None.
        error_message: Error details if failed, or None.
    """

    id: str
    task_id: str
    agent_name: str
    status: PollRunStatus
    started_at: int | None = None
    ended_at: int | None = None
    poll_run_dir: str | None = None
    error_message: str | None = None
    launch_method: str | None = None
    launch_pane_id: str | None = None
    launch_pid: int | None = None
    launch_pgid: int | None = None
    launch_recorded_at: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("id must be a non-empty string")
        if not isinstance(self.task_id, str) or not self.task_id:
            raise ValueError("task_id must be a non-empty string")
        if not isinstance(self.agent_name, str) or not self.agent_name:
            raise ValueError("agent_name must be a non-empty string")
        if not isinstance(self.status, PollRunStatus):
            raise TypeError("status must be a PollRunStatus")
        if self.started_at is not None and self.started_at < 0:
            raise ValueError("started_at must be non-negative")
        if self.ended_at is not None and self.ended_at < 0:
            raise ValueError("ended_at must be non-negative")
        if self.launch_pid is not None and self.launch_pid < 0:
            raise ValueError("launch_pid must be non-negative")
        if self.launch_pgid is not None and self.launch_pgid < 0:
            raise ValueError("launch_pgid must be non-negative")
        if self.launch_recorded_at is not None and self.launch_recorded_at < 0:
            raise ValueError("launch_recorded_at must be non-negative")

    def can_transition_to(self, target: PollRunStatus) -> bool:
        """Check if transitioning to target status is allowed."""
        return target in _VALID_TRANSITIONS.get(self.status, set())
