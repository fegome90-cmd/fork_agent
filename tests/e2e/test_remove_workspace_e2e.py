"""End-to-end tests for workspace removal.

Tests:
- Create workspace
- Remove workspace
- Verify worktree removed from filesystem
- Verify worktree removed from git
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.application.services.workspace.exceptions import (
    WorkspaceNotCleanError,
    WorkspaceNotFoundError,
)
from src.application.services.workspace.workspace_manager import WorkspaceManager


class TestRemoveWorkspaceE2E:
    """E2E tests for workspace removal."""

    def test_remove_workspace_removes_directory(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that removing workspace removes the directory."""
        # Create workspace
        workspace = workspace_manager.create_workspace("remove-dir-test")
        workspace_path = workspace.path

        # Verify it exists
        assert workspace_path.exists()

        # Remove workspace
        workspace_manager.remove_workspace("remove-dir-test", force=True)

        # Verify it's removed
        assert not workspace_path.exists()

    def test_remove_workspace_removes_from_git_worktree_list(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test that removing workspace removes it from git worktree list."""
        # Create workspace
        workspace_manager.create_workspace("remove-git-test")

        # Verify it's in worktree list
        result = subprocess.run(
            ["git", "worktree", "list"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert "remove-git-test" in result.stdout or ".worktrees/remove-git-test" in result.stdout

        # Remove workspace
        workspace_manager.remove_workspace("remove-git-test", force=True)

        # Verify it's removed from worktree list
        result = subprocess.run(
            ["git", "worktree", "list"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert "remove-git-test" not in result.stdout

    def test_remove_workspace_removes_branch(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,
    ) -> None:
        """Test that removing workspace removes the branch."""
        # Create workspace
        workspace_manager.create_workspace("remove-branch-test")

        # Verify branch exists
        result = subprocess.run(
            ["git", "branch", "--list", "remove-branch-test"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert "remove-branch-test" in result.stdout

        # Remove workspace
        workspace_manager.remove_workspace("remove-branch-test", force=True)

        # Verify branch is removed
        result = subprocess.run(
            ["git", "branch", "--list", "remove-branch-test"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert "remove-branch-test" not in result.stdout

    def test_remove_nonexistent_workspace_raises_error(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that removing non-existent workspace raises error."""
        with pytest.raises(WorkspaceNotFoundError):
            workspace_manager.remove_workspace("nonexistent-workspace")

    def test_remove_workspace_with_uncommitted_changes_requires_force(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that removing workspace with changes requires force."""
        # Create workspace
        workspace = workspace_manager.create_workspace("dirty-workspace")

        # Add uncommitted file
        (workspace.path / "dirty.txt").write_text("uncommitted content")

        # Try to remove without force - should fail
        with pytest.raises(WorkspaceNotCleanError):
            workspace_manager.remove_workspace("dirty-workspace", force=False)

        # Remove with force - should succeed
        workspace_manager.remove_workspace("dirty-workspace", force=True)

        # Verify it's removed
        workspaces = workspace_manager.list_workspaces()
        assert not any(ws.name == "dirty-workspace" for ws in workspaces)

    def test_remove_workspace_with_force_ignores_dirty(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that force flag allows removal of dirty workspace."""
        # Create workspace
        workspace = workspace_manager.create_workspace("force-remove")

        # Add uncommitted file
        (workspace.path / "uncommitted.txt").write_text("content")

        # Remove with force - should succeed
        workspace_manager.remove_workspace("force-remove", force=True)

        # Verify it's removed
        workspaces = workspace_manager.list_workspaces()
        assert not any(ws.name == "force-remove" for ws in workspaces)

    def test_remove_one_workspace_keeps_others(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that removing one workspace keeps others intact."""
        # Create multiple workspaces
        workspace_manager.create_workspace("keep-1")
        workspace_manager.create_workspace("keep-2")
        workspace_manager.create_workspace("remove-only")

        # Remove one
        workspace_manager.remove_workspace("remove-only", force=True)

        # Verify others still exist
        workspaces = workspace_manager.list_workspaces()
        names = {ws.name for ws in workspaces}
        assert "keep-1" in names
        assert "keep-2" in names
        assert "remove-only" not in names

    def test_remove_workspace_updates_list(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that removing workspace updates the list."""
        # Create workspace
        workspace_manager.create_workspace("list-update")

        # Verify it shows in list
        workspaces = workspace_manager.list_workspaces()
        assert any(ws.name == "list-update" for ws in workspaces)

        # Remove it
        workspace_manager.remove_workspace("list-update", force=True)

        # Verify it's not in list
        workspaces = workspace_manager.list_workspaces()
        assert not any(ws.name == "list-update" for ws in workspaces)

    def test_remove_workspace_after_detect(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test removing workspace after detecting it."""
        # Create and detect workspace
        workspace = workspace_manager.create_workspace("detect-remove")
        detected = workspace_manager.detect_workspace(workspace.path)

        assert detected is not None
        assert detected.name == "detect-remove"

        # Remove it
        workspace_manager.remove_workspace("detect-remove", force=True)

        # Verify detection returns None
        detected = workspace_manager.detect_workspace(workspace.path)
        assert detected is None
