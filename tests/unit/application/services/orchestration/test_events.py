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
