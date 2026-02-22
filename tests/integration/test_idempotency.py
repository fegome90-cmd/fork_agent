"""Integration tests for idempotency.

These tests verify:
- M-02: create_workspace is idempotent
- worktree_is_valid returns existing workspace
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from src.application.services.workspace.entities import LayoutType, WorkspaceConfig
from src.application.services.workspace.exceptions import WorkspaceExistsError
from src.application.services.workspace.workspace_manager import WorkspaceManager
from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor


class TestIdempotency:
    """Integration tests for idempotent operations."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repository."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Configure git user (required for commits)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit (required for worktree)
        (repo_path / "README.md").write_text("# Test Repository\n")
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        return repo_path

    @pytest.fixture
    def git_executor(self, git_repo: Path) -> GitCommandExecutor:
        """Create GitCommandExecutor pointing to test repo."""
        executor = GitCommandExecutor()
        # Verify we're in the test repo
        assert executor.get_repo_root() == git_repo.resolve()
        return executor

    @pytest.fixture
    def workspace_config(self) -> WorkspaceConfig:
        """Create workspace configuration."""
        return WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=True,
            hooks_dir=None,
        )

    @pytest.fixture
    def workspace_manager(
        self, git_executor: GitCommandExecutor, workspace_config: WorkspaceConfig
    ) -> WorkspaceManager:
        """Create WorkspaceManager instance."""
        return WorkspaceManager(
            git_executor=git_executor,
            config=workspace_config,
            hook_runner=None,
        )


class TestCreateWorkspaceIdempotency(TestIdempotency):
    """Tests for M-02: create_workspace idempotency."""

    def test_create_workspace_idempotent(
        self, workspace_manager: WorkspaceManager, git_repo: Path
    ) -> None:
        """Test that create_workspace is idempotent (M-02).

        Creating the same workspace twice should raise WorkspaceExistsError
        instead of creating duplicates.
        """
        # First creation should succeed
        workspace = workspace_manager.create_workspace("feature-test")
        assert workspace.name == "feature-test"
        assert workspace.state.value == "active"

        # Second creation should fail with WorkspaceExistsError
        with pytest.raises(WorkspaceExistsError) as exc_info:
            workspace_manager.create_workspace("feature-test")

        assert "already exists" in str(exc_info.value).lower()

        # Verify only one worktree exists with this name
        worktrees = workspace_manager.list_workspaces()
        feature_worktrees = [wt for wt in worktrees if wt.name == "feature-test"]
        assert len(feature_worktrees) == 1

    def test_create_different_workspaces_allowed(
        self, workspace_manager: WorkspaceManager, git_repo: Path
    ) -> None:
        """Test that creating different workspaces is allowed."""
        # Create first workspace
        ws1 = workspace_manager.create_workspace("feature-a")
        assert ws1.name == "feature-a"

        # Create second workspace
        ws2 = workspace_manager.create_workspace("feature-b")
        assert ws2.name == "feature-b"

        # Both should exist
        worktrees = workspace_manager.list_workspaces()
        assert len(worktrees) == 2

    def test_idempotency_with_different_layouts(
        self, workspace_manager: WorkspaceManager, git_repo: Path
    ) -> None:
        """Test idempotency with different layouts."""
        # Create with NESTED layout (default)
        ws1 = workspace_manager.create_workspace("layout-test")
        assert ws1.layout == LayoutType.NESTED

        # Trying to create with different layout should also fail
        with pytest.raises(WorkspaceExistsError):
            workspace_manager.create_workspace("layout-test", layout=LayoutType.SIBLING)


class TestWorktreeIsValid(TestIdempotency):
    """Tests for worktree_is_valid functionality."""

    def test_worktree_is_valid_returns_existing_workspace(
        self, workspace_manager: WorkspaceManager, git_repo: Path
    ) -> None:
        """Test that worktree_is_valid returns existing workspace (M-02)."""
        # Create a workspace
        workspace = workspace_manager.create_workspace("validation-test")
        assert workspace.name == "validation-test"

        # Verify worktree_is_valid returns True for existing workspace
        executor = workspace_manager._git  # Access the git executor
        is_valid = executor.worktree_is_valid(workspace.path)

        assert is_valid is True

    def test_worktree_is_valid_for_nonexistent_path(
        self, workspace_manager: WorkspaceManager, tmp_path: Path
    ) -> None:
        """Test worktree_is_valid returns False for non-existent path."""
        executor = workspace_manager._git

        nonexistent_path = tmp_path / "nonexistent" / "worktree"
        is_valid = executor.worktree_is_valid(nonexistent_path)

        assert is_valid is False

    def test_worktree_is_valid_for_main_repo(
        self, workspace_manager: WorkspaceManager, git_repo: Path
    ) -> None:
        """Test worktree_is_valid returns False for main repo."""
        executor = workspace_manager._git

        # Main repo is also a valid git directory but not a worktree
        is_valid = executor.worktree_is_valid(git_repo)

        # Should return False because it's the main repo, not a worktree
        assert is_valid is False


class TestWorkspaceStateAfterOperations(TestIdempotency):
    """Tests for workspace state consistency."""

    def test_workspace_state_after_creation(
        self, workspace_manager: WorkspaceManager
    ) -> None:
        """Test workspace has correct state after creation."""
        workspace = workspace_manager.create_workspace("state-test")

        from src.application.services.workspace.entities import WorktreeState

        assert workspace.state == WorktreeState.ACTIVE

    def test_workspace_found_after_creation(
        self, workspace_manager: WorkspaceManager
    ) -> None:
        """Test workspace can be found after creation."""
        created = workspace_manager.create_workspace("find-test")

        found = workspace_manager.start_workspace("find-test")

        assert found.name == created.name
        assert found.path == created.path
