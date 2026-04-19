"""Scheduler service for scheduled task business logic."""

from __future__ import annotations

import time

from src.domain.entities.scheduled_task import ScheduledTask, TaskStatus
from src.domain.ports.scheduled_task_repository import ScheduledTaskRepository


class SchedulerService:
    """Service for managing scheduled tasks with business logic."""

    __slots__ = ("_repository",)

    def __init__(self, repository: ScheduledTaskRepository) -> None:
        self._repository = repository

    def create_task(
        self,
        task_id: str,
        scheduled_at: int,
        action: str,
        context: dict | None = None,
    ) -> ScheduledTask:
        task = ScheduledTask(
            id=task_id,
            scheduled_at=scheduled_at,
            action=action,
            context=context,
            status=TaskStatus.PENDING,
            created_at=int(time.time() * 1000),
        )
        self._repository.create(task)
        return task

    def get_task(self, task_id: str) -> ScheduledTask | None:
        return self._repository.get_by_id(task_id)

    def get_pending_tasks(self) -> list[ScheduledTask]:
        return self._repository.get_pending()

    def get_overdue_tasks(self) -> list[ScheduledTask]:
        current_time = int(time.time() * 1000)
        return self._repository.get_overdue(current_time)

    def mark_completed(self, task_id: str) -> None:
        self._repository.update_status(task_id, TaskStatus.EXECUTED)

    def mark_failed(self, task_id: str) -> None:
        self._repository.update_status(task_id, TaskStatus.FAILED)

    def cancel_task(self, task_id: str) -> None:
        self._repository.update_status(task_id, TaskStatus.CANCELLED)

    def delete_task(self, task_id: str) -> None:
        self._repository.delete(task_id)

    def get_all_tasks(self) -> list[ScheduledTask]:
        return self._repository.get_all()
