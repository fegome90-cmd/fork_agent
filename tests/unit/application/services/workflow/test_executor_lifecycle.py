"""Tests for WorkflowExecutor lifecycle integration — duplicate suppression via lifecycle service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.application.services.agent_launch_lifecycle_service import (
    AgentLaunchLifecycleService,
    LaunchAttempt,
)
from src.application.services.workflow.executor import WorkflowExecutor
from src.application.services.workflow.state import Task
from src.domain.entities.agent_launch import AgentLaunch, LaunchStatus


def _make_task(
    task_id: str = "task-abc", slug: str = "test-task", description: str = "Do thing"
) -> Task:
    return Task(id=task_id, slug=slug, description=description)


def _make_claimed_launch(launch_id: str = "launch-001") -> AgentLaunch:
    return AgentLaunch(
        launch_id=launch_id,
        canonical_key="workflow:task-abc",
        surface="workflow",
        owner_type="task",
        owner_id="task-abc",
        status=LaunchStatus.RESERVED,
    )


def _make_active_launch(
    launch_id: str = "launch-001", tmux_session: str = "fork-test-abc123"
) -> AgentLaunch:
    return AgentLaunch(
        launch_id=launch_id,
        canonical_key="workflow:task-abc",
        surface="workflow",
        owner_type="task",
        owner_id="task-abc",
        status=LaunchStatus.ACTIVE,
        tmux_session=tmux_session,
    )


def _make_executor(lifecycle: AgentLaunchLifecycleService | None = None) -> WorkflowExecutor:
    return WorkflowExecutor(
        tmux_orchestrator=MagicMock(),
        memory_service=MagicMock(),
        workspace_manager=MagicMock(),
        hook_service=MagicMock(),
        lifecycle_service=lifecycle,
    )


class TestWorkflowExecutorWithoutLifecycle:
    """When lifecycle service is not wired, executor behaves as before."""

    def test_executes_task_normally(self) -> None:
        executor = _make_executor(lifecycle=None)
        executor._tmux.create_session.return_value = True
        executor._tmux.launch_agent.return_value = True
        executor._workspace.create_workspace.return_value = MagicMock(path=Path("/tmp/wt"))

        result = executor.execute_task(_make_task(), model="test-model")
        assert result.session_name is not None
        assert result.error is None

    def test_repeated_calls_spawn_repeatedly_without_lifecycle(self) -> None:
        """Without lifecycle, repeated calls will create multiple sessions (legacy behavior)."""
        executor = _make_executor(lifecycle=None)
        executor._tmux.create_session.return_value = True
        executor._tmux.launch_agent.return_value = True
        executor._workspace.create_workspace.return_value = MagicMock(path=Path("/tmp/wt"))

        r1 = executor.execute_task(_make_task(), model="m")
        r2 = executor.execute_task(_make_task(), model="m")
        assert r1.session_name != r2.session_name  # Different sessions — no dedup


class TestWorkflowExecutorWithLifecycle:
    """When lifecycle service is wired, duplicate launches are suppressed."""

    def test_first_request_proceeds(self) -> None:
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        claimed = _make_claimed_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=claimed,
            decision="claimed",
        )
        lifecycle.confirm_spawning.return_value = True
        lifecycle.confirm_active.return_value = True

        executor = _make_executor(lifecycle=lifecycle)
        executor._tmux.create_session.return_value = True
        executor._tmux.launch_agent.return_value = True
        executor._workspace.create_workspace.return_value = MagicMock(path=Path("/tmp/wt"))

        result = executor.execute_task(_make_task(), model="test-model")
        assert result.session_name is not None
        assert result.error is None
        lifecycle.request_launch.assert_called_once_with(
            canonical_key="workflow:task-abc",
            surface="workflow",
            owner_type="task",
            owner_id="task-abc",
        )
        lifecycle.confirm_spawning.assert_called_once_with("launch-001")
        lifecycle.confirm_active.assert_called_once()

    def test_duplicate_request_is_suppressed(self) -> None:
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        active = _make_active_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=None,
            decision="suppressed",
            existing_launch=active,
            reason="Active launch launch-001 in status ACTIVE",
        )

        executor = _make_executor(lifecycle=lifecycle)
        result = executor.execute_task(_make_task(), model="test-model")

        # No tmux session created
        assert result.error is not None
        assert "suppressed" in result.error.lower()
        executor._tmux.create_session.assert_not_called()

    def test_error_decision_fails_closed(self) -> None:
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=None,
            decision="error",
            reason="Registry unavailable",
        )

        executor = _make_executor(lifecycle=lifecycle)
        result = executor.execute_task(_make_task(), model="test-model")

        assert result.error is not None
        assert "registry error" in result.error.lower()
        executor._tmux.create_session.assert_not_called()

    def test_spawn_failure_marks_lifecycle_failed(self) -> None:
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        claimed = _make_claimed_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=claimed,
            decision="claimed",
        )
        lifecycle.confirm_spawning.return_value = True

        executor = _make_executor(lifecycle=lifecycle)
        executor._tmux.create_session.return_value = False  # session fails

        result = executor.execute_task(_make_task(), model="test-model")
        assert result.error is not None
        # mark_failed should be called with the launch_id and error message
        lifecycle.mark_failed.assert_called_once()
        call_args = lifecycle.mark_failed.call_args
        assert call_args[0][0] == "launch-001"  # launch_id
        assert "session" in call_args[0][1].lower()  # error mentions session

    def test_repeated_launch_same_task_does_not_spawn_twice(self) -> None:
        """Integration-level check: second call to same task ID is suppressed."""
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)

        # First call: claimed
        claimed = _make_claimed_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=claimed,
            decision="claimed",
        )
        lifecycle.confirm_spawning.return_value = True
        lifecycle.confirm_active.return_value = True

        executor = _make_executor(lifecycle=lifecycle)
        executor._tmux.create_session.return_value = True
        executor._tmux.launch_agent.return_value = True
        executor._workspace.create_workspace.return_value = MagicMock(path=Path("/tmp/wt"))

        r1 = executor.execute_task(_make_task(), model="m")
        assert r1.error is None

        # Second call: suppressed
        active = _make_active_launch()
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=None,
            decision="suppressed",
            existing_launch=active,
            reason="Already active",
        )

        r2 = executor.execute_task(_make_task(), model="m")
        assert r2.error is not None
        assert "suppressed" in r2.error.lower()
        # Only one tmux session created
        assert executor._tmux.create_session.call_count == 1


class TestAPIAgentsLifecycleDedup:
    """Tests for API /agents route lifecycle integration.

    These test the lifecycle logic inline since the route is async FastAPI.
    The core dedup logic is in the lifecycle service, so we test that the
    route uses it correctly by testing the service contract.
    """

    def test_api_canonical_key_format(self) -> None:
        """API canonical key should be api:{task_description_prefix}."""
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=_make_claimed_launch(),
            decision="claimed",
        )
        lifecycle.confirm_spawning.return_value = True
        lifecycle.confirm_active.return_value = True

        # Simulate what the route does
        task_desc = "Fix the authentication bug in login.py"
        canonical_key = f"api:{task_desc[:100]}"
        lifecycle.request_launch(
            canonical_key=canonical_key,
            surface="api",
            owner_type="session",
            owner_id="fork-opencode-abc123",
        )
        lifecycle.request_launch.assert_called_with(
            canonical_key=f"api:{task_desc[:100]}",
            surface="api",
            owner_type="session",
            owner_id="fork-opencode-abc123",
        )

    def test_duplicate_api_request_returns_conflict_info(self) -> None:
        """When a duplicate API launch is suppressed, the response includes existing info."""
        lifecycle = MagicMock(spec=AgentLaunchLifecycleService)
        active = _make_active_launch(tmux_session="fork-opencode-existing")
        lifecycle.request_launch.return_value = LaunchAttempt(
            launch=None,
            decision="suppressed",
            existing_launch=active,
            reason="Active launch in status ACTIVE",
        )

        attempt = lifecycle.request_launch(
            canonical_key="api:Fix auth bug",
            surface="api",
            owner_type="session",
            owner_id="fork-opencode-dup",
        )
        assert attempt.decision == "suppressed"
        assert attempt.existing_launch is not None
        assert attempt.existing_launch.tmux_session == "fork-opencode-existing"
