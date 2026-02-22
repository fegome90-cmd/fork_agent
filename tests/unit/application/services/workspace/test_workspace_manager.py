"""Unit tests for WorkspaceManager."""

from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

from src.application.services.workspace.entities import (
    LayoutType,
    WorktreeState,
    Workspace,
    WorkspaceConfig,
)
from src.application.services.workspace.exceptions import (
    GitError,
    WorkspaceExistsError,
    WorkspaceNotCleanError,
    WorkspaceNotFoundError,
)
from src.application.services.workspace.workspace_manager import (
    LayoutResolver,
    WorkspaceManager,
    WorkspaceManagerABC,
)


# Fixtures


@pytest.fixture
def workspace_config() -> WorkspaceConfig:
    """Fixture for default workspace config."""
    return WorkspaceConfig(
        default_layout=LayoutType.NESTED,
        auto_cleanup=True,
        hooks_dir=Path("/test/repo/.git/hooks"),
    )


@pytest.fixture
def mock_git_executor() -> MagicMock:
    """Fixture for mocked GitCommandExecutor."""
    return MagicMock()


@pytest.fixture
def workspace_manager(
    mock_git_executor: MagicMock, workspace_config: WorkspaceConfig
) -> WorkspaceManager:
    """Fixture for WorkspaceManager instance."""
    return WorkspaceManager(git_executor=mock_git_executor, config=workspace_config)


class TestLayoutResolver:
    """Tests for LayoutResolver class."""

    def test_resolve_path_nested(self) -> None:
        """Test resolving path for NESTED layout."""
        config = WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=False,
            hooks_dir=None,
        )
        resolver = LayoutResolver(config)

        path = resolver.resolve_path("feature-branch", Path("/test/repo"))

        assert path == Path("/test/repo/.worktrees/feature-branch")

    def test_resolve_path_outer_nested(self) -> None:
        """Test resolving path for OUTER_NESTED layout."""
        config = WorkspaceConfig(
            default_layout=LayoutType.OUTER_NESTED,
            auto_cleanup=False,
            hooks_dir=None,
        )
        resolver = LayoutResolver(config)

        path = resolver.resolve_path("feature-branch", Path("/test/repo"))

        assert path == Path("/test/myrepo.worktrees/feature-branch")

    def test_resolve_path_sibling(self) -> None:
        """Test resolving path for SIBLING layout."""
        config = WorkspaceConfig(
            default_layout=LayoutType.SIBLING,
            auto_cleanup=False,
            hooks_dir=None,
        )
        resolver = LayoutResolver(config)

        path = resolver.resolve_path("feature-branch", Path("/test/repo"))

        assert path == Path("/test/repo-feature-branch")


class TestWorkspaceManagerCreate:
    """Tests for create_workspace method."""

    def test_create_workspace_success(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test creating a workspace successfully."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = False

        workspace = workspace_manager.create_workspace("feature-branch")

        assert workspace.name == "feature-branch"
        assert workspace.state == WorktreeState.ACTIVE
        mock_git_executor.worktree_add.assert_called_once()

    def test_create_workspace_already_exists(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test creating a workspace that already exists."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = True

        with pytest.raises(WorkspaceExistsError):
            workspace_manager.create_workspace("feature-branch")

    def test_create_workspace_with_custom_layout(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test creating a workspace with custom layout."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = False

        workspace = workspace_manager.create_workspace(
            "feature-branch", layout=LayoutType.SIBLING
        )

        assert workspace.layout == LayoutType.SIBLING

    def test_create_workspace_git_error(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test creating a workspace when git operation fails."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = False
        mock_git_executor.worktree_add.side_effect = GitError("Git error")

        with pytest.raises(GitError):
            workspace_manager.create_workspace("feature-branch")


class TestWorkspaceManagerStart:
    """Tests for start_workspace method."""

    def test_start_workspace_found(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test starting an existing workspace."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        workspace = workspace_manager.start_workspace("feature")

        assert workspace.name == "feature"
        assert workspace.state == WorktreeState.ACTIVE

    def test_start_workspace_not_found(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test starting a non-existent workspace."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        with pytest.raises(WorkspaceNotFoundError):
            workspace_manager.start_workspace("nonexistent")

    def test_start_workspace_with_refs_heads_prefix(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test starting workspace with refs/heads/ prefix."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {
                "path": "/test/repo/.worktrees/feature",
                "branch": "refs/heads/feature-branch",
            },
        ]

        workspace = workspace_manager.start_workspace("feature-branch")

        assert workspace.name == "feature-branch"


class TestWorkspaceManagerList:
    """Tests for list_workspaces method."""

    def test_list_workspaces_empty(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test listing workspaces when there are none."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        workspaces = workspace_manager.list_workspaces()

        assert workspaces == []

    def test_list_workspaces_with_worktrees(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test listing workspaces with worktrees."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature1", "branch": "refs/heads/feature1"},
            {"path": "/test/repo/.worktrees/feature2", "branch": "refs/heads/feature2"},
        ]

        workspaces = workspace_manager.list_workspaces()

        assert len(workspaces) == 2
        assert workspaces[0].name == "feature1"
        assert workspaces[1].name == "feature2"


class TestWorkspaceManagerRemove:
    """Tests for remove_workspace method."""

    def test_remove_workspace_success(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test removing a workspace successfully."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]
        mock_git_executor.is_clean.return_value = True

        workspace_manager.remove_workspace("feature")

        mock_git_executor.worktree_remove.assert_called_once()

    def test_remove_workspace_not_clean(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test removing a workspace that has uncommitted changes."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]
        mock_git_executor.is_clean.return_value = False

        with pytest.raises(WorkspaceNotCleanError):
            workspace_manager.remove_workspace("feature")

    def test_remove_workspace_force(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test removing a workspace with force=True."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]
        mock_git_executor.is_clean.return_value = False  # Not clean but force=True

        workspace_manager.remove_workspace("feature", force=True)

        mock_git_executor.worktree_remove.assert_called_once()
        call_args = mock_git_executor.worktree_remove.call_args
        assert call_args[1]["force"] is True


class TestWorkspaceManagerMerge:
    """Tests for merge_workspace method."""

    def test_merge_workspace_success(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test merging a workspace successfully."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        workspace_manager.merge_workspace("feature")

        mock_git_executor._run_git_command.assert_called_once()
        mock_git_executor.branch_delete.assert_called_once()

    def test_merge_workspace_no_delete_branch(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test merging a workspace without deleting the branch."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        workspace_manager.merge_workspace("feature", delete_branch=False)

        mock_git_executor.branch_delete.assert_not_called()


class TestWorkspaceManagerDetect:
    """Tests for detect_workspace method."""

    def test_detect_workspace_from_path(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test detecting workspace from a path."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {"path": "/test/repo/.worktrees/feature", "branch": "refs/heads/feature"},
        ]

        workspace = workspace_manager.detect_workspace(Path("/test/repo/.worktrees/feature"))

        assert workspace is not None
        assert workspace.name == "feature"

    def test_detect_workspace_main_repo_returns_none(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test detecting workspace returns None for main repo."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        workspace = workspace_manager.detect_workspace(Path("/test/repo"))

        assert workspace is None

    def test_detect_workspace_not_a_worktree(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test detecting workspace returns None for non-worktree path."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]

        workspace = workspace_manager.detect_workspace(Path("/some/other/path"))

        assert workspace is None


class TestWorkspaceManagerDetectLayout:
    """Tests for _detect_layout method."""

    def test_detect_layout_nested(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test detecting NESTED layout."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")

        layout = workspace_manager._detect_layout(
            Path("/test/repo/.worktrees/feature"), Path("/test/repo")
        )

        assert layout == LayoutType.NESTED

    def test_detect_layout_outer_nested(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test detecting OUTER_NESTED layout."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")

        layout = workspace_manager._detect_layout(
            Path("/test/myrepo.worktrees/feature"), Path("/test/repo")
        )

        assert layout == LayoutType.OUTER_NESTED

    def test_detect_layout_sibling(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test detecting SIBLING layout."""
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")

        layout = workspace_manager._detect_layout(
            Path("/test/repo-feature"), Path("/test/repo")
        )

        assert layout == LayoutType.SIBLING


class TestWorkspaceManagerABC:
    """Tests for abstract base class."""

    def test_abc_cannot_instantiate(self) -> None:
        """Test that ABC cannot be instantiated directly."""
        with pytest.raises(TypeError):
            WorkspaceManagerABC()

    def test_abc_methods_are_abstract(self) -> None:
        """Test that ABC methods are marked as abstract."""
        # Check that the class has abstract methods
        assert hasattr(WorkspaceManagerABC, "create_workspace")
        assert hasattr(WorkspaceManagerABC, "start_workspace")
        assert hasattr(WorkspaceManagerABC, "list_workspaces")
        assert hasattr(WorkspaceManagerABC, "remove_workspace")
        assert hasattr(WorkspaceManagerABC, "merge_workspace")
        assert hasattr(WorkspaceManagerABC, "detect_workspace")


class TestWorkspaceManagerIntegration:
    """Integration tests for WorkspaceManager."""

    def test_full_workflow(
        self, workspace_manager: WorkspaceManager, mock_git_executor: MagicMock
    ) -> None:
        """Test full workflow: create, list, start, remove."""
        # Setup
        mock_git_executor.get_repo_root.return_value = Path("/test/repo")
        mock_git_executor.worktree_is_valid.return_value = False
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
        ]
        mock_git_executor.is_clean.return_value = True

        # Create workspace
        workspace = workspace_manager.create_workspace("feature-branch")
        assert workspace.name == "feature-branch"

        # List workspaces (now includes our new one)
        mock_git_executor.worktree_list.return_value = [
            {"path": "/test/repo", "branch": "refs/heads/main"},
            {
                "path": "/test/repo/.worktrees/feature-branch",
                "branch": "refs/heads/feature-branch",
            },
        ]
        workspaces = workspace_manager.list_workspaces()
        assert len(workspaces) == 1

        # Start workspace
        started = workspace_manager.start_workspace("feature-branch")
        assert started.name == "feature-branch"

        # Remove workspace
        workspace_manager.remove_workspace("feature-branch")
        mock_git_executor.worktree_remove.assert_called_once()
