"""Tests for CLI workflow commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from typer.testing import CliRunner

from src.application.services.workflow.state import (
    ExecuteState,
    PlanState,
    VerifyState,
    WorkflowPhase,
)

runner = CliRunner()


def get_app():
    from src.interfaces.cli.commands.workflow import app

    return app


class TestWorkflowOutline:
    """Tests for workflow outline command."""

    def test_outline_creates_plan_state(self, tmp_path: Path) -> None:

        plan_file = tmp_path / "plan.md"
        with patch(
            "src.interfaces.cli.commands.workflow.get_plan_state_path",
            return_value=tmp_path / "plan-state.json",
        ):
            result = runner.invoke(
                get_app(),
                ["outline", "test task", "--plan-file", str(plan_file)],
            )

        assert result.exit_code == 0
        assert "Plan created:" in result.stdout

    def test_outline_requires_task_description(self) -> None:

        result = runner.invoke(get_app(), ["outline"])

        assert result.exit_code != 0


class TestWorkflowExecute:
    """Tests for workflow execute command."""

    def test_execute_requires_plan(self, tmp_path: Path) -> None:
        from src.application.services.workflow.state import PlanState

        with (
            patch.object(PlanState, "load", return_value=None),
            patch(
                "src.interfaces.cli.commands.workflow.get_plan_state_path",
                return_value=tmp_path / "plan-state.json",
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_execute_state_path",
                return_value=tmp_path / "execute-state.json",
            ),
        ):
            result = runner.invoke(get_app(), ["execute"])

        assert result.exit_code == 1

    def test_execute_with_existing_plan(self, tmp_path: Path) -> None:

        plan_state = PlanState(session_id="test-session", phase=WorkflowPhase.OUTLINED)
        plan_path = tmp_path / "plan-state.json"
        plan_state.save(plan_path)

        with (
            patch(
                "src.interfaces.cli.commands.workflow.get_plan_state_path",
                return_value=plan_path,
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_execute_state_path",
                return_value=tmp_path / "execute-state.json",
            ),
        ):
            result = runner.invoke(get_app(), ["execute"])

        assert result.exit_code == 0
        assert "Execution started" in result.stdout


class TestWorkflowVerify:
    """Tests for workflow verify command."""

    def test_verify_requires_execute(self, tmp_path: Path) -> None:
        from src.application.services.workflow.state import ExecuteState, PlanState

        with (
            patch.object(PlanState, "load", return_value=PlanState(session_id="test")),
            patch.object(ExecuteState, "load", return_value=None),
            patch(
                "src.interfaces.cli.commands.workflow.get_plan_state_path",
                return_value=tmp_path / "plan-state.json",
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_execute_state_path",
                return_value=tmp_path / "execute-state.json",
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                return_value=tmp_path / "verify-state.json",
            ),
        ):
            result = runner.invoke(get_app(), ["verify"])

        assert result.exit_code == 1

    def test_verify_success(self, tmp_path: Path) -> None:

        plan_state = PlanState(session_id="test-session", phase=WorkflowPhase.OUTLINED)
        exec_state = ExecuteState(session_id="test-exec", phase=WorkflowPhase.EXECUTED)

        plan_path = tmp_path / "plan-state.json"
        exec_path = tmp_path / "execute-state.json"
        plan_state.save(plan_path)
        exec_state.save(exec_path)

        with (
            patch(
                "src.interfaces.cli.commands.workflow.get_plan_state_path",
                return_value=plan_path,
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_execute_state_path",
                return_value=exec_path,
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                return_value=tmp_path / "verify-state.json",
            ),
            patch(
                "src.interfaces.cli.commands.workflow.verify_runner.run",
                return_value={"passed": True, "exit_code": 0, "test_count": 1, "fail_count": 0, "duration_ms": 100},
            ),
        ):
            result = runner.invoke(get_app(), ["verify"])

        assert result.exit_code == 0
        assert "Verification complete" in result.stdout

    def test_verify_dispatches_start_and_complete_events(self, tmp_path: Path) -> None:
        from src.application.services.orchestration.events import (
            WorkflowVerifyCompleteEvent,
            WorkflowVerifyStartEvent,
        )

        plan_state = PlanState(session_id="test-session", phase=WorkflowPhase.OUTLINED)
        exec_state = ExecuteState(session_id="test-exec", phase=WorkflowPhase.EXECUTED)
        plan_path = tmp_path / "plan-state.json"
        exec_path = tmp_path / "execute-state.json"
        plan_state.save(plan_path)
        exec_state.save(exec_path)

        dispatched: list[object] = []

        with (
            patch(
                "src.interfaces.cli.commands.workflow.get_plan_state_path",
                return_value=plan_path,
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_execute_state_path",
                return_value=exec_path,
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                return_value=tmp_path / "verify-state.json",
            ),
            patch(
                "src.interfaces.cli.commands.workflow._dispatch_event",
                side_effect=lambda event, _context="", **_kwargs: dispatched.append(event),
            ),
            patch(
                "src.interfaces.cli.commands.workflow.verify_runner.run",
                return_value={"passed": True, "exit_code": 0, "test_count": 1, "fail_count": 0, "duration_ms": 100},
            ),
        ):
            result = runner.invoke(get_app(), ["verify"])

        assert result.exit_code == 0
        event_types = [type(e) for e in dispatched]
        assert WorkflowVerifyStartEvent in event_types
        assert WorkflowVerifyCompleteEvent in event_types


class TestWorkflowShip:
    """Tests for workflow ship command."""

    def test_ship_requires_verify(self, tmp_path: Path) -> None:
        from src.application.services.workflow.state import VerifyState

        with (
            patch.object(VerifyState, "load", return_value=None),
            patch(
                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                return_value=tmp_path / "verify-state.json",
            ),
        ):
            result = runner.invoke(get_app(), ["ship"])

        assert result.exit_code == 1

    def test_ship_blocked_without_unlock(self, tmp_path: Path) -> None:

        verify_state = VerifyState(session_id="test-verify", unlock_ship=False, phase=WorkflowPhase.VERIFIED)
        verify_path = tmp_path / "verify-state.json"
        verify_state.save(verify_path)

        with patch(
            "src.interfaces.cli.commands.workflow.get_verify_state_path",
            return_value=verify_path,
        ):
            result = runner.invoke(get_app(), ["ship"])

        assert result.exit_code == 1
        assert "Verification not complete" in result.output

    def test_ship_allowed_with_unlock(self, tmp_path: Path) -> None:

        verify_state = VerifyState(session_id="test-verify", unlock_ship=True, phase=WorkflowPhase.VERIFIED)
        verify_path = tmp_path / "verify-state.json"
        verify_state.save(verify_path)

        with patch(
            "src.interfaces.cli.commands.workflow.get_verify_state_path",
            return_value=verify_path,
        ):
            result = runner.invoke(get_app(), ["ship"])

        assert result.exit_code == 0
        assert "Shipping to" in result.stdout

    def test_ship_dispatches_start_and_complete_events(self, tmp_path: Path) -> None:
        from src.application.services.orchestration.events import (
            WorkflowShipCompleteEvent,
            WorkflowShipStartEvent,
        )

        verify_state = VerifyState(session_id="test-verify", unlock_ship=True, phase=WorkflowPhase.VERIFIED)
        verify_path = tmp_path / "verify-state.json"
        verify_state.save(verify_path)

        dispatched: list[object] = []

        with (
            patch(
                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                return_value=verify_path,
            ),
            patch(
                "src.interfaces.cli.commands.workflow._dispatch_event",
                side_effect=lambda event, _context="", **_kwargs: dispatched.append(event),
            ),
        ):
            result = runner.invoke(get_app(), ["ship"])

        assert result.exit_code == 0
        event_types = [type(e) for e in dispatched]
        assert WorkflowShipStartEvent in event_types
        assert WorkflowShipCompleteEvent in event_types


    def test_ship_records_preflight_failed_event(self, tmp_path: Path) -> None:
        from src.interfaces.cli.commands import workflow as workflow_module

        verify_state = VerifyState(session_id="test-verify", unlock_ship=True, phase=WorkflowPhase.VERIFIED)
        verify_path = tmp_path / "verify-state.json"
        verify_state.save(verify_path)

        events: list[tuple[str, dict[str, Any]]] = []

        preflight_error = workflow_module.ShipPreflightError(
            "dirty_worktree_cross_branch",
            current_branch="feature-x",
            target_branch="main",
            dirty_files_count=3,
            mode="no-worktree",
            reason="dirty_worktree_cross_branch",
        )

        with (
            patch(
                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                return_value=verify_path,
            ),
            patch(
                "src.interfaces.cli.commands.workflow._enforce_ship_checkout_preflight",
                side_effect=preflight_error,
            ),
            patch(
                "src.interfaces.cli.commands.workflow._record_ship_event",
                side_effect=lambda name, meta: events.append((name, meta)),
            ),
        ):
            result = runner.invoke(get_app(), ["ship", "--force", "--reason", "test", "--target", "main", "--no-worktree"])

        assert result.exit_code == 1
        assert any(name == "preflight_failed" for name, _ in events)
        assert not any(name == "completed" for name, _ in events)

    def test_ship_branch_alias_deprecated_keeps_target_metadata(self, tmp_path: Path) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        with (
            patch("src.interfaces.cli.commands.workflow._enforce_ship_checkout_preflight"),
            patch("src.interfaces.cli.commands.workflow._dispatch_event"),
            patch(
                "src.interfaces.cli.commands.workflow._record_ship_event",
                side_effect=lambda name, meta: events.append((name, meta)),
            ),
            patch("src.interfaces.cli.commands.workflow._get_current_branch", return_value="feat-branch"),
            patch("src.interfaces.cli.commands.workflow._get_dirty_files", return_value=[]),
            patch("src.interfaces.cli.commands.workflow.get_execute_state_path", return_value=tmp_path / "execute-state.json"),
        ):
            result = runner.invoke(
                get_app(),
                ["ship", "--force", "--reason", "test", "--branch", "main", "--use-worktree"],
            )

        assert result.exit_code == 0
        started_events = [meta for name, meta in events if name == "started"]
        assert started_events
        assert started_events[0]["target_branch"] == "main"

    def test_ship_use_worktree_mode_in_events(self, tmp_path: Path) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        with (
            patch("src.interfaces.cli.commands.workflow._enforce_ship_checkout_preflight"),
            patch("src.interfaces.cli.commands.workflow._dispatch_event"),
            patch("src.interfaces.cli.commands.workflow._merge_branch_via_temp_worktree"),
            patch(
                "src.interfaces.cli.commands.workflow._record_ship_event",
                side_effect=lambda name, meta: events.append((name, meta)),
            ),
            patch("src.interfaces.cli.commands.workflow._get_current_branch", return_value="feat-branch"),
            patch("src.interfaces.cli.commands.workflow._get_dirty_files", return_value=["a.py", "b.py"]),
            patch("src.interfaces.cli.commands.workflow.get_execute_state_path", return_value=tmp_path / "execute-state.json"),
        ):
            result = runner.invoke(
                get_app(),
                ["ship", "--force", "--reason", "test", "--target", "main", "--use-worktree"],
            )

        assert result.exit_code == 0
        started_events = [meta for name, meta in events if name == "started"]
        completed_events = [meta for name, meta in events if name == "completed"]
        assert started_events and completed_events
        assert started_events[0]["mode"] == "worktree"
        assert started_events[0]["dirty_files_count"] == 2
        assert completed_events[0]["mode"] == "worktree"
        assert completed_events[0]["dirty_files_count"] == 2


class TestWorkflowStatus:
    """Tests for workflow status command."""

    def test_status_all_none(self, tmp_path: Path) -> None:
        from src.application.services.workflow.state import (
            ExecuteState,
            PlanState,
            VerifyState,
        )

        with (
            patch.object(PlanState, "load", return_value=None),
            patch.object(ExecuteState, "load", return_value=None),
            patch.object(VerifyState, "load", return_value=None),
            patch(
                "src.interfaces.cli.commands.workflow.get_plan_state_path",
                return_value=tmp_path / "plan-state.json",
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_execute_state_path",
                return_value=tmp_path / "execute-state.json",
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                return_value=tmp_path / "verify-state.json",
            ),
        ):
            result = runner.invoke(get_app(), ["status"])

        assert result.exit_code == 0
        assert "Workflow Status" in result.stdout

    def test_status_with_plan(self, tmp_path: Path) -> None:

        plan_state = PlanState(session_id="test-plan", phase=WorkflowPhase.OUTLINED)
        plan_path = tmp_path / "plan-state.json"
        plan_state.save(plan_path)

        with (
            patch.object(PlanState, "load", return_value=plan_state),
            patch.object(ExecuteState, "load", return_value=None),
            patch.object(VerifyState, "load", return_value=None),
            patch(
                "src.interfaces.cli.commands.workflow.get_plan_state_path",
                return_value=plan_path,
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_execute_state_path",
                return_value=tmp_path / "execute-state.json",
            ),
            patch(
                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                return_value=tmp_path / "verify-state.json",
            ),
        ):
            result = runner.invoke(get_app(), ["status"])

        assert result.exit_code == 0
        assert "Plan:" in result.stdout
