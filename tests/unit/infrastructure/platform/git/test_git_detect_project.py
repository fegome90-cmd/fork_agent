"""Tests for git remote auto-detection.

Feature: detect_project_from_remote() extracts repo name from git remote origin URL.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.infrastructure.platform.git.exceptions import GitError


def _make_executor() -> MagicMock:
    """Create a GitCommandExecutor mock with minimal setup."""
    executor = MagicMock()
    executor._repo_path = None
    executor._version = (2, 30, 0)
    executor._run_git_command = MagicMock()
    return executor


class TestDetectProjectFromRemote:
    """Git remote auto-detection tests."""

    def test_detect_project_https_url(self) -> None:
        """Extract repo name from HTTPS URL with .git suffix."""
        from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor

        executor = _make_executor()
        executor._run_git_command.return_value = MagicMock(
            stdout="https://github.com/owner/my-project.git\n"
        )

        # Bind the real method
        result = GitCommandExecutor.detect_project_from_remote(executor)
        assert result == "my-project"

    def test_detect_project_https_url_no_suffix(self) -> None:
        """Extract repo name from HTTPS URL without .git suffix."""
        from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor

        executor = _make_executor()
        executor._run_git_command.return_value = MagicMock(
            stdout="https://github.com/owner/my-project\n"
        )

        result = GitCommandExecutor.detect_project_from_remote(executor)
        assert result == "my-project"

    def test_detect_project_ssh_url(self) -> None:
        """Extract repo name from SSH URL."""
        from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor

        executor = _make_executor()
        executor._run_git_command.return_value = MagicMock(
            stdout="git@github.com:owner/my-project.git\n"
        )

        result = GitCommandExecutor.detect_project_from_remote(executor)
        assert result == "my-project"

    def test_detect_project_ssh_url_no_suffix(self) -> None:
        """Extract repo name from SSH URL without .git suffix."""
        from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor

        executor = _make_executor()
        executor._run_git_command.return_value = MagicMock(
            stdout="git@github.com:owner/my-project\n"
        )

        result = GitCommandExecutor.detect_project_from_remote(executor)
        assert result == "my-project"

    def test_detect_project_no_remote(self) -> None:
        """Return None when no origin remote is configured."""
        from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor

        executor = _make_executor()
        executor._run_git_command.return_value = MagicMock(stdout="\n")

        result = GitCommandExecutor.detect_project_from_remote(executor)
        assert result is None

    def test_detect_project_git_error(self) -> None:
        """Return None on GitError (graceful degradation)."""
        from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor

        executor = _make_executor()
        executor._run_git_command.side_effect = GitError("not a git repo")

        result = GitCommandExecutor.detect_project_from_remote(executor)
        assert result is None

    def test_detect_project_trailing_slash(self) -> None:
        """Handle URL with trailing slash before .git."""
        from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor

        executor = _make_executor()
        executor._run_git_command.return_value = MagicMock(
            stdout="https://github.com/owner/my-project/\n"
        )

        result = GitCommandExecutor.detect_project_from_remote(executor)
        assert result == "my-project"

    def test_detect_project_with_path_param(self) -> None:
        """Use explicit path parameter."""
        from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor

        executor = _make_executor()
        executor._run_git_command.return_value = MagicMock(
            stdout="git@github.com:owner/cli-tool.git\n"
        )

        result = GitCommandExecutor.detect_project_from_remote(
            executor, path=Path("/some/repo")
        )
        assert result == "cli-tool"
        executor._run_git_command.assert_called_once()
        call_kwargs = executor._run_git_command.call_args
        assert call_kwargs.kwargs.get("cwd") == Path("/some/repo")
