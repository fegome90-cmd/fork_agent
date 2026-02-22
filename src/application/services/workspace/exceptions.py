"""Custom exceptions for the Workspace service."""

from typing import Optional

# Re-export Git exceptions from infrastructure to maintain backward compatibility
from src.infrastructure.platform.git.exceptions import (
    GitError,
    GitNotFoundError,
    GitVersionError,
)


class WorkspaceError(Exception):
    """Base exception for all workspace-related errors."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


class WorkspaceExistsError(WorkspaceError):
    """Raised when workspace already exists."""

    def __init__(
        self, message: str = "Workspace already exists.", original_exception: Optional[Exception] = None
    ):
        super().__init__(message, original_exception)


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when workspace doesn't exist."""

    def __init__(
        self, message: str = "Workspace not found.", original_exception: Optional[Exception] = None
    ):
        super().__init__(message, original_exception)


class WorkspaceNotCleanError(WorkspaceError):
    """Raised when workspace is not clean (uncommitted changes)."""

    def __init__(
        self, message: str = "Workspace is not clean (uncommitted changes).", original_exception: Optional[Exception] = None
    ):
        super().__init__(message, original_exception)


class HookExecutionError(WorkspaceError):
    """Raised when a hook fails to execute."""

    def __init__(
        self, message: str = "Hook execution failed.", original_exception: Optional[Exception] = None
    ):
        super().__init__(message, original_exception)


class InvalidLayoutError(WorkspaceError):
    """Raised when layout type is invalid."""

    def __init__(
        self, message: str = "Invalid layout type.", original_exception: Optional[Exception] = None
    ):
        super().__init__(message, original_exception)


class SecurityError(WorkspaceError):
    """Base security exception (path traversal, etc.)."""

    def __init__(
        self, message: str = "Security error.", original_exception: Optional[Exception] = None
    ):
        super().__init__(message, original_exception)


class GitError(WorkspaceError):
    """Base Git exception."""

    def __init__(
        self, message: str = "Git error.", original_exception: Optional[Exception] = None
    ):
        super().__init__(message, original_exception)


class GitNotFoundError(GitError):
    """Raised when git is not installed."""

    def __init__(
        self, message: str = "Git is not installed.", original_exception: Optional[Exception] = None
    ):
        super().__init__(message, original_exception)


class GitVersionError(GitError):
    """Raised when git version is less than 2.20 (C-03 requirement)."""

    def __init__(
        self, message: str = "Git version must be >= 2.20.", original_exception: Optional[Exception] = None
    ):
        super().__init__(message, original_exception)
