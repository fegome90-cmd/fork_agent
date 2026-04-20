"""Tests for concrete specifications.

TDD Red Phase - Tests written before implementation.
"""

from __future__ import annotations

from src.application.services.orchestration.events import (
    FileWrittenEvent,
    ToolPreExecutionEvent,
    UserCommandEvent,
)


class TestEventTypeSpec:
    """Tests for EventTypeSpec."""

    def test_matches_correct_event_type(self) -> None:
        """Should match events of the correct type."""
        from src.application.services.orchestration.specs import EventTypeSpec

        spec = EventTypeSpec(event_type=UserCommandEvent)
        event = UserCommandEvent(command_name="test")

        assert spec.is_satisfied_by(event) is True

    def test_rejects_wrong_event_type(self) -> None:
        """Should reject events of different type."""
        from src.application.services.orchestration.specs import EventTypeSpec

        spec = EventTypeSpec(event_type=UserCommandEvent)
        event = FileWrittenEvent(path="/tmp/test.py")

        assert spec.is_satisfied_by(event) is False

    def test_matches_file_written_event(self) -> None:
        """Should match FileWrittenEvent when specified."""
        from src.application.services.orchestration.specs import EventTypeSpec

        spec = EventTypeSpec(event_type=FileWrittenEvent)
        event = FileWrittenEvent(path="/tmp/test.py")

        assert spec.is_satisfied_by(event) is True


class TestCommandNameSpec:
    """Tests for CommandNameSpec."""

    def test_matches_exact_command_name(self) -> None:
        """Should match exact command name."""
        from src.application.services.orchestration.specs import CommandNameSpec

        spec = CommandNameSpec(name_pattern="test-command")
        event = UserCommandEvent(command_name="test-command")

        assert spec.is_satisfied_by(event) is True

    def test_matches_regex_pattern(self) -> None:
        """Should match regex pattern."""
        from src.application.services.orchestration.specs import CommandNameSpec

        spec = CommandNameSpec(name_pattern="test-.*")
        event = UserCommandEvent(command_name="test-command")

        assert spec.is_satisfied_by(event) is True

    def test_rejects_non_matching_pattern(self) -> None:
        """Should reject non-matching pattern."""
        from src.application.services.orchestration.specs import CommandNameSpec

        spec = CommandNameSpec(name_pattern="other-.*")
        event = UserCommandEvent(command_name="test-command")

        assert spec.is_satisfied_by(event) is False

    def test_rejects_wrong_event_type(self) -> None:
        """Should reject events that are not UserCommandEvent."""
        from src.application.services.orchestration.specs import CommandNameSpec

        spec = CommandNameSpec(name_pattern="test")
        event = FileWrittenEvent(path="/tmp/test.py")

        assert spec.is_satisfied_by(event) is False


class TestFilePathSpec:
    """Tests for FilePathSpec."""

    def test_matches_path_pattern(self) -> None:
        """Should match path regex pattern."""
        from src.application.services.orchestration.specs import FilePathSpec

        spec = FilePathSpec(path_pattern=r"/tmp/.*\.py")
        event = FileWrittenEvent(path="/tmp/test.py")

        assert spec.is_satisfied_by(event) is True

    def test_rejects_non_matching_path(self) -> None:
        """Should reject non-matching path."""
        from src.application.services.orchestration.specs import FilePathSpec

        spec = FilePathSpec(path_pattern=r"/src/.*")
        event = FileWrittenEvent(path="/tmp/test.py")

        assert spec.is_satisfied_by(event) is False

    def test_rejects_wrong_event_type(self) -> None:
        """Should reject events that are not FileWrittenEvent."""
        from src.application.services.orchestration.specs import FilePathSpec

        spec = FilePathSpec(path_pattern=".*")
        event = UserCommandEvent(command_name="test")

        assert spec.is_satisfied_by(event) is False


class TestRegexMatcherSpec:
    """Tests for RegexMatcherSpec - claudikins-kernel compatible."""

    def test_matches_user_command_event_by_name(self) -> None:
        """Should match UserCommandEvent by command name."""
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="UserCommand", matcher="test-.*")
        event = UserCommandEvent(command_name="test-command")

        assert spec.is_satisfied_by(event) is True

    def test_matches_file_written_event_by_path(self) -> None:
        """Should match FileWrittenEvent by path."""
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="FileWritten", matcher=r".*\.py")
        event = FileWrittenEvent(path="/tmp/test.py")

        assert spec.is_satisfied_by(event) is True

    def test_matches_tool_pre_execution_event_by_name(self) -> None:
        """Should match ToolPreExecutionEvent by tool name."""
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="ToolPreExecution", matcher="Bash|Edit")
        event = ToolPreExecutionEvent(tool_name="Bash")

        assert spec.is_satisfied_by(event) is True

    def test_rejects_wrong_event_type(self) -> None:
        """Should reject events of different type."""
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="UserCommand", matcher=".*")
        event = FileWrittenEvent(path="/tmp/test.py")

        assert spec.is_satisfied_by(event) is False

    def test_wildcard_matches_any_value(self) -> None:
        """Should match any value with .* pattern."""
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="UserCommand", matcher=".*")
        event = UserCommandEvent(command_name="anything")

        assert spec.is_satisfied_by(event) is True

    def test_matches_session_start_by_id(self) -> None:
        """Should match SessionStartEvent by session_id."""
        from src.application.services.orchestration.events import SessionStartEvent
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="SessionStart", matcher="session-.*")
        event = SessionStartEvent(session_id="session-123")

        assert spec.is_satisfied_by(event) is True

    def test_matches_subagent_start_by_name(self) -> None:
        """Should match SubagentStartEvent by agent_name."""
        from src.application.services.orchestration.events import SubagentStartEvent
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="SubagentStart", matcher="agent-.*")
        event = SubagentStartEvent(agent_name="agent-test")

        assert spec.is_satisfied_by(event) is True

    def test_matches_subagent_stop_by_name(self) -> None:
        """Should match SubagentStopEvent by agent_name."""
        from src.application.services.orchestration.events import SubagentStopEvent
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="SubagentStop", matcher="agent-.*")
        event = SubagentStopEvent(agent_name="agent-test")

        assert spec.is_satisfied_by(event) is True

    def test_matches_workflow_outline_start_by_plan_id(self) -> None:
        """Should match WorkflowOutlineStartEvent by plan_id."""
        from src.application.services.orchestration.events import (
            WorkflowOutlineStartEvent,
        )
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="WorkflowOutlineStart", matcher="plan-.*")
        event = WorkflowOutlineStartEvent(plan_id="plan-123")

        assert spec.is_satisfied_by(event) is True

    def test_matches_workflow_execute_start_by_plan_id(self) -> None:
        """Should match WorkflowExecuteStartEvent by plan_id."""
        from src.application.services.orchestration.events import (
            WorkflowExecuteStartEvent,
        )
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="WorkflowExecuteStart", matcher="plan-.*")
        event = WorkflowExecuteStartEvent(plan_id="plan-456")

        assert spec.is_satisfied_by(event) is True

    def test_matches_workflow_phase_change_by_plan_id(self) -> None:
        """Should match WorkflowPhaseChangeEvent by plan_id."""
        from src.application.services.orchestration.events import (
            WorkflowPhaseChangeEvent,
        )
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="WorkflowPhaseChange", matcher=".*")
        event = WorkflowPhaseChangeEvent(plan_id="plan-789", phase="execute")

        assert spec.is_satisfied_by(event) is True

    def test_rejects_non_matching_plan_id(self) -> None:
        """Should reject events with non-matching plan_id."""
        from src.application.services.orchestration.events import (
            WorkflowOutlineStartEvent,
        )
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="WorkflowOutlineStart", matcher="^prod-.*")
        event = WorkflowOutlineStartEvent(plan_id="dev-123")

        assert spec.is_satisfied_by(event) is False

    def test_invalid_regex_never_matches(self) -> None:
        """Should not match any event when regex is invalid (no accidental match-all)."""
        from src.application.services.orchestration.events import UserCommandEvent
        from src.application.services.orchestration.specs import RegexMatcherSpec

        spec = RegexMatcherSpec(event_type="UserCommand", matcher="[invalid")
        event = UserCommandEvent(command_name="anything")

        assert spec.is_satisfied_by(event) is False
