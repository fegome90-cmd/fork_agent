"""Tests for concrete events.

TDD Red Phase - Tests written before implementation.
"""

from __future__ import annotations

import pytest


class TestUserCommandEvent:
    """Tests for UserCommandEvent."""

    def test_create_with_command_name(self) -> None:
        """Should create event with command name."""
        from src.application.services.orchestration.events import UserCommandEvent

        event = UserCommandEvent(command_name="test-command", args=())

        assert event.command_name == "test-command"

    def test_create_with_args(self) -> None:
        """Should create event with args tuple."""
        from src.application.services.orchestration.events import UserCommandEvent

        event = UserCommandEvent(command_name="test", args=("arg1", "arg2"))

        assert event.args == ("arg1", "arg2")

    def test_event_is_immutable(self) -> None:
        """UserCommandEvent should be frozen."""
        from dataclasses import FrozenInstanceError

        from src.application.services.orchestration.events import UserCommandEvent

        event = UserCommandEvent(command_name="test", args=())

        with pytest.raises(FrozenInstanceError):
            event.command_name = "modified"  # type: ignore[misc]

    def test_default_args_is_empty_tuple(self) -> None:
        """Should default args to empty tuple."""
        from src.application.services.orchestration.events import UserCommandEvent

        event = UserCommandEvent(command_name="test")

        assert event.args == ()


class TestFileWrittenEvent:
    """Tests for FileWrittenEvent."""

    def test_create_with_path(self) -> None:
        """Should create event with file path."""
        from src.application.services.orchestration.events import FileWrittenEvent

        event = FileWrittenEvent(path="/tmp/test.py")

        assert event.path == "/tmp/test.py"

    def test_event_is_immutable(self) -> None:
        """FileWrittenEvent should be frozen."""
        from dataclasses import FrozenInstanceError

        from src.application.services.orchestration.events import FileWrittenEvent

        event = FileWrittenEvent(path="/tmp/test.py")

        with pytest.raises(FrozenInstanceError):
            event.path = "/modified"  # type: ignore[misc]


class TestToolPreExecutionEvent:
    """Tests for ToolPreExecutionEvent."""

    def test_create_with_tool_name(self) -> None:
        """Should create event with tool name."""
        from src.application.services.orchestration.events import (
            ToolPreExecutionEvent,
        )

        event = ToolPreExecutionEvent(tool_name="Bash")

        assert event.tool_name == "Bash"

    def test_event_is_immutable(self) -> None:
        """ToolPreExecutionEvent should be frozen."""
        from dataclasses import FrozenInstanceError

        from src.application.services.orchestration.events import (
            ToolPreExecutionEvent,
        )

        event = ToolPreExecutionEvent(tool_name="Bash")

        with pytest.raises(FrozenInstanceError):
            event.tool_name = "Edit"  # type: ignore[misc]


class TestWorkflowPhaseChangeEvent:
    """Tests for WorkflowPhaseChangeEvent."""

    def test_create_with_required_fields(self) -> None:
        """Should create event with plan_id and phase."""
        from src.application.services.orchestration.events import (
            WorkflowPhaseChangeEvent,
        )

        event = WorkflowPhaseChangeEvent(plan_id="plan-123", phase="execute")

        assert event.plan_id == "plan-123"
        assert event.phase == "execute"

    def test_timestamp_auto_generated(self) -> None:
        """Should auto-generate timestamp if not provided."""
        import time

        from src.application.services.orchestration.events import (
            WorkflowPhaseChangeEvent,
        )

        before = int(time.time())
        event = WorkflowPhaseChangeEvent(plan_id="plan-123", phase="outline")
        after = int(time.time())

        assert before <= event.timestamp <= after

    def test_event_is_immutable(self) -> None:
        """WorkflowPhaseChangeEvent should be frozen."""
        from dataclasses import FrozenInstanceError

        from src.application.services.orchestration.events import (
            WorkflowPhaseChangeEvent,
        )

        event = WorkflowPhaseChangeEvent(plan_id="plan-123", phase="outline")

        with pytest.raises(FrozenInstanceError):
            event.phase = "execute"  # type: ignore[misc]


class TestWorkflowOutlineEvents:
    """Tests for WorkflowOutlineStartEvent and CompleteEvent."""

    def test_outline_start_event(self) -> None:
        """Should create WorkflowOutlineStartEvent."""
        from src.application.services.orchestration.events import (
            WorkflowOutlineStartEvent,
        )

        event = WorkflowOutlineStartEvent(plan_id="plan-123", task_description="test task")

        assert event.plan_id == "plan-123"
        assert event.task_description == "test task"

    def test_outline_complete_event(self) -> None:
        """Should create WorkflowOutlineCompleteEvent."""
        from src.application.services.orchestration.events import (
            WorkflowOutlineCompleteEvent,
        )

        event = WorkflowOutlineCompleteEvent(plan_id="plan-123", plan_file="/tmp/plan.md")

        assert event.plan_id == "plan-123"
        assert event.plan_file == "/tmp/plan.md"


class TestWorkflowExecuteEvents:
    """Tests for WorkflowExecuteStartEvent and CompleteEvent."""

    def test_execute_start_event(self) -> None:
        """Should create WorkflowExecuteStartEvent."""
        from src.application.services.orchestration.events import (
            WorkflowExecuteStartEvent,
        )

        event = WorkflowExecuteStartEvent(plan_id="plan-123", task_count=5)

        assert event.plan_id == "plan-123"
        assert event.task_count == 5

    def test_execute_complete_event(self) -> None:
        """Should create WorkflowExecuteCompleteEvent."""
        from src.application.services.orchestration.events import (
            WorkflowExecuteCompleteEvent,
        )

        event = WorkflowExecuteCompleteEvent(plan_id="plan-123", tasks_completed=3)

        assert event.plan_id == "plan-123"
        assert event.tasks_completed == 3


class TestWorkflowVerifyEvents:
    """Tests for WorkflowVerifyStartEvent and CompleteEvent."""

    def test_verify_start_event(self) -> None:
        """Should create WorkflowVerifyStartEvent."""
        from src.application.services.orchestration.events import (
            WorkflowVerifyStartEvent,
        )

        event = WorkflowVerifyStartEvent(plan_id="plan-123", run_tests=True)

        assert event.plan_id == "plan-123"
        assert event.run_tests is True

    def test_verify_complete_event_with_results(self) -> None:
        """Should create WorkflowVerifyCompleteEvent with test results."""
        from src.application.services.orchestration.events import (
            WorkflowVerifyCompleteEvent,
        )

        event = WorkflowVerifyCompleteEvent(
            plan_id="plan-123", test_results={"passed": True, "coverage": True}
        )

        assert event.plan_id == "plan-123"
        assert event.test_results == {"passed": True, "coverage": True}

    def test_verify_complete_event_test_results_is_immutable(self) -> None:
        """Should wrap test_results in a read-only MappingProxyType."""
        from types import MappingProxyType

        from src.application.services.orchestration.events import (
            WorkflowVerifyCompleteEvent,
        )

        event = WorkflowVerifyCompleteEvent(plan_id="plan-123", test_results={"passed": True})

        assert isinstance(event.test_results, MappingProxyType)
        with pytest.raises(TypeError):
            event.test_results["new_key"] = False  # type: ignore[index]


class TestWorkflowShipEvents:
    """Tests for WorkflowShipStartEvent and CompleteEvent."""

    def test_ship_start_event(self) -> None:
        """Should create WorkflowShipStartEvent."""
        from src.application.services.orchestration.events import (
            WorkflowShipStartEvent,
        )

        event = WorkflowShipStartEvent(plan_id="plan-123", target_branch="main")

        assert event.plan_id == "plan-123"
        assert event.target_branch == "main"

    def test_ship_complete_event(self) -> None:
        """Should create WorkflowShipCompleteEvent."""
        from src.application.services.orchestration.events import (
            WorkflowShipCompleteEvent,
        )

        event = WorkflowShipCompleteEvent(plan_id="plan-123", target_branch="main")

        assert event.plan_id == "plan-123"
        assert event.target_branch == "main"
