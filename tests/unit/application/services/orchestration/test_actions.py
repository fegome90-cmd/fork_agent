"""Tests for concrete actions.

TDD Red Phase - Tests written before implementation.
"""

from __future__ import annotations

import pytest


class TestShellCommandAction:
    """Tests for ShellCommandAction."""

    def test_create_with_command(self) -> None:
        """Should create action with command string."""
        from src.application.services.orchestration.actions import ShellCommandAction

        action = ShellCommandAction(command="echo hello")

        assert action.command == "echo hello"

    def test_default_timeout_is_30(self) -> None:
        """Should default timeout to 30 seconds."""
        from src.application.services.orchestration.actions import ShellCommandAction

        action = ShellCommandAction(command="echo test")

        assert action.timeout == 30

    def test_create_with_custom_timeout(self) -> None:
        """Should accept custom timeout."""
        from src.application.services.orchestration.actions import ShellCommandAction

        action = ShellCommandAction(command="sleep 5", timeout=60)

        assert action.timeout == 60

    def test_action_is_immutable(self) -> None:
        """ShellCommandAction should be frozen."""
        from dataclasses import FrozenInstanceError

        from src.application.services.orchestration.actions import ShellCommandAction

        action = ShellCommandAction(command="echo test")

        with pytest.raises(FrozenInstanceError):
            action.command = "modified"  # type: ignore[misc]

    def test_timeout_must_be_positive(self) -> None:
        """Should reject zero or negative timeout."""
        from src.application.services.orchestration.actions import ShellCommandAction

        with pytest.raises(ValueError):
            ShellCommandAction(command="test", timeout=0)

        with pytest.raises(ValueError):
            ShellCommandAction(command="test", timeout=-1)
