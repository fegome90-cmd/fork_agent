"""Git-related exceptions."""


class GitError(Exception):
    """Base Git exception."""

    def __init__(self, message: str = "Git error.", original_exception: Exception | None = None):
        super().__init__(message)
        self.original_exception = original_exception


class GitNotFoundError(GitError):
    """Raised when git is not installed."""

    def __init__(
        self, message: str = "Git is not installed.", original_exception: Exception | None = None
    ):
        super().__init__(message, original_exception)


class GitVersionError(GitError):
    """Raised when git version is less than 2.20 (C-03 requirement)."""

    def __init__(
        self,
        message: str = "Git version must be >= 2.20.",
        original_exception: Exception | None = None,
    ):
        super().__init__(message, original_exception)
