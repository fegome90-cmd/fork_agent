"""Unit tests for WorkspaceDetector."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.workspace.entities import LayoutType, WorktreeState
from src.application.services.workspace.workspace_detector import WorkspaceDetector
from src.application.services.workspace.workspace_manager import WorkspaceManager


@pytest.fixture
def mock_git_executor() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_workspace_manager(mock_git_executor: MagicMock) -> MagicMock:
    manager = MagicMock(spec=WorkspaceManager)
    manager._git = mock_git_executor
    return manager


@pytest.fixture
def workspace_detector(mock_workspace_manager: MagicMock) -> WorkspaceDetector:
    return WorkspaceDetector(mock_workspace_manager)


class TestWorkspaceDetectorDetect:
    def test_detect_with_path(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/test/repo/.worktrees/feature")
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        with (
            patch.object(Path, "resolve", lambda self: self),
            patch.object(
                Path, "is_relative_to", lambda self, other: str(self).startswith(str(other) + "/")
            ),
        ):
            workspace = workspace_detector.detect(test_path)

        assert workspace is not None
        assert workspace.name == "feature"
        assert workspace.layout == LayoutType.NESTED
        assert workspace.state == WorktreeState.ACTIVE

    def test_detect_with_path_inside_worktree(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/test/repo/.worktrees/feature/src")
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        with (
            patch.object(Path, "resolve", lambda self: self),
            patch.object(
                Path, "is_relative_to", lambda self, other: str(self).startswith(str(other) + "/")
            ),
        ):
            workspace = workspace_detector.detect(test_path)

        assert workspace is not None
        assert workspace.name == "feature"

    def test_detect_returns_none_for_main_repo(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/test/repo")
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        with patch.object(Path, "resolve", lambda self: self):
            workspace = workspace_detector.detect(test_path)

        assert workspace is None

    def test_detect_returns_none_when_no_worktrees(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/some/other/path")
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        with patch.object(Path, "resolve", lambda self: self):
            workspace = workspace_detector.detect(test_path)

        assert workspace is None

    def test_detect_returns_none_on_path_resolve_error(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/invalid/path")

        def mock_resolve_err(self: Path) -> Path:
            raise OSError("Cannot resolve path")

        with patch.object(Path, "resolve", mock_resolve_err):
            workspace = workspace_detector.detect(test_path)

        assert workspace is None

    def test_detect_returns_none_on_get_repo_root_error(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/test/repo")
        mock_git_executor.get_repo_root.side_effect = Exception("Not a git repo")

        workspace = workspace_detector.detect(test_path)

        assert workspace is None

    def test_detect_uses_cwd_when_path_is_none(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        def mock_cwd() -> Path:
            return Path("/test/repo/.worktrees/feature")

        with (
            patch.object(Path, "resolve", lambda self: self),
            patch.object(
                Path, "is_relative_to", lambda self, other: str(self).startswith(str(other) + "/")
            ),
            patch("pathlib.Path.cwd", mock_cwd),
        ):
            workspace = workspace_detector.detect()

        assert workspace is not None
        assert workspace.name == "feature"

    def test_detect_handles_oserror_in_worktree_loop(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/test/repo/.worktrees/feature")
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        call_count = 0

        def mock_resolve(self: Path) -> Path:
            return self

        def mock_is_relative_to_err(self: Path, other: Path) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("Path error")
            return str(self).startswith(str(other) + "/")

        with patch.object(Path, "resolve", mock_resolve):
            with patch.object(Path, "is_relative_to", mock_is_relative_to_err):
                workspace = workspace_detector.detect(test_path)

        assert workspace is not None
        assert workspace.name == "feature"


class TestWorkspaceDetectorIsInWorkspace:
    def test_is_in_workspace_returns_true(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/test/repo/.worktrees/feature")
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        with (
            patch.object(Path, "resolve", lambda self: self),
            patch.object(
                Path, "is_relative_to", lambda self, other: str(self).startswith(str(other) + "/")
            ),
        ):
            result = workspace_detector.is_in_workspace(test_path)

        assert result is True

    def test_is_in_workspace_returns_false(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/some/other/path")
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        with patch.object(Path, "resolve", lambda self: self):
            result = workspace_detector.is_in_workspace(test_path)

        assert result is False


class TestWorkspaceDetectorGetWorkspaceName:
    def test_get_workspace_name_returns_name(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/test/repo/.worktrees/feature")
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        with (
            patch.object(Path, "resolve", lambda self: self),
            patch.object(
                Path, "is_relative_to", lambda self, other: str(self).startswith(str(other) + "/")
            ),
        ):
            name = workspace_detector.get_workspace_name(test_path)

        assert name == "feature"

    def test_get_workspace_name_returns_none_when_not_in_workspace(
        self, workspace_detector: WorkspaceDetector, mock_git_executor: MagicMock
    ) -> None:
        test_path = Path("/some/other/path")
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        with patch.object(Path, "resolve", lambda self: self):
            name = workspace_detector.get_workspace_name(test_path)

        assert name is None


class TestWorkspaceDetectorDetectLayout:
    def test_detect_layout_nested(self, workspace_detector: WorkspaceDetector) -> None:
        worktree_path = Path("/test/repo/.worktrees/feature")
        repo_root = Path("/test/repo")

        with (
            patch.object(Path, "resolve", lambda self: self),
            patch.object(
                Path, "is_relative_to", lambda self, other: str(self).startswith(str(other) + "/")
            ),
        ):
            layout = workspace_detector._detect_layout(worktree_path, repo_root)

        assert layout == LayoutType.NESTED

    def test_detect_layout_outer_nested(self, workspace_detector: WorkspaceDetector) -> None:
        worktree_path = Path("/test/repo.worktrees/feature")
        repo_root = Path("/test/repo")

        call_count = 0

        def mock_is_relative_to_outer(self: Path, other: Path) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return False
            return str(self).startswith(str(other) + "/")

        with patch.object(Path, "resolve", lambda self: self):
            with patch.object(Path, "is_relative_to", mock_is_relative_to_outer):
                layout = workspace_detector._detect_layout(worktree_path, repo_root)

        assert layout == LayoutType.OUTER_NESTED

    def test_detect_layout_sibling(self, workspace_detector: WorkspaceDetector) -> None:
        worktree_path = Path("/test/repo-feature")
        repo_root = Path("/test/repo")

        call_count = 0

        def mock_is_relative_to(self: Path, other: Path) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return False
            return str(self).startswith(str(other) + "/")

        with patch.object(Path, "resolve", lambda self: self):
            with patch.object(Path, "is_relative_to", mock_is_relative_to):
                layout = workspace_detector._detect_layout(worktree_path, repo_root)

        assert layout == LayoutType.SIBLING

    def test_detect_layout_falls_back_to_nested(
        self, workspace_detector: WorkspaceDetector
    ) -> None:
        worktree_path = Path("/some/other/location/feature")
        repo_root = Path("/test/repo")

        with patch.object(Path, "resolve", lambda self: self):
            with patch.object(Path, "is_relative_to", lambda self, other: False):
                layout = workspace_detector._detect_layout(worktree_path, repo_root)

        assert layout == LayoutType.NESTED

    def test_detect_layout_handles_oserror_nested(
        self, workspace_detector: WorkspaceDetector
    ) -> None:
        worktree_path = Path("/test/repo/.worktrees/feature")
        repo_root = Path("/test/repo")

        call_count = 0

        def mock_resolve_err(self: Path) -> Path:
            raise OSError("Cannot resolve")

        def mock_is_relative_to(self: Path, other: Path) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("Path error")
            return True

        with patch.object(Path, "resolve", mock_resolve_err):
            with patch.object(Path, "is_relative_to", mock_is_relative_to):
                layout = workspace_detector._detect_layout(worktree_path, repo_root)

        assert layout == LayoutType.NESTED


class TestWorkspaceDetectorGit:
    def test_git_property_returns_git_executor(
        self, workspace_detector: WorkspaceDetector, mock_workspace_manager: MagicMock
    ) -> None:
        git = workspace_detector._git

        assert git is mock_workspace_manager._git
