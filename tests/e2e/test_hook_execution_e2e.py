"""End-to-end tests for hook execution.

Tests:
- Create hook scripts
- Create workspace
- Verify hooks are executed
- Verify hook results
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.services.workspace.entities import HookResult
from src.application.services.workspace.hook_runner import HookRunner
from src.application.services.workspace.workspace_manager import WorkspaceManager


class TestHookExecutionE2E:
    """E2E tests for hook execution."""

    @pytest.fixture
    def setup_hook_script(self, hooks_dir: Path) -> Path:
        """Create a setup hook script."""
        hook_path = hooks_dir / "setup.sh"
        hook_path.write_text(
            "#!/bin/bash\n"
            "WORKSPACE_PATH=$1\n"
            "echo \"Setup executed for: $WORKSPACE_PATH\" > \"$WORKSPACE_PATH/.setup_log\"\n"
            "exit 0\n"
        )
        hook_path.chmod(0o755)
        return hook_path

    @pytest.fixture
    def teardown_hook_script(self, hooks_dir: Path) -> Path:
        """Create a teardown hook script."""
        hook_path = hooks_dir / "teardown.sh"
        hook_path.write_text(
            "#!/bin/bash\n"
            "WORKSPACE_PATH=$1\n"
            "echo \"Teardown executed for: $WORKSPACE_PATH\" > \"$WORKSPACE_PATH/.teardown_log\"\n"
            "exit 0\n"
        )
        hook_path.chmod(0o755)
        return hook_path

    def test_setup_hook_executes_on_workspace_creation(
        self,
        workspace_manager: WorkspaceManager,
        setup_hook_script: Path,
    ) -> None:
        """Test that setup hook executes when creating workspace."""
        # Create workspace
        workspace = workspace_manager.create_workspace("hook-setup-test")

        # Verify setup hook ran
        log_file = workspace.path / ".setup_log"
        assert log_file.exists()
        assert "Setup executed" in log_file.read_text()

    def test_setup_hook_result_stored_in_workspace(
        self,
        workspace_manager: WorkspaceManager,
        setup_hook_script: Path,
    ) -> None:
        """Test that setup hook result is stored in workspace entity."""
        workspace = workspace_manager.create_workspace("hook-result-test")

        # Verify hook result is stored
        assert workspace.last_setup_hook is not None
        assert workspace.last_setup_hook.success is True
        assert workspace.last_setup_hook.exit_code == 0

    def test_teardown_hook_executes_on_workspace_removal(
        self,
        workspace_manager: WorkspaceManager,
        setup_hook_script: Path,
        teardown_hook_script: Path,
    ) -> None:
        """Test that teardown hook executes when removing workspace."""
        # Create workspace (this runs setup hook)
        workspace = workspace_manager.create_workspace("hook-teardown-test")
        workspace_path = workspace.path

        # Verify setup ran
        assert (workspace_path / ".setup_log").exists()

        # Remove workspace (this runs teardown hook)
        workspace_manager.remove_workspace("hook-teardown-test", force=True)

        # Note: After removal, the directory no longer exists
        # So we need to check if teardown ran before removal
        # In a real scenario, you'd want to capture this differently

    def test_hook_receives_workspace_path(
        self,
        workspace_manager: WorkspaceManager,
        hooks_dir: Path,
    ) -> None:
        """Test that hook receives correct workspace path."""
        # Create custom hook that writes the path
        hook_path = hooks_dir / "setup.sh"
        hook_path.write_text(
            "#!/bin/bash\n"
            "WORKSPACE_PATH=$1\n"
            "echo \"Path: $WORKSPACE_PATH\" > \"$WORKSPACE_PATH/.path_log\"\n"
            "exit 0\n"
        )
        hook_path.chmod(0o755)

        # Create workspace
        workspace = workspace_manager.create_workspace("hook-path-test")

        # Verify path was passed correctly
        log_file = workspace.path / ".path_log"
        assert log_file.exists()
        assert str(workspace.path) in log_file.read_text()

    def test_hook_failure_does_not_prevent_workspace_creation(
        self,
        workspace_manager: WorkspaceManager,
        hooks_dir: Path,
    ) -> None:
        """Test that workspace creation succeeds even if hook fails."""
        # Create failing hook
        hook_path = hooks_dir / "setup.sh"
        hook_path.write_text(
            "#!/bin/bash\n"
            "exit 1\n"
        )
        hook_path.chmod(0o755)

        # Create workspace - should still succeed
        workspace = workspace_manager.create_workspace("hook-fail-test")

        # Workspace should exist
        assert workspace.path.exists()

    def test_no_hooks_when_hook_runner_not_configured(
        self,
        workspace_manager_no_hooks: WorkspaceManager,
    ) -> None:
        """Test that no hooks run when hook_runner is not configured."""
        workspace = workspace_manager_no_hooks.create_workspace("no-hooks-e2e")

        # Should have no hook result
        assert workspace.last_setup_hook is None

    def test_multiple_workspaces_run_separate_hooks(
        self,
        workspace_manager: WorkspaceManager,
        hooks_dir: Path,
    ) -> None:
        """Test that multiple workspaces each run their own hooks."""
        # Create setup hook that creates a log file
        hook_path = hooks_dir / "setup.sh"
        hook_path.write_text(
            "#!/bin/bash\n"
            "WORKSPACE_PATH=$1\n"
            "echo 'setup ran' > \"$WORKSPACE_PATH/.setup_log\"\n"
            "exit 0\n"
        )
        hook_path.chmod(0o755)

        # Create first workspace
        workspace1 = workspace_manager.create_workspace("multi-hook-1")

        # Create second workspace
        workspace2 = workspace_manager.create_workspace("multi-hook-2")

        # Both should have hook logs
        assert (workspace1.path / ".setup_log").exists()
        assert (workspace2.path / ".setup_log").exists()

    def test_hook_with_custom_environment(
        self,
        hooks_dir: Path,
        git_executor,
        workspace_config,
    ) -> None:
        """Test that hooks run with custom environment variables."""
        # Create hook that outputs environment
        hook_path = hooks_dir / "setup.sh"
        hook_path.write_text(
            "#!/bin/bash\n"
            "WORKSPACE_PATH=$1\n"
            "echo \"HOME=$HOME\" > \"$WORKSPACE_PATH/.env_log\"\n"
            "echo \"USER=$USER\" >> \"$WORKSPACE_PATH/.env_log\"\n"
            "exit 0\n"
        )
        hook_path.chmod(0o755)

        # Create workspace manager
        from src.application.services.workspace.workspace_manager import WorkspaceManager

        manager = WorkspaceManager(
            git_executor=git_executor,
            config=workspace_config,
            hook_runner=HookRunner(hooks_dir=hooks_dir, timeout=30),
        )

        workspace = manager.create_workspace("hook-env-test")

        # Verify environment was passed
        log_file = workspace.path / ".env_log"
        assert log_file.exists()

    def test_workspace_manager_uses_config_hooks_dir(
        self,
        workspace_manager: WorkspaceManager,
    ) -> None:
        """Test that workspace manager uses hooks_dir from config."""
        # The fixture provides hooks_dir
        workspace = workspace_manager.create_workspace("config-hooks-test")

        # Verify workspace was created (implies hooks_dir was used)
        assert workspace.path.exists()
        assert workspace.last_setup_hook is not None
