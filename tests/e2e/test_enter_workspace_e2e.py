"""End-to-end tests for workspace enter command.

Tests:
- Enter workspace returns correct path
- Enter nonexistent workspace raises error
- Start workspace returns correct entity
- Enter workspace after creation
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.services.workspace.exceptions import WorkspaceNotFoundError
from src.application.services.workspace.workspace_manager import WorkspaceManager


class TestEnterWorkspaceE2E:
    """E2E tests for entering workspaces."""

    def test_enter_workspace_returns_correct_path(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that entering a workspace returns the correct path."""
        workspace_manager.create_workspace("enter-test")

        workspace = workspace_manager.start_workspace("enter-test")

        assert workspace.name == "enter-test"
        assert workspace.path.exists()
        assert workspace.path.is_dir()

    def test_enter_nonexistent_workspace_raises_error(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that entering a nonexistent workspace raises WorkspaceNotFoundError."""
        with pytest.raises(WorkspaceNotFoundError):
            workspace_manager.start_workspace("does-not-exist")

    def test_enter_workspace_after_multiple_creations(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that entering a specific workspace returns the right one."""
        workspace_manager.create_workspace("alpha")
        workspace_manager.create_workspace("beta")
        workspace_manager.create_workspace("gamma")

        alpha = workspace_manager.start_workspace("alpha")
        beta = workspace_manager.start_workspace("beta")

        assert alpha.name == "alpha"
        assert beta.name == "beta"
        assert alpha.path != beta.path

    def test_enter_workspace_has_correct_state(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that entered workspace has ACTIVE state."""
        workspace_manager.create_workspace("state-test")

        workspace = workspace_manager.start_workspace("state-test")

        assert workspace.state.value == "active"

    def test_enter_workspace_has_correct_layout(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that entered workspace reports correct layout."""
        workspace_manager.create_workspace("layout-enter-test")

        workspace = workspace_manager.start_workspace("layout-enter-test")

        assert workspace.layout is not None

    def test_enter_workspace_has_correct_repo_root(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test that entered workspace reports correct repo root."""
        workspace_manager.create_workspace("repo-root-test")

        workspace = workspace_manager.start_workspace("repo-root-test")

        assert workspace.repo_root == git_repo

    def test_enter_workspace_path_matches_worktree_path(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that the entered workspace path matches the actual worktree directory."""
        created = workspace_manager.create_workspace("path-match-test")
        entered = workspace_manager.start_workspace("path-match-test")

        assert created.path == entered.path

    def test_enter_workspace_list_and_enter_consistent(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that listed and entered workspace have matching properties."""
        workspace_manager.create_workspace("consistency-test")

        listed = workspace_manager.list_workspaces()
        assert len(listed) == 1

        entered = workspace_manager.start_workspace("consistency-test")

        assert listed[0].name == entered.name
        assert listed[0].path == entered.path
        assert listed[0].layout == entered.layout
