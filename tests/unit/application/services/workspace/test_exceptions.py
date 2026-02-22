"""Unit tests for workspace exceptions."""

import pytest

from src.application.services.workspace.exceptions import (
    GitError,
    GitNotFoundError,
    GitVersionError,
    HookExecutionError,
    InvalidLayoutError,
    SecurityError,
    WorkspaceError,
    WorkspaceExistsError,
    WorkspaceNotCleanError,
    WorkspaceNotFoundError,
)


class TestWorkspaceError:
    """Tests for WorkspaceError base exception."""

    def test_workspace_error_creation(self) -> None:
        """Test creating a WorkspaceError."""
        error = WorkspaceError("Test error message")
        assert str(error) == "Test error message"
        assert error.original_exception is None

    def test_workspace_error_with_original_exception(self) -> None:
        """Test WorkspaceError with original exception."""
        original = ValueError("Original error")
        error = WorkspaceError("Test error", original)
        assert str(error) == "Test error"
        assert error.original_exception is original

    def test_workspace_error_is_exception(self) -> None:
        """Test WorkspaceError inherits from Exception."""
        error = WorkspaceError("Test")
        assert isinstance(error, Exception)


class TestWorkspaceExistsError:
    """Tests for WorkspaceExistsError."""

    def test_workspace_exists_error_default_message(self) -> None:
        """Test default message for WorkspaceExistsError."""
        error = WorkspaceExistsError()
        assert "Workspace already exists" in str(error)

    def test_workspace_exists_error_custom_message(self) -> None:
        """Test custom message for WorkspaceExistsError."""
        error = WorkspaceExistsError("Custom exists message")
        assert str(error) == "Custom exists message"

    def test_workspace_exists_error_with_original(self) -> None:
        """Test WorkspaceExistsError with original exception."""
        original = RuntimeError("Original")
        error = WorkspaceExistsError("Custom", original)
        assert error.original_exception is original

    def test_workspace_exists_error_inherits_workspace_error(self) -> None:
        """Test WorkspaceExistsError inherits from WorkspaceError."""
        error = WorkspaceExistsError()
        assert isinstance(error, WorkspaceError)


class TestWorkspaceNotFoundError:
    """Tests for WorkspaceNotFoundError."""

    def test_workspace_not_found_error_default_message(self) -> None:
        """Test default message for WorkspaceNotFoundError."""
        error = WorkspaceNotFoundError()
        assert "Workspace not found" in str(error)

    def test_workspace_not_found_error_custom_message(self) -> None:
        """Test custom message for WorkspaceNotFoundError."""
        error = WorkspaceNotFoundError("Custom not found message")
        assert str(error) == "Custom not found message"

    def test_workspace_not_found_error_with_original(self) -> None:
        """Test WorkspaceNotFoundError with original exception."""
        original = RuntimeError("Original")
        error = WorkspaceNotFoundError("Custom", original)
        assert error.original_exception is original

    def test_workspace_not_found_error_inherits_workspace_error(self) -> None:
        """Test WorkspaceNotFoundError inherits from WorkspaceError."""
        error = WorkspaceNotFoundError()
        assert isinstance(error, WorkspaceError)


class TestWorkspaceNotCleanError:
    """Tests for WorkspaceNotCleanError."""

    def test_workspace_not_clean_error_default_message(self) -> None:
        """Test default message for WorkspaceNotCleanError."""
        error = WorkspaceNotCleanError()
        assert "not clean" in str(error).lower()

    def test_workspace_not_clean_error_custom_message(self) -> None:
        """Test custom message for WorkspaceNotCleanError."""
        error = WorkspaceNotCleanError("Custom not clean message")
        assert str(error) == "Custom not clean message"

    def test_workspace_not_clean_error_with_original(self) -> None:
        """Test WorkspaceNotCleanError with original exception."""
        original = RuntimeError("Original")
        error = WorkspaceNotCleanError("Custom", original)
        assert error.original_exception is original

    def test_workspace_not_clean_error_inherits_workspace_error(self) -> None:
        """Test WorkspaceNotCleanError inherits from WorkspaceError."""
        error = WorkspaceNotCleanError()
        assert isinstance(error, WorkspaceError)


class TestHookExecutionError:
    """Tests for HookExecutionError."""

    def test_hook_execution_error_default_message(self) -> None:
        """Test default message for HookExecutionError."""
        error = HookExecutionError()
        assert "Hook" in str(error) and "failed" in str(error).lower()

    def test_hook_execution_error_custom_message(self) -> None:
        """Test custom message for HookExecutionError."""
        error = HookExecutionError("Custom hook message")
        assert str(error) == "Custom hook message"

    def test_hook_execution_error_with_original(self) -> None:
        """Test HookExecutionError with original exception."""
        original = RuntimeError("Original")
        error = HookExecutionError("Custom", original)
        assert error.original_exception is original

    def test_hook_execution_error_inherits_workspace_error(self) -> None:
        """Test HookExecutionError inherits from WorkspaceError."""
        error = HookExecutionError()
        assert isinstance(error, WorkspaceError)


class TestInvalidLayoutError:
    """Tests for InvalidLayoutError."""

    def test_invalid_layout_error_default_message(self) -> None:
        """Test default message for InvalidLayoutError."""
        error = InvalidLayoutError()
        assert "Invalid layout" in str(error)

    def test_invalid_layout_error_custom_message(self) -> None:
        """Test custom message for InvalidLayoutError."""
        error = InvalidLayoutError("Custom layout message")
        assert str(error) == "Custom layout message"

    def test_invalid_layout_error_with_original(self) -> None:
        """Test InvalidLayoutError with original exception."""
        original = RuntimeError("Original")
        error = InvalidLayoutError("Custom", original)
        assert error.original_exception is original

    def test_invalid_layout_error_inherits_workspace_error(self) -> None:
        """Test InvalidLayoutError inherits from WorkspaceError."""
        error = InvalidLayoutError()
        assert isinstance(error, WorkspaceError)


class TestSecurityError:
    """Tests for SecurityError."""

    def test_security_error_default_message(self) -> None:
        """Test default message for SecurityError."""
        error = SecurityError()
        assert "Security error" in str(error)

    def test_security_error_custom_message(self) -> None:
        """Test custom message for SecurityError."""
        error = SecurityError("Custom security message")
        assert str(error) == "Custom security message"

    def test_security_error_with_original(self) -> None:
        """Test SecurityError with original exception."""
        original = RuntimeError("Original")
        error = SecurityError("Custom", original)
        assert error.original_exception is original

    def test_security_error_inherits_workspace_error(self) -> None:
        """Test SecurityError inherits from WorkspaceError."""
        error = SecurityError()
        assert isinstance(error, WorkspaceError)


class TestGitError:
    """Tests for GitError."""

    def test_git_error_default_message(self) -> None:
        """Test default message for GitError."""
        error = GitError()
        assert "Git error" in str(error)

    def test_git_error_custom_message(self) -> None:
        """Test custom message for GitError."""
        error = GitError("Custom git message")
        assert str(error) == "Custom git message"

    def test_git_error_with_original(self) -> None:
        """Test GitError with original exception."""
        original = RuntimeError("Original")
        error = GitError("Custom", original)
        assert error.original_exception is original

    def test_git_error_inherits_exception(self) -> None:
        """Test GitError inherits from Exception (infrastructure-level)."""
        error = GitError()
        assert isinstance(error, Exception)


class TestGitNotFoundError:
    """Tests for GitNotFoundError."""

    def test_git_not_found_error_default_message(self) -> None:
        """Test default message for GitNotFoundError."""
        error = GitNotFoundError()
        assert "Git is not installed" in str(error)

    def test_git_not_found_error_custom_message(self) -> None:
        """Test custom message for GitNotFoundError."""
        error = GitNotFoundError("Custom git not found message")
        assert str(error) == "Custom git not found message"

    def test_git_not_found_error_with_original(self) -> None:
        """Test GitNotFoundError with original exception."""
        original = FileNotFoundError("Original")
        error = GitNotFoundError("Custom", original)
        assert error.original_exception is original

    def test_git_not_found_error_inherits_git_error(self) -> None:
        """Test GitNotFoundError inherits from GitError."""
        error = GitNotFoundError()
        assert isinstance(error, GitError)


class TestGitVersionError:
    """Tests for GitVersionError."""

    def test_git_version_error_default_message(self) -> None:
        """Test default message for GitVersionError."""
        error = GitVersionError()
        assert "Git version" in str(error) and "2.20" in str(error)

    def test_git_version_error_custom_message(self) -> None:
        """Test custom message for GitVersionError."""
        error = GitVersionError("Custom version message")
        assert str(error) == "Custom version message"

    def test_git_version_error_with_original(self) -> None:
        """Test GitVersionError with original exception."""
        original = RuntimeError("Original")
        error = GitVersionError("Custom", original)
        assert error.original_exception is original

    def test_git_version_error_inherits_git_error(self) -> None:
        """Test GitVersionError inherits from GitError."""
        error = GitVersionError()
        assert isinstance(error, GitError)


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    def test_exception_hierarchy(self) -> None:
        """Test that all exceptions form a proper hierarchy."""
        # Workspace-specific exceptions inherit from WorkspaceError
        assert issubclass(WorkspaceExistsError, WorkspaceError)
        assert issubclass(WorkspaceNotFoundError, WorkspaceError)
        assert issubclass(WorkspaceNotCleanError, WorkspaceError)
        assert issubclass(HookExecutionError, WorkspaceError)
        assert issubclass(InvalidLayoutError, WorkspaceError)
        assert issubclass(SecurityError, WorkspaceError)

        # Git exceptions are infrastructure-level (inherit from their own base)
        assert issubclass(GitNotFoundError, GitError)
        assert issubclass(GitVersionError, GitError)
        # GitError inherits from Exception (not WorkspaceError - it's infrastructure)
        assert issubclass(GitError, Exception)

    def test_can_raise_and_catch_all_exceptions(self) -> None:
        """Test that all exceptions can be raised and caught."""
        exceptions = [
            WorkspaceError("test"),
            WorkspaceExistsError("test"),
            WorkspaceNotFoundError("test"),
            WorkspaceNotCleanError("test"),
            HookExecutionError("test"),
            InvalidLayoutError("test"),
            SecurityError("test"),
            GitError("test"),
            GitNotFoundError("test"),
            GitVersionError("test"),
        ]

        for exc in exceptions:
            with pytest.raises(type(exc)):
                raise exc

    def test_workspace_error_catches_workspace_exceptions(self) -> None:
        """Test that catching WorkspaceError catches workspace-specific exceptions."""
        workspace_exceptions = [
            WorkspaceExistsError(),
            WorkspaceNotFoundError(),
            WorkspaceNotCleanError(),
            HookExecutionError(),
            InvalidLayoutError(),
            SecurityError(),
        ]

        for exc in workspace_exceptions:
            assert isinstance(exc, WorkspaceError)

    def test_git_error_catches_git_exceptions(self) -> None:
        """Test that catching GitError catches all git-specific exceptions."""
        git_exceptions = [
            GitError(),
            GitNotFoundError(),
            GitVersionError(),
        ]

        for exc in git_exceptions:
            assert isinstance(exc, GitError)
