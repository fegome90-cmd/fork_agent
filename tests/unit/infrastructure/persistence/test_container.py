"""Tests for DI container factory functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.infrastructure.persistence.container import (
    create_container,
    detect_memory_db_path,
    get_default_db_path,
    get_memory_service,
    get_memory_service_auto,
    get_tmux_orchestrator,
    get_workspace_manager,
)


class TestGetTmuxOrchestrator:
    """Tests for get_tmux_orchestrator factory function."""

    def test_returns_tmux_orchestrator_instance(self) -> None:
        """Should return a TmuxOrchestrator instance."""
        with patch("src.infrastructure.persistence.container.get_container") as mock_get:
            mock_container = MagicMock()
            mock_orchestrator = MagicMock()
            mock_container.tmux_orchestrator.return_value = mock_orchestrator
            mock_get.return_value = mock_container

            result = get_tmux_orchestrator()

            assert result is mock_orchestrator
            mock_container.tmux_orchestrator.assert_called_once()

    def test_creates_singleton_instance(self) -> None:
        """Should return the same instance on subsequent calls."""
        with patch("src.infrastructure.persistence.container.get_container") as mock_get:
            mock_container = MagicMock()
            mock_orchestrator = MagicMock()
            mock_container.tmux_orchestrator.return_value = mock_orchestrator
            mock_get.return_value = mock_container

            result1 = get_tmux_orchestrator()
            result2 = get_tmux_orchestrator()

            assert result1 is result2


class TestGetMemoryService:
    """Tests for get_memory_service factory function."""

    def test_returns_memory_service_with_default_path(self) -> None:
        """Should return a MemoryService with default DB path."""
        with patch("src.infrastructure.persistence.container.get_container") as mock_get:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.memory_service.return_value = mock_service
            mock_get.return_value = mock_container

            result = get_memory_service()

            assert result is mock_service

    def test_returns_memory_service_with_custom_path(self) -> None:
        """Should return a MemoryService with custom DB path."""
        custom_path = Path("/custom/path/memory.db")

        with patch("src.infrastructure.persistence.container.create_container") as mock_create:
            mock_container = MagicMock()
            mock_service = MagicMock()
            mock_container.memory_service.return_value = mock_service
            mock_create.return_value = mock_container

            result = get_memory_service(custom_path)

            mock_create.assert_called_once_with(custom_path)
            assert result is mock_service


class TestGetWorkspaceManager:
    """Tests for get_workspace_manager factory function."""

    def test_returns_workspace_manager_instance(self) -> None:
        """Should return a WorkspaceManager instance via container."""
        from src.application.services.workspace.workspace_manager import WorkspaceManager

        db = Path("/tmp/test_wm.db")
        result = get_workspace_manager(db)
        assert isinstance(result, WorkspaceManager)

    def test_returns_container_singleton(self) -> None:
        """Should return the same instance for same db_path."""
        db = Path("/tmp/test_wm_singleton.db")
        result1 = get_workspace_manager(db)
        result2 = get_workspace_manager(db)
        assert result1 is result2


class TestDetectMemoryDbPath:
    """Tests for detect_memory_db_path function."""

    def test_returns_default_path_when_not_in_worktree(self) -> None:
        """Should return default path when not in a worktree."""
        with patch("src.infrastructure.persistence.container.get_workspace_manager") as mock_get_wm:
            mock_wm = MagicMock()
            mock_wm.detect_workspace.return_value = None
            mock_get_wm.return_value = mock_wm

            result = detect_memory_db_path()

            assert result == get_default_db_path()

    def test_returns_worktree_path_when_in_worktree(self) -> None:
        """Should return worktree-specific path when in a worktree."""
        with (
            patch("src.infrastructure.persistence.container.get_workspace_manager") as mock_get_wm,
            patch("src.infrastructure.persistence.container.Path.mkdir"),
        ):
            mock_workspace = MagicMock()
            mock_workspace.path = Path("/some/worktree")

            mock_wm = MagicMock()
            mock_wm.detect_workspace.return_value = mock_workspace
            mock_get_wm.return_value = mock_wm

            result = detect_memory_db_path()

            assert result == Path("/some/worktree/.memory/observations.db")

    def test_returns_default_on_detection_failure(self) -> None:
        """Should return default path when detection fails."""
        with patch("src.infrastructure.persistence.container.get_workspace_manager") as mock_get_wm:
            mock_get_wm.side_effect = OSError("Detection failed")

            result = detect_memory_db_path()

            assert result == get_default_db_path()


class TestGetMemoryServiceAuto:
    """Tests for get_memory_service_auto factory function."""

    def test_returns_memory_service_with_detected_path(self) -> None:
        """Should return MemoryService with auto-detected DB path."""
        with (
            patch("src.infrastructure.persistence.container.detect_memory_db_path") as mock_detect,
            patch("src.infrastructure.persistence.container.get_memory_service") as mock_get,
        ):
            detected_path = Path("/detected/memory.db")
            mock_detect.return_value = detected_path

            mock_service = MagicMock()
            mock_get.return_value = mock_service

            result = get_memory_service_auto()

            mock_detect.assert_called_once()
            mock_get.assert_called_once_with(detected_path)
            assert result is mock_service


class TestCreateContainer:
    """Tests for create_container factory function."""

    def test_creates_container_with_default_path(self) -> None:
        """Should create container with default DB path."""
        with patch(
            "src.infrastructure.persistence.container._run_migrations_on_init"
        ) as mock_migrate:
            container = create_container()

            # Container is created (dependency-injector returns DynamicContainer)
            assert container is not None
            mock_migrate.assert_called_once()

    def test_creates_container_with_custom_path(self) -> None:
        """Should create container with custom DB path."""
        custom_path = Path("/custom/db/path.db")

        with patch(
            "src.infrastructure.persistence.container._run_migrations_on_init"
        ) as mock_migrate:
            container = create_container(custom_path)

            # Container is created
            assert container is not None
            # Verify custom path was used
            from unittest.mock import ANY
            mock_migrate.assert_called_once_with(custom_path, ANY)
