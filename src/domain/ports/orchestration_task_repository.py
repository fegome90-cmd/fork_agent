"""Port for orchestration task persistence."""

from __future__ import annotations

from typing import Protocol

from src.domain.entities.orchestration_task import OrchestrationTask, OrchestrationTaskStatus


class OrchestrationTaskRepository(Protocol):
    """Protocol for orchestration task persistence."""

    def save(self, task: OrchestrationTask) -> None: ...

    def cas_save(self, task: OrchestrationTask, expected_status: OrchestrationTaskStatus) -> bool:
        """Compare-and-save: persist *task* only if the current DB status matches.

        Returns True if the row was updated, False if the status guard failed
        (i.e. another writer changed the status concurrently).
        """
        ...

    def get_by_id(self, task_id: str) -> OrchestrationTask | None: ...

    def get_by_ids(self, task_ids: list[str]) -> list[OrchestrationTask]:
        """Retrieve multiple tasks by their IDs in a single query."""
        ...

    def list_by_status(self, status: OrchestrationTaskStatus) -> list[OrchestrationTask]: ...

    def list_by_owner(self, owner: str) -> list[OrchestrationTask]: ...

    def list_blocked(self) -> list[OrchestrationTask]: ...

    def list_all(self) -> list[OrchestrationTask]: ...

    def remove(self, task_id: str) -> None: ...
