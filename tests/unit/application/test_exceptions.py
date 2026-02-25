"""Tests for custom memory exceptions."""

import pytest

from src.application.exceptions import (
    MemoryError,
    ObservationNotFoundError,
    RepositoryError,
    ServiceError,
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
