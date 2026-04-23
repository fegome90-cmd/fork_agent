"""Custom exceptions for the Memory subsystem."""


class MemoryStoreError(Exception):
    """Base exception for all memory-related errors.

    NOTE: Originally named ``MemoryError`` but renamed to avoid shadowing
    the Python builtin ``MemoryError``.
    """

    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        self.original_exception = original_exception


class RepositoryError(MemoryStoreError):
    """Raised for errors originating from the data persistence layer."""

    pass


class ServiceError(MemoryStoreError):
    """Raised for errors in the business logic layer."""

    pass


class SessionNotFoundError(MemoryStoreError):
    """Raised when a session is not found."""

    def __init__(
        self,
        message: str = "Session not found.",
        original_exception: Exception | None = None,
    ):
        super().__init__(message, original_exception)


class ObservationNotFoundError(MemoryStoreError):
    """Raised when a specific observation is not found."""

    def __init__(
        self, message: str = "Observation not found.", original_exception: Exception | None = None
    ):
        super().__init__(message, original_exception)


class WorkflowError(Exception):
    """Base exception for all workflow-related errors."""

    pass


class TaskTransitionError(ValueError):
    """Raised when a task state transition is invalid or the task is concurrently modified."""


class PhaseSkipError(WorkflowError):
    """Raised when attempting to skip a workflow phase without proper validation."""

    def __init__(self, message: str, current_phase: str, target_phase: str):
        super().__init__(message)
        self.current_phase = current_phase
        self.target_phase = target_phase
