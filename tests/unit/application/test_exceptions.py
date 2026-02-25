"""Tests for custom memory exceptions."""

import pytest

from src.application.exceptions import (
    MemoryError,
    ObservationNotFoundError,
    PhaseSkipError,
    RepositoryError,
    ServiceError,
    WorkflowError,
)


def test_raise_memory_error() -> None:
    """Verify that MemoryError can be raised."""
    with pytest.raises(MemoryError, match="Base memory error"):
        raise MemoryError("Base memory error")


def test_raise_repository_error() -> None:
    """Verify that RepositoryError can be raised."""
    with pytest.raises(RepositoryError, match="DB error"):
        raise RepositoryError("DB error")


def test_raise_service_error() -> None:
    """Verify that ServiceError can be raised."""
    with pytest.raises(ServiceError, match="Service logic failed"):
        raise ServiceError("Service logic failed")


def test_raise_observation_not_found_error() -> None:
    """Verify that ObservationNotFoundError can be raised with a default message."""
    with pytest.raises(ObservationNotFoundError, match="Observation not found."):
        raise ObservationNotFoundError()


def test_exception_can_wrap_original_exception() -> None:
    """Verify that our custom exceptions can store the original exception for debugging."""
    original = ValueError("Invalid value")
    try:
        raise RepositoryError("Failed to save data", original_exception=original)
    except RepositoryError as e:
        assert e.original_exception is original
        assert str(e) == "Failed to save data"


def test_raise_phase_skip_error() -> None:
    """Verify that PhaseSkipError can be raised with proper attributes."""
    with pytest.raises(PhaseSkipError) as exc_info:
        raise PhaseSkipError(
            message="Cannot skip to verify",
            current_phase="planning",
            target_phase="verify",
        )
    error = exc_info.value
    assert error.current_phase == "planning"
    assert error.target_phase == "verify"
    assert "Cannot skip to verify" in str(error)


def test_phase_skip_error_inherits_from_workflow_error() -> None:
    """Verify that PhaseSkipError inherits from WorkflowError."""
    error = PhaseSkipError(
        message="Test",
        current_phase="planning",
        target_phase="verify",
    )
    assert isinstance(error, WorkflowError)


def test_raise_workflow_error() -> None:
    """Verify that WorkflowError can be raised."""
    with pytest.raises(WorkflowError, match="Workflow error"):
        raise WorkflowError("Workflow error")
