"""Tests for TaskBoardService.retry() method (SM-C1/C2)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.exceptions import TaskTransitionError
from src.application.services.task_board_service import TaskBoardService
from src.domain.entities.orchestration_task import OrchestrationTask, OrchestrationTaskStatus


class TestRetry:
    def test_retry_resets_in_progress_to_approved(self) -> None:
        task = OrchestrationTask(id="t1", subject="s", status=OrchestrationTaskStatus.IN_PROGRESS)
        repo = MagicMock()
        repo.get_by_id.return_value = task
        service = TaskBoardService(repo=repo)
        result = service.retry("t1")
        assert result.status == OrchestrationTaskStatus.APPROVED
        repo.save.assert_called_once()

    def test_retry_raises_for_completed_task(self) -> None:
        task = OrchestrationTask(id="t1", subject="s", status=OrchestrationTaskStatus.COMPLETED)
        repo = MagicMock()
        repo.get_by_id.return_value = task
        service = TaskBoardService(repo=repo)
        with pytest.raises(TaskTransitionError, match="Cannot retry"):
            service.retry("t1")

    def test_retry_raises_for_not_found(self) -> None:
        repo = MagicMock()
        repo.get_by_id.return_value = None
        service = TaskBoardService(repo=repo)
        with pytest.raises(ValueError, match="not found"):
            service.retry("missing")

    def test_retry_raises_for_pending_task(self) -> None:
        """PENDING tasks cannot be retried — transition not allowed."""
        task = OrchestrationTask(id="t1", subject="s", status=OrchestrationTaskStatus.PENDING)
        repo = MagicMock()
        repo.get_by_id.return_value = task
        service = TaskBoardService(repo=repo)
        with pytest.raises(TaskTransitionError, match="Cannot retry"):
            service.retry("t1")
