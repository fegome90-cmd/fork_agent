"""End-to-end tests for workspace creation.

Tests:
- Create workspace using CLI-style API
- Verify worktree exists on filesystem
- Verify branch was created in git
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.application.services.workspace.entities import (
    LayoutType,
    WorkspaceConfig,
    WorktreeState,
)
from src.application.services.workspace.workspace_manager import WorkspaceManager
from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor


class TestCreateWorkspaceE2E:
    """E2E tests for workspace creation."""

    def test_create_workspace_creates_worktree(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test that creating a workspace creates a valid worktree."""
        # Create workspace
        workspace = workspace_manager.create_workspace("feature-test")

        # Verify workspace entity
        assert workspace.name == "feature-test"
        assert workspace.state == WorktreeState.ACTIVE

        # Verify worktree directory exists
        assert workspace.path.exists()
        assert workspace.path.is_dir()

        # Verify worktree is a valid git worktree
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert workspace.path.name in result.stdout

    def test_create_workspace_creates_branch(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test that creating a workspace creates a new branch."""
        branch_name = "feature-branch"

        # Create workspace
        workspace = workspace_manager.create_workspace(branch_name)

        # Verify branch exists
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert branch_name in result.stdout

        # Verify the worktree is on the correct branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workspace.path,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == branch_name

    def test_create_workspace_with_nested_layout(
        self,
        git_executor: GitCommandExecutor,
        workspace_config: WorkspaceConfig,  # noqa: ARG002
    ) -> None:
        """Test workspace creation with NESTED layout."""
        config = WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=True,
            hooks_dir=None,
        )
        manager = WorkspaceManager(
            git_executor=git_executor,
            config=config,
            hook_runner=None,
        )

        workspace = manager.create_workspace("nested-workspace")

        # Verify path is nested under .worktrees/
        assert ".worktrees" in workspace.path.parts
        assert workspace.layout == LayoutType.NESTED

    def test_create_workspace_with_sibling_layout(
        self,
        git_executor: GitCommandExecutor,
        git_repo: Path,
    ) -> None:
        """Test workspace creation with SIBLING layout."""
        config = WorkspaceConfig(
            default_layout=LayoutType.SIBLING,
            auto_cleanup=True,
            hooks_dir=None,
        )
        manager = WorkspaceManager(
            git_executor=git_executor,
            config=config,
            hook_runner=None,
        )

        workspace = manager.create_workspace("sibling-workspace")

        # Verify path is a sibling directory
        assert workspace.path.parent == git_repo.parent
        assert workspace.layout == LayoutType.SIBLING

    def test_create_duplicate_workspace_raises_error(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that creating duplicate workspace raises error."""
        from src.application.services.workspace.exceptions import WorkspaceExistsError

        # Create first workspace
        workspace_manager.create_workspace("duplicate-test")

        # Try to create duplicate - should raise error
        with pytest.raises(WorkspaceExistsError):
            workspace_manager.create_workspace("duplicate-test")

    def test_create_workspace_preserves_main_branch(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test that creating a workspace doesn't affect main branch."""
        # Get initial main branch commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        initial_commit = result.stdout.strip()

        # Create workspace
        workspace_manager.create_workspace("feature-main")

        # Verify main branch unchanged
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == initial_commit

    def test_create_workspace_with_custom_layout_parameter(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test creating workspace with custom layout parameter."""
        workspace = workspace_manager.create_workspace(
            "custom-layout-workspace",
            layout=LayoutType.NESTED,
        )

        assert workspace.layout == LayoutType.NESTED
        assert ".worktrees" in workspace.path.parts
