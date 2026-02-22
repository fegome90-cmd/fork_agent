"""Tests for CLI dependencies - DI helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.interfaces.cli import dependencies


class TestGetContainer:
    def test_get_container_returns_container(self) -> None:
        container = dependencies.get_container()
        assert container is not None

    def test_get_container_with_custom_path(self) -> None:
        with patch("src.interfaces.cli.dependencies.create_container") as mock_create:
            mock_container = MagicMock()
            mock_create.return_value = mock_container

            result = dependencies.get_container(Path("/custom/path"))

            mock_create.assert_called_once_with(Path("/custom/path"))


class TestGetRepository:
    def test_get_repository_returns_repository(self) -> None:
        with patch("src.interfaces.cli.dependencies.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_repo = MagicMock()
            mock_container.observation_repository.return_value = mock_repo
            mock_get_container.return_value = mock_container

            result = dependencies.get_repository()

            mock_container.observation_repository.assert_called_once()

    def test_get_repository_with_custom_path(self) -> None:
        with patch("src.interfaces.cli.dependencies.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_repo = MagicMock()
            mock_container.observation_repository.return_value = mock_repo
            mock_get_container.return_value = mock_container

            result = dependencies.get_repository(Path("/custom/path"))

            mock_get_container.assert_called_once_with(Path("/custom/path"))
            mock_container.observation_repository.assert_called_once()


class TestGetMemoryService:
    def test_get_memory_service_returns_service(self) -> None:
        with patch("src.interfaces.cli.dependencies.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.memory_service.return_value = mock_service
            mock_get_container.return_value = mock_container

            result = dependencies.get_memory_service()

            mock_container.memory_service.assert_called_once()

    def test_get_memory_service_with_custom_path(self) -> None:
        with patch("src.interfaces.cli.dependencies.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.memory_service.return_value = mock_service
            mock_get_container.return_value = mock_container

            result = dependencies.get_memory_service(Path("/custom/path"))

            mock_get_container.assert_called_once_with(Path("/custom/path"))
            mock_container.memory_service.assert_called_once()

    def test_get_memory_service_returns_memory_service(self) -> None:
        with patch("src.interfaces.cli.dependencies.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.memory_service.return_value = mock_service
            mock_get_container.return_value = mock_container

            result = dependencies.get_memory_service()

            assert result is mock_service



class TestGetSchedulerService:
    def test_get_scheduler_service_returns_service(self) -> None:
        with patch("src.interfaces.cli.dependencies.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.scheduler_service.return_value = mock_service
            mock_get_container.return_value = mock_container

            result = dependencies.get_scheduler_service()

            mock_container.scheduler_service.assert_called_once()

    def test_get_scheduler_service_with_custom_path(self) -> None:
        with patch("src.interfaces.cli.dependencies.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.scheduler_service.return_value = mock_service
            mock_get_container.return_value = mock_container

            result = dependencies.get_scheduler_service(Path("/custom/path"))

            mock_get_container.assert_called_once_with(Path("/custom/path"))
            mock_container.scheduler_service.assert_called_once()

    def test_get_scheduler_service_returns_scheduler_service(self) -> None:
        with patch("src.interfaces.cli.dependencies.get_container") as mock_get_container:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.scheduler_service.return_value = mock_service
            mock_get_container.return_value = mock_container

            result = dependencies.get_scheduler_service()

            assert result is mock_service
