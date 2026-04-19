"""Tests for CLI dependencies — re-exports from canonical container."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.infrastructure.persistence import container as _container
from src.interfaces.cli import dependencies


class TestGetContainer:
    def test_get_container_returns_container(self) -> None:
        c = dependencies.get_container()
        assert c is not None

    def test_get_container_with_custom_path(self) -> None:
        with patch("src.infrastructure.persistence.container.create_container") as mock_create:
            mock_container = MagicMock()
            mock_create.return_value = mock_container

            dependencies.get_container(Path("/custom/path"))

            mock_create.assert_called_once_with(Path("/custom/path"))


class TestGetRepository:
    def test_get_repository_returns_repository(self) -> None:
        with patch("src.infrastructure.persistence.container.get_container") as mock_gc:
            mock_container = MagicMock()
            mock_repo = MagicMock()
            mock_container.observation_repository.return_value = mock_repo
            mock_gc.return_value = mock_container

            dependencies.get_repository()

            mock_container.observation_repository.assert_called_once()

    def test_get_repository_with_custom_path(self) -> None:
        with patch("src.infrastructure.persistence.container.get_container") as mock_gc:
            mock_container = MagicMock()
            mock_repo = MagicMock()
            mock_container.observation_repository.return_value = mock_repo
            mock_gc.return_value = mock_container

            dependencies.get_repository(Path("/custom/path"))

            mock_gc.assert_called_once_with(Path("/custom/path"))
            mock_container.observation_repository.assert_called_once()


class TestGetMemoryService:
    def test_get_memory_service_returns_service(self) -> None:
        with patch("src.infrastructure.persistence.container.get_container") as mock_gc:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.memory_service.return_value = mock_service
            mock_gc.return_value = mock_container

            dependencies.get_memory_service()

            mock_container.memory_service.assert_called_once()

    def test_get_memory_service_with_custom_path(self) -> None:
        with patch("src.infrastructure.persistence.container.get_container") as mock_gc:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.memory_service.return_value = mock_service
            mock_gc.return_value = mock_container

            dependencies.get_memory_service(Path("/custom/path"))

            mock_gc.assert_called_once_with(Path("/custom/path"))
            mock_container.memory_service.assert_called_once()

    def test_get_memory_service_returns_memory_service(self) -> None:
        with patch("src.infrastructure.persistence.container.get_container") as mock_gc:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.memory_service.return_value = mock_service
            mock_gc.return_value = mock_container

            result = dependencies.get_memory_service()

            assert result is mock_service


class TestGetSchedulerService:
    def test_get_scheduler_service_returns_service(self) -> None:
        with patch("src.infrastructure.persistence.container.get_container") as mock_gc:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.scheduler_service.return_value = mock_service
            mock_gc.return_value = mock_container

            dependencies.get_scheduler_service()

            mock_container.scheduler_service.assert_called_once()

    def test_get_scheduler_service_with_custom_path(self) -> None:
        with patch("src.infrastructure.persistence.container.get_container") as mock_gc:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.scheduler_service.return_value = mock_service
            mock_gc.return_value = mock_container

            dependencies.get_scheduler_service(Path("/custom/path"))

            mock_gc.assert_called_once_with(Path("/custom/path"))
            mock_container.scheduler_service.assert_called_once()

    def test_get_scheduler_service_returns_scheduler_service(self) -> None:
        with patch("src.infrastructure.persistence.container.get_container") as mock_gc:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.scheduler_service.return_value = mock_service
            mock_gc.return_value = mock_container

            result = dependencies.get_scheduler_service()

            assert result is mock_service


class TestReExports:
    """Verify that CLI dependencies re-exports match canonical container."""

    def test_get_hook_service_is_same_function(self) -> None:
        assert dependencies.get_hook_service is _container.get_hook_service

    def test_get_workflow_executor_is_same_function(self) -> None:
        assert dependencies.get_workflow_executor is _container.get_workflow_executor

    def test_get_container_is_same_function(self) -> None:
        assert dependencies.get_container is _container.get_container

    def test_get_memory_service_is_same_function(self) -> None:
        assert dependencies.get_memory_service is _container.get_memory_service

    def test_get_telemetry_service_is_same_function(self) -> None:
        assert dependencies.get_telemetry_service is _container.get_telemetry_service
