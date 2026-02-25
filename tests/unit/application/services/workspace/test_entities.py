"""Unit tests for workspace entities."""

from pathlib import Path

import pytest

from src.application.services.workspace.entities import (
    HookResult,
    LayoutType,
    Workspace,
    WorkspaceConfig,
    WorkspaceHook,
    WorktreeState,
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
        from dataclasses import FrozenInstanceError

        workspace = Workspace(
            name="feature-branch",
            path=Path("/test/repo/.worktrees/feature-branch"),
            layout=LayoutType.NESTED,
            state=WorktreeState.ACTIVE,
            repo_root=Path("/test/repo"),
        )

        with pytest.raises(FrozenInstanceError):
            workspace.name = "new-name"

        with pytest.raises(FrozenInstanceError):
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

    def test_workspace_with_last_setup_hook(self) -> None:
        """Test creating Workspace with last_setup_hook."""
        hook_result = HookResult(
            success=True,
            exit_code=0,
            stdout="Setup done",
            stderr="",
            duration_ms=50,
        )
        workspace = Workspace(
            name="feature-branch",
            path=Path("/test/repo/.worktrees/feature-branch"),
            layout=LayoutType.NESTED,
            state=WorktreeState.ACTIVE,
            repo_root=Path("/test/repo"),
            last_setup_hook=hook_result,
        )
        assert workspace.last_setup_hook == hook_result

    def test_workspace_with_last_teardown_hook(self) -> None:
        """Test creating Workspace with last_teardown_hook."""
        hook_result = HookResult(
            success=True,
            exit_code=0,
            stdout="Teardown done",
            stderr="",
            duration_ms=50,
        )
        workspace = Workspace(
            name="feature-branch",
            path=Path("/test/repo/.worktrees/feature-branch"),
            layout=LayoutType.NESTED,
            state=WorktreeState.ACTIVE,
            repo_root=Path("/test/repo"),
            last_teardown_hook=hook_result,
        )
        assert workspace.last_teardown_hook == hook_result

    def test_workspace_validates_last_setup_hook_type(self) -> None:
        """Test that Workspace validates last_setup_hook is HookResult or None."""
        with pytest.raises(TypeError, match="last_setup_hook debe ser un HookResult o None"):
            Workspace(
                name="feature-branch",
                path=Path("/test/repo/.worktrees/feature-branch"),
                layout=LayoutType.NESTED,
                state=WorktreeState.ACTIVE,
                repo_root=Path("/test/repo"),
                last_setup_hook="not a hook result",  # type: ignore
            )

    def test_workspace_validates_last_teardown_hook_type(self) -> None:
        """Test that Workspace validates last_teardown_hook is HookResult or None."""
        with pytest.raises(TypeError, match="last_teardown_hook debe ser un HookResult o None"):
            Workspace(
                name="feature-branch",
                path=Path("/test/repo/.worktrees/feature-branch"),
                layout=LayoutType.NESTED,
                state=WorktreeState.ACTIVE,
                repo_root=Path("/test/repo"),
                last_teardown_hook="not a hook result",  # type: ignore
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
        from dataclasses import FrozenInstanceError

        config = WorkspaceConfig(
            default_layout=LayoutType.NESTED,
            auto_cleanup=True,
            hooks_dir=Path("/test/repo/.git/hooks"),
        )

        with pytest.raises(FrozenInstanceError):
            config.auto_cleanup = False

        with pytest.raises(FrozenInstanceError):
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


class TestHookResult:
    """Tests for HookResult dataclass."""

    def test_create_hook_result(self) -> None:
        """Test creating a HookResult instance."""
        result = HookResult(
            success=True,
            exit_code=0,
            stdout="Setup complete",
            stderr="",
            duration_ms=100,
        )
        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "Setup complete"
        assert result.stderr == ""
        assert result.duration_ms == 100

    def test_hook_result_immutability(self) -> None:
        """Test that HookResult is immutable (frozen=True)."""
        from dataclasses import FrozenInstanceError

        result = HookResult(
            success=True,
            exit_code=0,
            stdout="output",
            stderr="",
            duration_ms=100,
        )
        with pytest.raises(FrozenInstanceError):
            result.success = False
        with pytest.raises(FrozenInstanceError):
            result.exit_code = 1

    def test_hook_result_validates_success_type(self) -> None:
        """Test that HookResult validates success is a bool."""
        with pytest.raises(TypeError, match="success debe ser un booleano"):
            HookResult(
                success="true",  # type: ignore
                exit_code=0,
                stdout="output",
                stderr="",
                duration_ms=100,
            )

    def test_hook_result_validates_exit_code_type(self) -> None:
        """Test that HookResult validates exit_code is an int."""
        with pytest.raises(TypeError, match="exit_code debe ser un entero"):
            HookResult(
                success=True,
                exit_code="0",  # type: ignore
                stdout="output",
                stderr="",
                duration_ms=100,
            )

    def test_hook_result_validates_stdout_type(self) -> None:
        """Test that HookResult validates stdout is a string."""
        with pytest.raises(TypeError, match="stdout debe ser un string"):
            HookResult(
                success=True,
                exit_code=0,
                stdout=123,  # type: ignore
                stderr="",
                duration_ms=100,
            )

    def test_hook_result_validates_stderr_type(self) -> None:
        """Test that HookResult validates stderr is a string."""
        with pytest.raises(TypeError, match="stderr debe ser un string"):
            HookResult(
                success=True,
                exit_code=0,
                stdout="",
                stderr=123,  # type: ignore
                duration_ms=100,
            )

    def test_hook_result_validates_duration_ms_type(self) -> None:
        """Test that HookResult validates duration_ms is an int."""
        with pytest.raises(TypeError, match="duration_ms debe ser un entero"):
            HookResult(
                success=True,
                exit_code=0,
                stdout="",
                stderr="",
                duration_ms="100",  # type: ignore
            )


class TestWorkspaceHook:
    """Tests for WorkspaceHook dataclass."""

    def test_create_workspace_hook(self) -> None:
        """Test creating a WorkspaceHook instance."""
        hook = WorkspaceHook(
            workspace_id="ws-001",
            setup_path=Path("/test/setup.sh"),
            teardown_path=Path("/test/teardown.sh"),
            environment=(("KEY", "value"),),
        )
        assert hook.workspace_id == "ws-001"
        assert hook.setup_path == Path("/test/setup.sh")
        assert hook.teardown_path == Path("/test/teardown.sh")
        assert hook.environment == (("KEY", "value"),)

    def test_create_workspace_hook_with_defaults(self) -> None:
        """Test creating WorkspaceHook with default values."""
        hook = WorkspaceHook(workspace_id="ws-001")
        assert hook.workspace_id == "ws-001"
        assert hook.setup_path is None
        assert hook.teardown_path is None
        assert hook.environment == ()

    def test_workspace_hook_immutability(self) -> None:
        """Test that WorkspaceHook is immutable (frozen=True)."""
        from dataclasses import FrozenInstanceError

        hook = WorkspaceHook(
            workspace_id="ws-001",
            setup_path=Path("/test/setup.sh"),
        )
        with pytest.raises(FrozenInstanceError):
            hook.workspace_id = "ws-002"
        with pytest.raises(FrozenInstanceError):
            hook.setup_path = Path("/other/setup.sh")

    def test_workspace_hook_validates_workspace_id_type(self) -> None:
        """Test that WorkspaceHook validates workspace_id is a string."""
        with pytest.raises(TypeError, match="workspace_id debe ser un string"):
            WorkspaceHook(workspace_id=123)  # type: ignore

    def test_workspace_hook_validates_setup_path_type(self) -> None:
        """Test that WorkspaceHook validates setup_path is a Path or None."""
        with pytest.raises(TypeError, match="setup_path debe ser un Path o None"):
            WorkspaceHook(workspace_id="ws-001", setup_path="/not/a/path")  # type: ignore

    def test_workspace_hook_validates_teardown_path_type(self) -> None:
        """Test that WorkspaceHook validates teardown_path is a Path or None."""
        with pytest.raises(TypeError, match="teardown_path debe ser un Path o None"):
            WorkspaceHook(workspace_id="ws-001", teardown_path="/not/a/path")  # type: ignore

    def test_workspace_hook_validates_environment_is_tuple(self) -> None:
        """Test that WorkspaceHook validates environment is a tuple."""
        with pytest.raises(TypeError, match="environment debe ser una tupla"):
            WorkspaceHook(workspace_id="ws-001", environment={"key": "value"})  # type: ignore

    def test_workspace_hook_validates_environment_item_format(self) -> None:
        """Test that WorkspaceHook validates environment items are tuples of 2."""
        with pytest.raises(TypeError, match="environment debe ser tupla de tuplas"):
            WorkspaceHook(workspace_id="ws-001", environment=("not a tuple",))  # type: ignore

    def test_workspace_hook_validates_environment_item_length(self) -> None:
        """Test that WorkspaceHook validates environment items have length 2."""
        with pytest.raises(TypeError, match="environment debe ser tupla de tuplas"):
            WorkspaceHook(workspace_id="ws-001", environment=(("key", "value", "extra"),))  # type: ignore

    def test_workspace_hook_with_empty_environment(self) -> None:
        """Test creating WorkspaceHook with empty environment tuple."""
        hook = WorkspaceHook(workspace_id="ws-001", environment=())
        assert hook.environment == ()

    def test_workspace_hook_with_multiple_env_vars(self) -> None:
        """Test creating WorkspaceHook with multiple environment variables."""
        hook = WorkspaceHook(
            workspace_id="ws-001",
            environment=(
                ("VAR1", "value1"),
                ("VAR2", "value2"),
                ("VAR3", "value3"),
            ),
        )
        assert len(hook.environment) == 3
