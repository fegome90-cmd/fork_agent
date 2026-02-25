"""Tests for CLI workflow commands."""

from __future__ import annotations

import tempfile
from pathlib import Path
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
        from src.interfaces.cli.commands.workflow import app

        plan_file = tmp_path / "plan.md"
        with patch(
            "src.interfaces.cli.commands.workflow.get_plan_state_path",
            return_value=tmp_path / "plan-state.json",
        ):
            result = runner.invoke(get_app(),
                ["outline", "test task", "--plan-file", str(plan_file)],
            )

        assert result.exit_code == 0
        assert "Plan created:" in result.stdout

    def test_outline_requires_task_description(self) -> None:
        from src.interfaces.cli.commands.workflow import app

        result = runner.invoke(get_app(), ["outline"])

        assert result.exit_code != 0


class TestWorkflowExecute:
    """Tests for workflow execute command."""

    def test_execute_requires_plan(self, tmp_path: Path) -> None:
        from src.application.services.workflow.state import PlanState

        with patch.object(PlanState, "load", return_value=None):
            with patch(
                "src.interfaces.cli.commands.workflow.get_plan_state_path",
                return_value=tmp_path / "plan-state.json",
            ):
                with patch(
                    "src.interfaces.cli.commands.workflow.get_execute_state_path",
                    return_value=tmp_path / "execute-state.json",
                ):
                    result = runner.invoke(get_app(), ["execute"])

        assert result.exit_code == 1

    def test_execute_with_existing_plan(self, tmp_path: Path) -> None:
        from src.interfaces.cli.commands.workflow import app

        plan_state = PlanState(session_id="test-session", phase=WorkflowPhase.OUTLINED)
        plan_path = tmp_path / "plan-state.json"
        plan_state.save(plan_path)

        with patch(
            "src.interfaces.cli.commands.workflow.get_plan_state_path",
            return_value=plan_path,
        ):
            with patch(
                "src.interfaces.cli.commands.workflow.get_execute_state_path",
                return_value=tmp_path / "execute-state.json",
            ):
                result = runner.invoke(get_app(), ["execute"])

        assert result.exit_code == 0
        assert "Execution started" in result.stdout


class TestWorkflowVerify:
    """Tests for workflow verify command."""

    def test_verify_requires_execute(self, tmp_path: Path) -> None:
        from src.application.services.workflow.state import ExecuteState, PlanState

        with patch.object(PlanState, "load", return_value=PlanState(session_id="test")):
            with patch.object(ExecuteState, "load", return_value=None):
                with patch(
                    "src.interfaces.cli.commands.workflow.get_plan_state_path",
                    return_value=tmp_path / "plan-state.json",
                ):
                    with patch(
                        "src.interfaces.cli.commands.workflow.get_execute_state_path",
                        return_value=tmp_path / "execute-state.json",
                    ):
                        with patch(
                            "src.interfaces.cli.commands.workflow.get_verify_state_path",
                            return_value=tmp_path / "verify-state.json",
                        ):
                            result = runner.invoke(get_app(), ["verify"])

        assert result.exit_code == 1

    def test_verify_success(self, tmp_path: Path) -> None:
        from src.interfaces.cli.commands.workflow import app

        plan_state = PlanState(session_id="test-session", phase=WorkflowPhase.OUTLINED)
        exec_state = ExecuteState(session_id="test-exec", phase=WorkflowPhase.EXECUTING)

        plan_path = tmp_path / "plan-state.json"
        exec_path = tmp_path / "execute-state.json"
        plan_state.save(plan_path)
        exec_state.save(exec_path)

        with patch(
            "src.interfaces.cli.commands.workflow.get_plan_state_path",
            return_value=plan_path,
        ):
            with patch(
                "src.interfaces.cli.commands.workflow.get_execute_state_path",
                return_value=exec_path,
            ):
                with patch(
                    "src.interfaces.cli.commands.workflow.get_verify_state_path",
                    return_value=tmp_path / "verify-state.json",
                ):
                    result = runner.invoke(get_app(), ["verify"])

        assert result.exit_code == 0
        assert "Verification complete" in result.stdout


class TestWorkflowShip:
    """Tests for workflow ship command."""

    def test_ship_requires_verify(self, tmp_path: Path) -> None:
        from src.application.services.workflow.state import VerifyState

        with patch.object(VerifyState, "load", return_value=None):
            with patch(
                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                return_value=tmp_path / "verify-state.json",
            ):
                result = runner.invoke(get_app(), ["ship"])

        assert result.exit_code == 1

    def test_ship_blocked_without_unlock(self, tmp_path: Path) -> None:
        from src.interfaces.cli.commands.workflow import app

        verify_state = VerifyState(session_id="test-verify", unlock_ship=False)
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
        from src.interfaces.cli.commands.workflow import app

        verify_state = VerifyState(session_id="test-verify", unlock_ship=True)
        verify_path = tmp_path / "verify-state.json"
        verify_state.save(verify_path)

        with patch(
            "src.interfaces.cli.commands.workflow.get_verify_state_path",
            return_value=verify_path,
        ):
            result = runner.invoke(get_app(), ["ship"])

        assert result.exit_code == 0
        assert "Shipping to" in result.stdout


class TestWorkflowStatus:
    """Tests for workflow status command."""

    def test_status_all_none(self, tmp_path: Path) -> None:
        from src.application.services.workflow.state import (
            ExecuteState,
            PlanState,
            VerifyState,
        )

        with patch.object(PlanState, "load", return_value=None):
            with patch.object(ExecuteState, "load", return_value=None):
                with patch.object(VerifyState, "load", return_value=None):
                    with patch(
                        "src.interfaces.cli.commands.workflow.get_plan_state_path",
                        return_value=tmp_path / "plan-state.json",
                    ):
                        with patch(
                            "src.interfaces.cli.commands.workflow.get_execute_state_path",
                            return_value=tmp_path / "execute-state.json",
                        ):
                            with patch(
                                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                                return_value=tmp_path / "verify-state.json",
                            ):
                                result = runner.invoke(get_app(), ["status"])

        assert result.exit_code == 0
        assert "Workflow Status" in result.stdout

    def test_status_with_plan(self, tmp_path: Path) -> None:
        from src.interfaces.cli.commands.workflow import app

        plan_state = PlanState(session_id="test-plan", phase=WorkflowPhase.OUTLINED)
        plan_path = tmp_path / "plan-state.json"
        plan_state.save(plan_path)

        with patch.object(PlanState, "load", return_value=plan_state):
            with patch.object(ExecuteState, "load", return_value=None):
                with patch.object(VerifyState, "load", return_value=None):
                    with patch(
                        "src.interfaces.cli.commands.workflow.get_plan_state_path",
                        return_value=plan_path,
                    ):
                        with patch(
                            "src.interfaces.cli.commands.workflow.get_execute_state_path",
                            return_value=tmp_path / "execute-state.json",
                        ):
                            with patch(
                                "src.interfaces.cli.commands.workflow.get_verify_state_path",
                                return_value=tmp_path / "verify-state.json",
                            ):
                                result = runner.invoke(get_app(), ["status"])

        assert result.exit_code == 0
        assert "Plan:" in result.stdout
