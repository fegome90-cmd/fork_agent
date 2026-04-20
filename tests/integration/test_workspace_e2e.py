"""End-to-end integration tests for workspace creation.

These tests verify:
- Complete workspace creation flow with hooks
- Workspace removal flow with hooks
- List workspaces after creation
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.application.services.workspace.entities import (
    LayoutType,
    WorkspaceConfig,
)
from src.application.services.workspace.hook_runner import HookRunner
from src.application.services.workspace.workspace_manager import WorkspaceManager
from src.infrastructure.platform.git.git_command_executor import GitCommandExecutor


class TestWorkspaceE2E:
    """End-to-end tests for workspace management with hooks."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a temporary git repository with initial commit."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Configure git user
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

        # Create initial commit
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
    def hooks_dir(self, git_repo: Path) -> Path:
        """Create hooks directory within the repo."""
        hooks_dir = git_repo / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        return hooks_dir

    @pytest.fixture
    def setup_hook(self, hooks_dir: Path, git_repo: Path) -> Path:  # noqa: ARG002
        """Create a setup hook script."""
        hook_path = hooks_dir / "setup.sh"
        hook_path.write_text(
            "#!/bin/bash\n"
            "WORKSPACE_PATH=$1\n"
            'echo "Setup hook running for: $WORKSPACE_PATH" > "$WORKSPACE_PATH/.setup_log"\n'
            'echo "Workspace: $WORKSPACE_PATH" >> "$WORKSPACE_PATH/.setup_log"\n'
            "exit 0\n"
        )
        hook_path.chmod(0o755)
        return hook_path

    @pytest.fixture
    def teardown_hook(self, hooks_dir: Path, git_repo: Path) -> Path:  # noqa: ARG002
        """Create a teardown hook script."""
        hook_path = hooks_dir / "teardown.sh"
        hook_path.write_text(
            "#!/bin/bash\n"
            "WORKSPACE_PATH=$1\n"
            'echo "Teardown hook running for: $WORKSPACE_PATH" > "$WORKSPACE_PATH/.teardown_log"\n'
            "exit 0\n"
        )
        hook_path.chmod(0o755)
        return hook_path

    @pytest.fixture
    def git_executor(self, git_repo: Path) -> GitCommandExecutor:
        """Create GitCommandExecutor."""
        return GitCommandExecutor(repo_path=git_repo)

    @pytest.fixture
    def hook_runner(self, hooks_dir: Path) -> HookRunner:
        """Create HookRunner."""
        return HookRunner(hooks_dir=hooks_dir, timeout=30)

    @pytest.fixture
    def workspace_config(self, hooks_dir: Path) -> WorkspaceConfig:
        """Create workspace configuration with hooks."""
        return WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=True,
            hooks_dir=hooks_dir,
        )

    @pytest.fixture
    def workspace_manager(
        self,
        git_executor: GitCommandExecutor,
        workspace_config: WorkspaceConfig,
        hook_runner: HookRunner,
    ) -> WorkspaceManager:
        """Create WorkspaceManager with hooks."""
        return WorkspaceManager(
            git_executor=git_executor,
            config=workspace_config,
            hook_runner=hook_runner,
        )


class TestWorkspaceCreationWithHooks(TestWorkspaceE2E):
    """Tests for complete workspace creation flow with hooks."""

    def test_create_workspace_with_setup_hook(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,  # noqa: ARG002
        setup_hook: Path,  # noqa: ARG002
    ) -> None:
        """Test complete workspace creation with setup hook."""
        # Create workspace
        workspace = workspace_manager.create_workspace("feature-e2e")

        # Verify workspace was created
        assert workspace.name == "feature-e2e"
        assert workspace.path.exists()

        # Verify setup hook ran and created log file
        log_file = workspace.path / ".setup_log"
        assert log_file.exists()
        assert "Setup hook running" in log_file.read_text()

        # Verify hook result is stored in workspace
        assert workspace.last_setup_hook is not None
        assert workspace.last_setup_hook.success is True

    def test_create_workspace_without_hooks(
        self, git_executor: GitCommandExecutor, workspace_config: WorkspaceConfig
    ) -> None:
        """Test workspace creation without hooks."""
        # Create manager without hook runner
        manager = WorkspaceManager(
            git_executor=git_executor,
            config=workspace_config,
            hook_runner=None,
        )

        workspace = manager.create_workspace("no-hooks-test")

        assert workspace.name == "no-hooks-test"
        assert workspace.last_setup_hook is None

    def test_create_workspace_with_custom_layout(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,  # noqa: ARG002
    ) -> None:
        """Test workspace creation with custom layout."""
        workspace = workspace_manager.create_workspace(
            "feature-custom-layout",
            layout=LayoutType.NESTED,
        )

        assert workspace.layout == LayoutType.NESTED
        assert workspace.name == "feature-custom-layout"


class TestWorkspaceRemovalWithHooks(TestWorkspaceE2E):
    """Tests for workspace removal flow with hooks."""

    def test_remove_workspace_with_teardown_hook(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,  # noqa: ARG002
        teardown_hook: Path,  # noqa: ARG002
    ) -> None:
        """Test workspace removal with teardown hook."""
        # First create a workspace
        workspace = workspace_manager.create_workspace("remove-test")
        workspace_path = workspace.path
        assert workspace_path.exists()

        # Now remove it
        workspace_manager.remove_workspace("remove-test", force=True)

        # Verify worktree is removed
        worktrees = workspace_manager.list_workspaces()
        removed_workspace = [wt for wt in worktrees if wt.name == "remove-test"]
        assert len(removed_workspace) == 0

    def test_remove_nonexistent_workspace_raises_error(
        self, workspace_manager: WorkspaceManager
    ) -> None:
        """Test removing non-existent workspace raises error."""
        from src.application.services.workspace.exceptions import (
            WorkspaceNotFoundError,
        )

        with pytest.raises(WorkspaceNotFoundError):
            workspace_manager.remove_workspace("nonexistent-workspace")

    def test_remove_workspace_with_uncommitted_changes(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,  # noqa: ARG002
    ) -> None:
        """Test removing workspace with uncommitted changes requires force."""
        from src.application.services.workspace.exceptions import (
            WorkspaceNotCleanError,
        )

        # Create workspace
        workspace = workspace_manager.create_workspace("dirty-workspace")

        # Add uncommitted changes
        (workspace.path / "new_file.txt").write_text("uncommitted content")

        # Try to remove without force - should fail
        with pytest.raises(WorkspaceNotCleanError):
            workspace_manager.remove_workspace("dirty-workspace", force=False)

        # Remove with force - should succeed
        workspace_manager.remove_workspace("dirty-workspace", force=True)

        # Verify it's removed
        worktrees = workspace_manager.list_workspaces()
        assert not any(wt.name == "dirty-workspace" for wt in worktrees)


class TestListWorkspaces(TestWorkspaceE2E):
    """Tests for listing workspaces."""

    def test_list_workspaces_after_creation(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,  # noqa: ARG002
    ) -> None:
        """Test list workspaces after creation."""
        # Initially empty (only main repo)
        worktrees = workspace_manager.list_workspaces()
        initial_count = len(worktrees)

        # Create a workspace
        workspace_manager.create_workspace("list-test-1")

        # Should have one more workspace
        worktrees = workspace_manager.list_workspaces()
        assert len(worktrees) == initial_count + 1
        assert any(wt.name == "list-test-1" for wt in worktrees)

    def test_list_multiple_workspaces(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,  # noqa: ARG002
    ) -> None:
        """Test listing multiple workspaces."""
        # Create multiple workspaces
        workspace_manager.create_workspace("multi-1")
        workspace_manager.create_workspace("multi-2")
        workspace_manager.create_workspace("multi-3")

        # List all workspaces
        worktrees = workspace_manager.list_workspaces()

        # Should have 3 workspaces
        names = [wt.name for wt in worktrees]
        assert "multi-1" in names
        assert "multi-2" in names
        assert "multi-3" in names

    def test_list_workspaces_includes_details(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,  # noqa: ARG002
    ) -> None:
        """Test that list includes correct workspace details."""
        workspace_manager.create_workspace("detail-test")

        worktrees = workspace_manager.list_workspaces()
        found = next(wt for wt in worktrees if wt.name == "detail-test")

        assert found.name == "detail-test"
        assert found.path.exists()
        assert found.layout == LayoutType.NESTED


class TestFullWorkflowE2E(TestWorkspaceE2E):
    """End-to-end tests for complete workflows."""

    def test_full_create_list_remove_workflow(
        self,
        workspace_manager: WorkspaceManager,
        git_repo: Path,  # noqa: ARG002
        setup_hook: Path,  # noqa: ARG002
        teardown_hook: Path,  # noqa: ARG002
    ) -> None:
        """Test complete workflow: create, list, remove."""
        # Step 1: Create workspace
        workspace = workspace_manager.create_workspace("workflow-test")
        assert workspace.name == "workflow-test"

        # Step 2: Verify it's in the list
        worktrees = workspace_manager.list_workspaces()
        assert any(wt.name == "workflow-test" for wt in worktrees)

        # Step 3: Start/find workspace
        found = workspace_manager.start_workspace("workflow-test")
        assert found.name == "workflow-test"

        # Step 4: Remove workspace
        workspace_manager.remove_workspace("workflow-test", force=True)

        # Step 5: Verify it's removed from list
        worktrees = workspace_manager.list_workspaces()
        assert not any(wt.name == "workflow-test" for wt in worktrees)

    def test_workspace_survives_manager_recreation(
        self, git_executor: GitCommandExecutor, workspace_config: WorkspaceConfig
    ) -> None:
        """Test that workspaces persist across manager instances."""
        # Create first manager and workspace
        manager1 = WorkspaceManager(
            git_executor=git_executor,
            config=workspace_config,
            hook_runner=None,
        )
        workspace1 = manager1.create_workspace("persist-test")

        # Create new manager instance
        manager2 = WorkspaceManager(
            git_executor=git_executor,
            config=workspace_config,
            hook_runner=None,
        )

        # Workspace should still exist
        found = manager2.start_workspace("persist-test")
        assert found.name == workspace1.name
        assert found.path == workspace1.path
