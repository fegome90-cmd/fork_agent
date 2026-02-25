"""Custom exceptions for the Memory subsystem."""


class MemoryError(Exception):
    """Base exception for all memory-related errors."""

    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        self.original_exception = original_exception


class RepositoryError(MemoryError):
    """Raised for errors originating from the data persistence layer."""

    pass


class ServiceError(MemoryError):
    """Raised for errors in the business logic layer."""

    pass


class ObservationNotFoundError(MemoryError):
    """Raised when a specific observation is not found."""

    def __init__(
        self, message: str = "Observation not found.", original_exception: Exception | None = None
    ):
        super().__init__(message, original_exception)


class WorkflowError(Exception):
    """Base exception for all workflow-related errors."""

    pass


class PhaseSkipError(WorkflowError):
    """Raised when attempting to skip a workflow phase without proper validation."""

    def __init__(self, message: str, current_phase: str, target_phase: str):
        super().__init__(message)
        self.current_phase = current_phase
        self.target_phase = target_phase
