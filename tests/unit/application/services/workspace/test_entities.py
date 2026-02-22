"""Unit tests for workspace entities."""

import pytest
from pathlib import Path

from src.application.services.workspace.entities import (
    LayoutType,
    WorktreeState,
    Workspace,
    WorkspaceConfig,
)


class TestLayoutType:
    """Tests for LayoutType enum."""

    def test_layout_type_values(self) -> None:
        """Test LayoutType enum values."""
        assert LayoutType.NESTED.value == ".worktrees/<branch>/"
        assert LayoutType.OUTER_NESTED.value == "../<repo>.worktrees/<branch>/"
        assert LayoutType.SIBLING.value == "../<repo>-<branch>/"

    def test_layout_type_members(self) -> None:
        """Test LayoutType enum members."""
        assert len(LayoutType) == 3
        assert LayoutType.NESTED in LayoutType
        assert LayoutType.OUTER_NESTED in LayoutType
        assert LayoutType.SIBLING in LayoutType


class TestWorktreeState:
    """Tests for WorktreeState enum."""

    def test_worktree_state_values(self) -> None:
        """Test WorktreeState enum values."""
        assert WorktreeState.ACTIVE.value == "active"
        assert WorktreeState.MERGED.value == "merged"
        assert WorktreeState.REMOVED.value == "removed"

    def test_worktree_state_members(self) -> None:
        """Test WorktreeState enum members."""
        assert len(WorktreeState) == 3
        assert WorktreeState.ACTIVE in WorktreeState
        assert WorktreeState.MERGED in WorktreeState
        assert WorktreeState.REMOVED in WorktreeState


class TestWorkspace:
    """Tests for Workspace dataclass."""

    def test_create_workspace(self) -> None:
        """Test creating a Workspace instance."""
        path = Path("/test/repo/.worktrees/feature-branch")
        repo_root = Path("/test/repo")

        workspace = Workspace(
            name="feature-branch",
            path=path,
            layout=LayoutType.NESTED,
            state=WorktreeState.ACTIVE,
            repo_root=repo_root,
        )

        assert workspace.name == "feature-branch"
        assert workspace.path == path
        assert workspace.layout == LayoutType.NESTED
        assert workspace.state == WorktreeState.ACTIVE
        assert workspace.repo_root == repo_root

    def test_workspace_immutability(self) -> None:
        """Test that Workspace is immutable (frozen=True)."""
        workspace = Workspace(
            name="feature-branch",
            path=Path("/test/repo/.worktrees/feature-branch"),
            layout=LayoutType.NESTED,
            state=WorktreeState.ACTIVE,
            repo_root=Path("/test/repo"),
        )

        with pytest.raises(Exception):
            workspace.name = "new-name"

        with pytest.raises(Exception):
            workspace.state = WorktreeState.MERGED

    def test_workspace_validates_name_type(self) -> None:
        """Test that Workspace validates name is a string."""
        with pytest.raises(TypeError, match="name debe ser un string"):
            Workspace(
                name=123,  # type: ignore
                path=Path("/test/repo/.worktrees/feature-branch"),
                layout=LayoutType.NESTED,
                state=WorktreeState.ACTIVE,
                repo_root=Path("/test/repo"),
            )

    def test_workspace_validates_path_type(self) -> None:
        """Test that Workspace validates path is a Path."""
        with pytest.raises(TypeError, match="path debe ser un Path"):
            Workspace(
                name="feature-branch",
                path="/test/repo/.worktrees/feature-branch",  # type: ignore
                layout=LayoutType.NESTED,
                state=WorktreeState.ACTIVE,
                repo_root=Path("/test/repo"),
            )

    def test_workspace_validates_layout_type(self) -> None:
        """Test that Workspace validates layout is a LayoutType."""
        with pytest.raises(TypeError, match="layout debe ser un LayoutType"):
            Workspace(
                name="feature-branch",
                path=Path("/test/repo/.worktrees/feature-branch"),
                layout="nested",  # type: ignore
                state=WorktreeState.ACTIVE,
                repo_root=Path("/test/repo"),
            )

    def test_workspace_validates_state_type(self) -> None:
        """Test that Workspace validates state is a WorktreeState."""
        with pytest.raises(TypeError, match="state debe ser un WorktreeState"):
            Workspace(
                name="feature-branch",
                path=Path("/test/repo/.worktrees/feature-branch"),
                layout=LayoutType.NESTED,
                state="active",  # type: ignore
                repo_root=Path("/test/repo"),
            )

    def test_workspace_validates_repo_root_type(self) -> None:
        """Test that Workspace validates repo_root is a Path."""
        with pytest.raises(TypeError, match="repo_root debe ser un Path"):
            Workspace(
                name="feature-branch",
                path=Path("/test/repo/.worktrees/feature-branch"),
                layout=LayoutType.NESTED,
                state=WorktreeState.ACTIVE,
                repo_root="/test/repo",  # type: ignore
            )


class TestWorkspaceConfig:
    """Tests for WorkspaceConfig dataclass."""

    def test_create_workspace_config(self) -> None:
        """Test creating a WorkspaceConfig instance."""
        hooks_dir = Path("/test/repo/.git/hooks")

        config = WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=True,
            hooks_dir=hooks_dir,
        )

        assert config.default_layout == LayoutType.NESTED
        assert config.auto_cleanup is True
        assert config.hooks_dir == hooks_dir

    def test_create_workspace_config_with_none_hooks_dir(self) -> None:
        """Test creating a WorkspaceConfig with None hooks_dir."""
        config = WorkspaceConfig(
            default_layout=LayoutType.SIBLING,
            auto_cleanup=False,
            hooks_dir=None,
        )

        assert config.default_layout == LayoutType.SIBLING
        assert config.auto_cleanup is False
        assert config.hooks_dir is None

    def test_workspace_config_immutability(self) -> None:
        """Test that WorkspaceConfig is immutable (frozen=True)."""
        config = WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=True,
            hooks_dir=Path("/test/repo/.git/hooks"),
        )

        with pytest.raises(Exception):
            config.auto_cleanup = False

        with pytest.raises(Exception):
            config.default_layout = LayoutType.SIBLING

    def test_workspace_config_validates_layout_type(self) -> None:
        """Test that WorkspaceConfig validates default_layout is a LayoutType."""
        with pytest.raises(TypeError, match="default_layout debe ser un LayoutType"):
            WorkspaceConfig(
                default_layout="nested",  # type: ignore
                auto_cleanup=True,
                hooks_dir=Path("/test/repo/.git/hooks"),
            )

    def test_workspace_config_validates_auto_cleanup_type(self) -> None:
        """Test that WorkspaceConfig validates auto_cleanup is a bool."""
        with pytest.raises(TypeError, match="auto_cleanup debe ser un booleano"):
            WorkspaceConfig(
                default_layout=LayoutType.NESTED,
                auto_cleanup="true",  # type: ignore
                hooks_dir=Path("/test/repo/.git/hooks"),
            )

    def test_workspace_config_validates_hooks_dir_type(self) -> None:
        """Test that WorkspaceConfig validates hooks_dir is a Path or None."""
        with pytest.raises(TypeError, match="hooks_dir debe ser un Path o None"):
            WorkspaceConfig(
                default_layout=LayoutType.NESTED,
                auto_cleanup=True,
                hooks_dir="/test/repo/.git/hooks",  # type: ignore
            )

    def test_workspace_config_validates_hooks_dir_with_none(self) -> None:
        """Test that WorkspaceConfig accepts None for hooks_dir."""
        config = WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=True,
            hooks_dir=None,
        )
        assert config.hooks_dir is None
