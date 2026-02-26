"""Tests for WorkflowExecutor service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.workflow.executor import (
    CleanupResult,
    ExecutionResult,
    TaskExecutionResult,
    WorkflowExecutor,
    TASK_STATUS_EXECUTING,
    TASK_STATUS_PENDING,
)
from src.application.services.workflow.state import (
    ExecuteState,
    PlanState,
    Task,
    WorkflowPhase,
)
from src.application.services.workspace.entities import (
    LayoutType,
    Workspace,
    WorktreeState,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_tmux() -> MagicMock:
    """Create a mock TmuxOrchestrator."""
    mock = MagicMock()
    mock.create_session.return_value = True
    mock.launch_agent.return_value = True
    return mock


@pytest.fixture
def mock_memory() -> MagicMock:
    """Create a mock MemoryService."""
    mock = MagicMock()
    mock.save.return_value = MagicMock(id="obs-123")
    return mock


@pytest.fixture
def mock_workspace() -> MagicMock:
    """Create a mock WorkspaceManager."""
    mock = MagicMock()
    mock.create_workspace.return_value = Workspace(
        name="task-test-feature",
        path=Path("/tmp/worktrees/task-test-feature"),
        layout=LayoutType.NESTED,
        state=WorktreeState.ACTIVE,
        repo_root=Path("/tmp/repo"),
    )
    mock.merge_workspace.return_value = None
    mock.remove_workspace.return_value = None
    return mock


@pytest.fixture
def mock_hooks() -> MagicMock:
    """Create a mock HookService."""
    mock = MagicMock()
    mock.dispatch.return_value = None
    return mock


@pytest.fixture
def executor(
    mock_tmux: MagicMock,
    mock_memory: MagicMock,
    mock_workspace: MagicMock,
    mock_hooks: MagicMock,
) -> WorkflowExecutor:
    """Create a WorkflowExecutor with mocked dependencies."""
    return WorkflowExecutor(
        tmux_orchestrator=mock_tmux,
        memory_service=mock_memory,
        workspace_manager=mock_workspace,
        hook_service=mock_hooks,
    )


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id="task-001",
        slug="implement-user-auth",
        description="Implement user authentication with JWT tokens",
        status=TASK_STATUS_PENDING,
    )


@pytest.fixture
def sample_plan(sample_task: Task) -> PlanState:
    """Create a sample plan for testing."""
    return PlanState(
        session_id="plan-abc123",
        status="outlined",
        phase=WorkflowPhase.OUTLINED,
        tasks=[sample_task],
    )


# =============================================================================
# Test TaskExecutionResult
# =============================================================================


class TestTaskExecutionResult:
    """Tests for TaskExecutionResult dataclass."""

    def test_create_minimal_result(self, sample_task: Task) -> None:
        """Test creating a minimal result with only task."""
        result = TaskExecutionResult(task=sample_task)
        assert result.task == sample_task
        assert result.session_name is None
        assert result.worktree_path is None
        assert result.worktree_name is None
        assert result.error is None

    def test_create_full_result(self, sample_task: Task) -> None:
        """Test creating a result with all fields."""
        result = TaskExecutionResult(
            task=sample_task,
            session_name="fork-test-abc123",
            worktree_path="/tmp/worktrees/task-test",
            worktree_name="task-test",
            error=None,
        )
        assert result.session_name == "fork-test-abc123"
        assert result.worktree_path == "/tmp/worktrees/task-test"
        assert result.worktree_name == "task-test"

    def test_result_is_frozen(self, sample_task: Task) -> None:
        """Test that TaskExecutionResult is immutable."""
        result = TaskExecutionResult(task=sample_task)
        with pytest.raises(AttributeError):
            result.session_name = "new-session"  # type: ignore


# =============================================================================
# Test ExecutionResult
# =============================================================================


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_create_minimal_result(self) -> None:
        """Test creating a minimal execution result."""
        exec_state = ExecuteState(session_id="exec-123")
        result = ExecutionResult(exec_state=exec_state)
        assert result.exec_state == exec_state
        assert result.spawned_sessions == ()
        assert result.worktrees_created == ()
        assert result.errors == ()

    def test_create_full_result(self) -> None:
        """Test creating a result with all fields."""
        exec_state = ExecuteState(session_id="exec-123", status=TASK_STATUS_EXECUTING)
        result = ExecutionResult(
            exec_state=exec_state,
            spawned_sessions=("session-1", "session-2"),
            worktrees_created=("worktree-1",),
            errors=("Error 1",),
        )
        assert len(result.spawned_sessions) == 2
        assert len(result.worktrees_created) == 1
        assert len(result.errors) == 1


# =============================================================================
# Test CleanupResult
# =============================================================================


class TestCleanupResult:
    """Tests for CleanupResult dataclass."""

    def test_create_success_result(self) -> None:
        """Test creating a successful cleanup result."""
        result = CleanupResult(
            worktree_name="task-test",
            merged=True,
            removed=True,
        )
        assert result.merged is True
        assert result.removed is True
        assert result.error is None

    def test_create_partial_failure_result(self) -> None:
        """Test creating a result with partial failure."""
        result = CleanupResult(
            worktree_name="task-test",
            merged=True,
            removed=False,
            error="Remove failed: permission denied",
        )
        assert result.merged is True
        assert result.removed is False
        assert "permission denied" in result.error  # type: ignore


# =============================================================================
# Test WorkflowExecutor.execute_task
# =============================================================================


class TestExecuteTask:
    """Tests for WorkflowExecutor.execute_task method."""

    def test_execute_task_success(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
        mock_tmux: MagicMock,
        mock_workspace: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Test successful task execution."""
        result = executor.execute_task(sample_task, model="opencode/glm-5-free")

        assert result.error is None
        assert result.session_name is not None
        assert result.worktree_name is not None
        assert "fork-" in result.session_name
        assert "task-implement-user-auth" == result.worktree_name

        # Verify tmux calls
        mock_tmux.create_session.assert_called_once()
        mock_tmux.launch_agent.assert_called_once()

        # Verify workspace creation
        mock_workspace.create_workspace.assert_called_once()

        # Verify event dispatch
        mock_hooks.dispatch.assert_called_once()

    def test_execute_task_with_custom_session_name(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
        mock_tmux: MagicMock,
    ) -> None:
        """Test task execution with custom session name."""
        result = executor.execute_task(
            sample_task,
            model="opencode/glm-5-free",
            session_name="custom-session-name",
        )

        assert result.session_name == "custom-session-name"
        mock_tmux.create_session.assert_called_once_with("custom-session-name")

    def test_execute_task_tmux_failure(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
        mock_tmux: MagicMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Test task execution when tmux session creation fails."""
        mock_tmux.create_session.return_value = False

        result = executor.execute_task(sample_task, model="opencode/glm-5-free")

        assert result.session_name is None
        assert result.error is not None
        assert "Failed to create tmux session" in result.error

        # Worktree should still be created
        mock_workspace.create_workspace.assert_called_once()

    def test_execute_task_tmux_exception(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
        mock_tmux: MagicMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Test task execution when tmux raises exception."""
        mock_tmux.create_session.side_effect = RuntimeError("Tmux not available")

        result = executor.execute_task(sample_task, model="opencode/glm-5-free")

        assert result.session_name is None
        assert result.error is not None
        assert "Error creating tmux session" in result.error
        assert "Tmux not available" in result.error

    def test_execute_task_worktree_failure(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
        mock_workspace: MagicMock,
    ) -> None:
        """Test task execution when worktree creation fails."""
        mock_workspace.create_workspace.side_effect = RuntimeError("Git error")

        result = executor.execute_task(sample_task, model="opencode/glm-5-free")

        assert result.worktree_name is None
        assert result.error is not None
        assert "Failed to create worktree" in result.error

    def test_execute_task_both_failures(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
        mock_tmux: MagicMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Test task execution when both tmux and worktree fail."""
        mock_tmux.create_session.return_value = False
        mock_workspace.create_workspace.side_effect = RuntimeError("Git error")

        result = executor.execute_task(sample_task, model="opencode/glm-5-free")

        assert result.session_name is None
        assert result.worktree_name is None
        assert result.error is not None
        assert "Failed to create tmux session" in result.error
        assert "Failed to create worktree" in result.error

    def test_execute_task_truncates_long_slug(
        self,
        executor: WorkflowExecutor,
        mock_tmux: MagicMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Test that long slugs are truncated properly."""
        long_slug_task = Task(
            id="task-002",
            slug="this-is-a-very-long-slug-that-should-be-truncated",
            description="Task with long slug",
        )

        result = executor.execute_task(long_slug_task, model="opencode/glm-5-free")

        # Session name should have truncated slug (20 chars)
        assert len(result.session_name) < 50  # fork-<20 chars>-<8 hex>
        # Worktree name should have truncated slug (30 chars)
        assert result.worktree_name is not None
        assert len(result.worktree_name) <= 35  # task-<30 chars>


# =============================================================================
# Test WorkflowExecutor.execute_plan
# =============================================================================


class TestExecutePlan:
    """Tests for WorkflowExecutor.execute_plan method."""

    def test_execute_plan_single_task(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
        mock_tmux: MagicMock,
        mock_workspace: MagicMock,
        mock_hooks: MagicMock,
        mock_memory: MagicMock,
    ) -> None:
        """Test executing a plan with a single task."""
        result = executor.execute_plan(sample_plan)

        assert result.errors == ()
        assert len(result.spawned_sessions) == 1
        assert len(result.worktrees_created) == 1
        assert result.exec_state.status == TASK_STATUS_EXECUTING

        # Verify events dispatched
        assert mock_hooks.dispatch.call_count >= 2  # start + complete + worktree

    def test_execute_plan_multiple_tasks(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
        mock_tmux: MagicMock,
        mock_workspace: MagicMock,
    ) -> None:
        """Test executing a plan with multiple tasks."""
        task2 = Task(
            id="task-002",
            slug="add-unit-tests",
            description="Add comprehensive unit tests",
        )
        sample_plan.tasks.append(task2)

        result = executor.execute_plan(sample_plan)

        assert len(result.spawned_sessions) == 2
        assert len(result.worktrees_created) == 2
        assert len(result.exec_state.tasks) == 2

    def test_execute_plan_sequential(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
        mock_tmux: MagicMock,
    ) -> None:
        """Test sequential execution (default)."""
        result = executor.execute_plan(sample_plan, parallel=False)

        assert len(result.spawned_sessions) == 1
        # Verify tasks were executed in order
        assert mock_tmux.create_session.call_count == 1

    def test_execute_plan_parallel(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
        mock_tmux: MagicMock,
    ) -> None:
        """Test parallel execution."""
        task2 = Task(
            id="task-002",
            slug="add-integration-tests",
            description="Add integration tests",
        )
        sample_plan.tasks.append(task2)

        result = executor.execute_plan(sample_plan, parallel=True)

        assert len(result.spawned_sessions) == 2
        assert mock_tmux.create_session.call_count == 2

    def test_execute_plan_specific_task(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
        mock_tmux: MagicMock,
    ) -> None:
        """Test executing a specific task by ID."""
        task2 = Task(
            id="task-002",
            slug="add-docs",
            description="Add documentation",
        )
        sample_plan.tasks.append(task2)

        result = executor.execute_plan(sample_plan, task_id="task-002")

        assert len(result.spawned_sessions) == 1
        assert result.exec_state.tasks[0].id == "task-002"

    def test_execute_plan_nonexistent_task(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
        mock_tmux: MagicMock,
    ) -> None:
        """Test executing a nonexistent task ID returns empty result."""
        result = executor.execute_plan(sample_plan, task_id="nonexistent-id")

        assert len(result.spawned_sessions) == 0
        assert len(result.exec_state.tasks) == 0

    def test_execute_plan_custom_model(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
        mock_tmux: MagicMock,
    ) -> None:
        """Test executing with custom model."""
        result = executor.execute_plan(sample_plan, model="custom-model")

        assert len(result.spawned_sessions) == 1
        # Verify model was passed to launch_agent
        call_args = mock_tmux.launch_agent.call_args
        assert call_args[0][2] == "custom-model"

    def test_execute_plan_memory_persistence(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
        mock_memory: MagicMock,
    ) -> None:
        """Test that execution is persisted to memory."""
        executor.execute_plan(sample_plan)

        mock_memory.save.assert_called_once()
        call_args = mock_memory.save.call_args
        assert "workflow:execute:" in call_args[1]["content"]
        assert call_args[1]["metadata"]["phase"] == "execute"

    def test_execute_plan_memory_failure_logged(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
        mock_memory: MagicMock,
    ) -> None:
        """Test that memory persistence failure is logged but doesn't fail."""
        mock_memory.save.side_effect = RuntimeError("DB error")

        # Should not raise
        result = executor.execute_plan(sample_plan)
        assert result is not None

    def test_execute_plan_updates_task_status(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
    ) -> None:
        """Test that task status is updated to executing."""
        result = executor.execute_plan(sample_plan)

        assert result.exec_state.tasks[0].status == TASK_STATUS_EXECUTING

    def test_execute_plan_preserves_task_status_on_failure(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
        mock_tmux: MagicMock,
    ) -> None:
        """Test that task status is preserved when session creation fails."""
        mock_tmux.create_session.return_value = False

        result = executor.execute_plan(sample_plan)

        # Status should remain as original (pending) since no session was created
        assert result.exec_state.tasks[0].status == TASK_STATUS_PENDING


# =============================================================================
# Test WorkflowExecutor.cleanup_worktree
# =============================================================================


class TestCleanupWorktree:
    """Tests for WorkflowExecutor.cleanup_worktree method."""

    def test_cleanup_success(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
        mock_workspace: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Test successful worktree cleanup."""
        task_with_worktree = Task(
            id="task-001",
            slug="test-feature",
            description="Test",
            worktree_path="/tmp/worktrees/task-test",
            branch="task-test-feature",
        )

        result = executor.cleanup_worktree(task_with_worktree)

        assert result.merged is True
        assert result.removed is True
        assert result.error is None

        mock_workspace.merge_workspace.assert_called_once()
        mock_workspace.remove_workspace.assert_called_once()

        # Verify events dispatched
        assert mock_hooks.dispatch.call_count >= 2  # merged + removed

    def test_cleanup_no_worktree_path(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
    ) -> None:
        """Test cleanup when task has no worktree path."""
        result = executor.cleanup_worktree(sample_task)

        assert result.merged is False
        assert result.removed is False
        assert result.error == "No worktree path found"

    def test_cleanup_merge_only(
        self,
        executor: WorkflowExecutor,
        mock_workspace: MagicMock,
    ) -> None:
        """Test cleanup with merge but no remove."""
        task_with_worktree = Task(
            id="task-001",
            slug="test",
            description="Test",
            worktree_path="/tmp/worktrees/task-test",
            branch="task-test",
        )

        mock_workspace.remove_workspace.side_effect = RuntimeError("Remove failed")

        result = executor.cleanup_worktree(task_with_worktree, merge=True)

        assert result.merged is True
        assert result.removed is False
        assert "Remove failed" in result.error  # type: ignore

    def test_cleanup_remove_only(
        self,
        executor: WorkflowExecutor,
        mock_workspace: MagicMock,
    ) -> None:
        """Test cleanup without merge."""
        task_with_worktree = Task(
            id="task-001",
            slug="test",
            description="Test",
            worktree_path="/tmp/worktrees/task-test",
            branch="task-test",
        )

        result = executor.cleanup_worktree(task_with_worktree, merge=False)

        assert result.merged is False
        assert result.removed is True
        mock_workspace.merge_workspace.assert_not_called()

    def test_cleanup_custom_target_branch(
        self,
        executor: WorkflowExecutor,
        mock_workspace: MagicMock,
    ) -> None:
        """Test cleanup with custom target branch."""
        task_with_worktree = Task(
            id="task-001",
            slug="test",
            description="Test",
            worktree_path="/tmp/worktrees/task-test",
            branch="task-test",
        )

        result = executor.cleanup_worktree(
            task_with_worktree,
            merge=True,
            target_branch="develop",
        )

        assert result.merged is True
        mock_workspace.merge_workspace.assert_called_once_with(
            "task-test",
            target_branch="develop",
            delete_branch=False,
        )

    def test_cleanup_merge_failure(
        self,
        executor: WorkflowExecutor,
        mock_workspace: MagicMock,
    ) -> None:
        """Test cleanup when merge fails."""
        task_with_worktree = Task(
            id="task-001",
            slug="test",
            description="Test",
            worktree_path="/tmp/worktrees/task-test",
            branch="task-test",
        )

        mock_workspace.merge_workspace.side_effect = RuntimeError("Merge conflict")

        result = executor.cleanup_worktree(task_with_worktree)

        assert result.merged is False
        assert result.removed is True  # Remove should still be attempted
        assert "Merge failed" in result.error  # type: ignore

    def test_cleanup_both_failures(
        self,
        executor: WorkflowExecutor,
        mock_workspace: MagicMock,
    ) -> None:
        """Test cleanup when both merge and remove fail."""
        task_with_worktree = Task(
            id="task-001",
            slug="test",
            description="Test",
            worktree_path="/tmp/worktrees/task-test",
            branch="task-test",
        )

        mock_workspace.merge_workspace.side_effect = RuntimeError("Merge conflict")
        mock_workspace.remove_workspace.side_effect = RuntimeError("Remove failed")

        result = executor.cleanup_worktree(task_with_worktree)

        assert result.merged is False
        assert result.removed is False
        assert "Merge failed" in result.error  # type: ignore
        assert "Remove failed" in result.error  # type: ignore

    def test_cleanup_uses_task_branch_if_no_branch_field(
        self,
        executor: WorkflowExecutor,
        mock_workspace: MagicMock,
    ) -> None:
        """Test cleanup derives worktree name from slug if branch not set."""
        task_no_branch = Task(
            id="task-001",
            slug="my-feature",
            description="Test",
            worktree_path="/tmp/worktrees/task-my-feature",
            branch=None,
        )

        result = executor.cleanup_worktree(task_no_branch)

        # Should derive worktree_name from slug
        assert result.worktree_name == "task-my-feature"

    def test_cleanup_dispatch_failure_logged(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
        mock_hooks: MagicMock,
    ) -> None:
        """Test that dispatch failure is logged but doesn't fail cleanup."""
        mock_hooks.dispatch.side_effect = RuntimeError("Hook error")

        task_with_worktree = Task(
            id="task-001",
            slug="test",
            description="Test",
            worktree_path="/tmp/worktrees/task-test",
            branch="task-test",
        )

        # Should not raise
        result = executor.cleanup_worktree(task_with_worktree)
        assert result is not None


# =============================================================================
# Test WorkflowExecutor.cleanup_all_worktrees
# =============================================================================


class TestCleanupAllWorktrees:
    """Tests for WorkflowExecutor.cleanup_all_worktrees method."""

    def test_cleanup_all_success(
        self,
        executor: WorkflowExecutor,
        mock_workspace: MagicMock,
    ) -> None:
        """Test cleaning up multiple worktrees."""
        tasks = (
            Task(
                id="task-001",
                slug="feature-1",
                description="Feature 1",
                worktree_path="/tmp/wt1",
                branch="task-feature-1",
            ),
            Task(
                id="task-002",
                slug="feature-2",
                description="Feature 2",
                worktree_path="/tmp/wt2",
                branch="task-feature-2",
            ),
        )

        results = executor.cleanup_all_worktrees(tasks)

        assert len(results) == 2
        assert all(r.merged and r.removed for r in results)

    def test_cleanup_all_skips_tasks_without_worktree(
        self,
        executor: WorkflowExecutor,
    ) -> None:
        """Test that tasks without worktree are skipped."""
        tasks = (
            Task(
                id="task-001",
                slug="feature-1",
                description="Feature 1",
                worktree_path="/tmp/wt1",
                branch="task-feature-1",
            ),
            Task(
                id="task-002",
                slug="feature-2",
                description="Feature 2",
                worktree_path=None,
                branch=None,
            ),
        )

        results = executor.cleanup_all_worktrees(tasks)

        assert len(results) == 1
        assert results[0].worktree_name == "task-feature-1"

    def test_cleanup_all_empty_tasks(
        self,
        executor: WorkflowExecutor,
    ) -> None:
        """Test cleanup with empty task list."""
        results = executor.cleanup_all_worktrees(())
        assert results == ()

    def test_cleanup_all_custom_target_branch(
        self,
        executor: WorkflowExecutor,
        mock_workspace: MagicMock,
    ) -> None:
        """Test cleanup all with custom target branch."""
        tasks = (
            Task(
                id="task-001",
                slug="feature",
                description="Feature",
                worktree_path="/tmp/wt",
                branch="task-feature",
            ),
        )

        executor.cleanup_all_worktrees(tasks, merge=True, target_branch="develop")

        mock_workspace.merge_workspace.assert_called_once_with(
            "task-feature",
            target_branch="develop",
            delete_branch=False,
        )


# =============================================================================
# Test Helper Methods
# =============================================================================


class TestHelperMethods:
    """Tests for private helper methods."""

    def test_collect_result_data(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
    ) -> None:
        """Test _collect_result_data helper."""
        result = TaskExecutionResult(
            task=sample_task,
            session_name="session-1",
            worktree_name="worktree-1",
            error="Some error",
        )

        sessions: list[str] = []
        worktrees: list[str] = []
        errors: list[str] = []

        executor._collect_result_data(result, sessions, worktrees, errors)

        assert sessions == ["session-1"]
        assert worktrees == ["worktree-1"]
        assert errors == ["Some error"]

    def test_collect_result_data_partial(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
    ) -> None:
        """Test _collect_result_data with partial data."""
        result = TaskExecutionResult(
            task=sample_task,
            session_name="session-1",
            worktree_name=None,
            error=None,
        )

        sessions: list[str] = []
        worktrees: list[str] = []
        errors: list[str] = []

        executor._collect_result_data(result, sessions, worktrees, errors)

        assert sessions == ["session-1"]
        assert worktrees == []
        assert errors == []

    def test_create_updated_task(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
    ) -> None:
        """Test _create_updated_task helper."""
        result = TaskExecutionResult(
            task=sample_task,
            session_name="session-1",
            worktree_path="/tmp/wt",
            worktree_name="task-test",
        )

        updated = executor._create_updated_task(result)

        assert updated.id == sample_task.id
        assert updated.status == TASK_STATUS_EXECUTING
        assert updated.session_name == "session-1"
        assert updated.worktree_path == "/tmp/wt"
        assert updated.branch == "task-test"

    def test_create_updated_task_no_session(
        self,
        executor: WorkflowExecutor,
        sample_task: Task,
    ) -> None:
        """Test _create_updated_task when no session created."""
        result = TaskExecutionResult(
            task=sample_task,
            session_name=None,
            worktree_path=None,
            worktree_name=None,
        )

        updated = executor._create_updated_task(result)

        assert updated.status == TASK_STATUS_PENDING
        assert updated.session_name is None

    def test_dispatch_event_success(
        self,
        executor: WorkflowExecutor,
        mock_hooks: MagicMock,
    ) -> None:
        """Test _dispatch_event successful dispatch."""
        from src.application.services.orchestration.events import WorktreeCreatedEvent

        event = WorktreeCreatedEvent(
            workspace_name="test",
            worktree_path="/tmp/test",
        )

        executor._dispatch_event(event)

        mock_hooks.dispatch.assert_called_once_with(event)

    def test_dispatch_event_failure_logged(
        self,
        executor: WorkflowExecutor,
        mock_hooks: MagicMock,
    ) -> None:
        """Test _dispatch_event handles failures gracefully."""
        from src.application.services.orchestration.events import WorktreeCreatedEvent

        mock_hooks.dispatch.side_effect = RuntimeError("Hook failed")

        event = WorktreeCreatedEvent(
            workspace_name="test",
            worktree_path="/tmp/test",
        )

        # Should not raise
        executor._dispatch_event(event)

        mock_hooks.dispatch.assert_called_once()


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_plan(
        self,
        executor: WorkflowExecutor,
    ) -> None:
        """Test executing an empty plan."""
        empty_plan = PlanState(
            session_id="empty-plan",
            tasks=[],
        )

        result = executor.execute_plan(empty_plan)

        assert len(result.spawned_sessions) == 0
        assert len(result.exec_state.tasks) == 0

    def test_task_with_empty_slug(
        self,
        executor: WorkflowExecutor,
        mock_tmux: MagicMock,
    ) -> None:
        """Test task with empty slug."""
        task = Task(
            id="task-001",
            slug="",
            description="Task with empty slug",
        )

        result = executor.execute_task(task, model="test-model")

        # Should still work with empty slug
        assert result.session_name is not None
        assert "fork--" in result.session_name  # fork-{empty}-{uuid}

    def test_task_with_unicode_description(
        self,
        executor: WorkflowExecutor,
        mock_tmux: MagicMock,
    ) -> None:
        """Test task with unicode in description."""
        task = Task(
            id="task-001",
            slug="unicode-task",
            description="Implementación de autenticación 中文 🚀",
        )

        result = executor.execute_task(task, model="test-model")

        assert result.error is None
        # Verify unicode was passed to launch_agent
        call_args = mock_tmux.launch_agent.call_args
        assert "autenticación" in call_args[0][3]

    def test_concurrent_session_names_unique(
        self,
        executor: WorkflowExecutor,
        sample_plan: PlanState,
    ) -> None:
        """Test that concurrent executions generate unique session names."""
        task2 = Task(
            id="task-002",
            slug="same-slug",  # Same slug as first task
            description="Another task",
        )
        sample_plan.tasks = [sample_plan.tasks[0], task2]

        result = executor.execute_plan(sample_plan, parallel=True)

        # Session names should be unique due to UUID
        session_names = result.spawned_sessions
        assert len(set(session_names)) == len(session_names)
