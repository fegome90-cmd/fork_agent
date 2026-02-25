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
