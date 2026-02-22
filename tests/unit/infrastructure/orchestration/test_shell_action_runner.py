"""Tests for ShellActionRunner infrastructure.

TDD Red Phase - Tests written before implementation.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.orchestration.actions import ShellCommandAction
from src.domain.ports.event_ports import Action


class MockAction:
    """Mock action that is not ShellCommandAction."""

    pass


class TestShellActionRunner:
    """Tests for ShellActionRunner."""

    def test_run_executes_shell_command(self, tmp_path: Path) -> None:
        """Should execute shell command successfully."""
        from src.infrastructure.orchestration.shell_action_runner import (
            ShellActionRunner,
        )

        runner = ShellActionRunner(hooks_dir=tmp_path)
        action = ShellCommandAction(command="echo hello")

        runner.run(action)

    def test_run_raises_type_error_for_wrong_action_type(self, tmp_path: Path) -> None:
        """Should raise TypeError for non-ShellCommandAction."""
        from src.infrastructure.orchestration.shell_action_runner import (
            ShellActionRunner,
        )

        runner = ShellActionRunner(hooks_dir=tmp_path)
        action = MockAction()

        with pytest.raises(TypeError, match="ShellActionRunner only handles"):
            runner.run(action)

    def test_run_uses_action_timeout(self, tmp_path: Path) -> None:
        """Should use action's timeout value."""
        from src.infrastructure.orchestration.shell_action_runner import (
            ShellActionRunner,
        )

        runner = ShellActionRunner(hooks_dir=tmp_path, default_timeout=10)
        action = ShellCommandAction(command="echo test", timeout=60)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            runner.run(action)

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["timeout"] == 60

    def test_run_uses_action_default_timeout(self, tmp_path: Path) -> None:
        """Should use action's default timeout (30)."""
        from src.infrastructure.orchestration.shell_action_runner import (
            ShellActionRunner,
        )

        runner = ShellActionRunner(hooks_dir=tmp_path, default_timeout=45)
        action = ShellCommandAction(command="echo test")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            runner.run(action)

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["timeout"] == 30

    def test_run_raises_on_non_zero_exit(self, tmp_path: Path) -> None:
        """Should raise RuntimeError on non-zero exit code."""
        from src.infrastructure.orchestration.shell_action_runner import (
            ShellActionRunner,
        )

        runner = ShellActionRunner(hooks_dir=tmp_path)
        action = ShellCommandAction(command="exit 1")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error message")

            with pytest.raises(RuntimeError, match="Action failed"):
                runner.run(action)

    def test_run_uses_safe_environment(self, tmp_path: Path) -> None:
        """Should filter dangerous environment variables."""
        from src.infrastructure.orchestration.shell_action_runner import (
            ShellActionRunner,
        )

        runner = ShellActionRunner(hooks_dir=tmp_path)
        action = ShellCommandAction(command="echo test")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            runner.run(action)

            call_kwargs = mock_run.call_args[1]
            env = call_kwargs["env"]

            assert "LD_PRELOAD" not in env
            assert "LD_LIBRARY_PATH" not in env

    def test_run_passes_hooks_dir_env(self, tmp_path: Path) -> None:
        """Should pass HOOKS_DIR environment variable."""
        from src.infrastructure.orchestration.shell_action_runner import (
            ShellActionRunner,
        )

        runner = ShellActionRunner(hooks_dir=tmp_path)
        action = ShellCommandAction(command="echo test")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            runner.run(action)

            call_kwargs = mock_run.call_args[1]
            env = call_kwargs["env"]

            assert "HOOKS_DIR" in env
            assert env["HOOKS_DIR"] == str(tmp_path)

    def test_run_handles_timeout(self, tmp_path: Path) -> None:
        """Should raise RuntimeError on timeout."""
        from src.infrastructure.orchestration.shell_action_runner import (
            ShellActionRunner,
        )

        runner = ShellActionRunner(hooks_dir=tmp_path, default_timeout=1)
        action = ShellCommandAction(command="sleep 10", timeout=1)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 10", timeout=1)

            with pytest.raises(RuntimeError, match="timed out"):
                runner.run(action)
